"""
请求日志记录中间件
用于记录 AgentOS API 的请求和响应信息

功能：
- 记录请求方法、路径、客户端IP
- 非流式：记录响应状态码与完整请求耗时
- 流式：区分 header_ready（响应对象就绪）与 stream_complete（流传输结束），单行关联 request_id
- 使用独立 RotatingFileHandler 实例写入与 agno 相同文件，避免多 Logger 共享 Handler 导致并发错乱
"""

import os
import time
import uuid
import logging
import logging.handlers
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, _StreamingResponse as MiddlewareStreamingResponse
from starlette.responses import StreamingResponse


def _parse_path_list(env_val: Optional[str]) -> List[str]:
    if not env_val or not env_val.strip():
        return []
    return [p.strip() for p in env_val.split(",") if p.strip()]


def _load_request_logging_options() -> Dict[str, Any]:
    """
    读取请求日志路径策略：配置 agentos.request_logging + 环境变量覆盖。
    - skip_info_prefixes: 匹配前缀的路径请求/响应用 DEBUG
    - always_info_prefixes: 匹配前缀则强制 INFO（覆盖 skip）
    """
    skip_prefixes: List[str] = ["/health", "/sessions"]
    always_prefixes: List[str] = []

    try:
        from config.config_loader import get_agentos_config  # type: ignore
        cfg = get_agentos_config().get("request_logging") or {}
        skip_prefixes = list(cfg.get("skip_info_prefixes", skip_prefixes))
        always_prefixes = list(cfg.get("always_info_prefixes", always_prefixes))
    except Exception:
        pass

    # 环境变量覆盖（逗号分隔前缀）
    env_skip = os.environ.get("REQUEST_LOGGING_SKIP_INFO_PREFIXES")
    if env_skip is not None:
        skip_prefixes = _parse_path_list(env_skip)
    env_always = os.environ.get("REQUEST_LOGGING_ALWAYS_INFO_PREFIXES")
    if env_always is not None:
        always_prefixes = _parse_path_list(env_always)

    return {
        "skip_prefixes": skip_prefixes,
        "always_prefixes": always_prefixes,
    }


def _should_skip_info(path: str, opts: Dict[str, Any]) -> bool:
    path = path or ""
    for prefix in opts.get("always_prefixes", []):
        if prefix and path.startswith(prefix):
            return False
    for prefix in opts.get("skip_prefixes", []):
        if prefix and (path == prefix.rstrip("/") or path.startswith(prefix)):
            return True
    if path.rstrip("/") == "/health":
        return True
    return False


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志记录中间件。
    流式响应不在 call_next 返回时记为“完成”；结束时打 stream_complete 一行（含 request_id）。
    """

    _request_logging_opts: Optional[Dict[str, Any]] = None

    def __init__(self, app, logger_name: str = "agentos.request"):
        super().__init__(app)
        self.logger = self._setup_logger(logger_name)

    def _setup_logger(self, logger_name: str) -> logging.Logger:
        """
        为 agentos.request 创建独立 Handler 实例（与 agno 同文件路径），
        不共享 agno 的 Handler 对象，避免并发 emit 锁竞争与 Filter 耦合。
        """
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        logger.propagate = False

        log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(log_format, date_format)

        agno_logger = logging.getLogger("agno")
        template_handler: Optional[logging.handlers.RotatingFileHandler] = None
        for h in agno_logger.handlers:
            if isinstance(h, logging.handlers.RotatingFileHandler):
                template_handler = h
                break

        if template_handler is not None:
            max_bytes = getattr(template_handler, "maxBytes", 10485760)
            backup_count = getattr(template_handler, "backupCount", 5)
            encoding = getattr(template_handler, "encoding", "utf-8") or "utf-8"
            file_handler = logging.handlers.RotatingFileHandler(
                template_handler.baseFilename,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding=encoding,
            )
        else:
            _current_file = Path(__file__).resolve()
            _project_root = _current_file.parents[2]
            log_file_path = _project_root / "log" / "app.log"
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                str(log_file_path),
                maxBytes=10485760,
                backupCount=5,
                encoding="utf-8",
            )

        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        return logger

    def _get_response_body_stream(self, response):
        """从响应对象获取可迭代的 body 流。"""
        body_iterator = getattr(response, "body_iterator", None)
        if body_iterator is not None:
            if callable(body_iterator):
                return body_iterator()
            return body_iterator
        body = getattr(response, "body", None)
        if body is not None and hasattr(body, "__aiter__"):
            return body
        return None

    def _wrap_streaming_response(
        self,
        response,
        request_start_time: float,
        request_id: str,
        method: str,
        path: str,
        status_code: int,
        header_ready_ms: float,
    ):
        """
        包装流式响应：首包打阶段耗时；结束打单行 stream_complete（与 request_id 关联）；
        流内异常打 Stream error。
        """
        try:
            from utils.tool_hooks import get_and_clear_query_phase_end_time  # type: ignore
        except ImportError:
            get_and_clear_query_phase_end_time = None

        phase_logger = logging.getLogger("agno")
        body_iterator = self._get_response_body_stream(response)
        if body_iterator is None:
            if "/runs" in path or path.rstrip("/").endswith("runs"):
                phase_logger.info(
                    f"未包装流式响应(无 body 流): request_id={request_id} response_type={type(response).__name__} path={path}"
                )
            return response

        is_runs_path = "/runs" in path or path.rstrip("/").endswith("runs")

        async def wrapped_body():
            first = True
            ttfb_ms: Optional[float] = None
            stream_error: Optional[str] = None
            try:
                async for chunk in body_iterator:
                    if first:
                        first = False
                        ttfb_ms = (time.perf_counter() - request_start_time) * 1000
                        if is_runs_path:
                            if get_and_clear_query_phase_end_time is not None:
                                t_end = get_and_clear_query_phase_end_time()
                                if t_end is not None:
                                    elapsed = time.perf_counter() - t_end
                                    phase_logger.info(
                                        f"request_id={request_id} 查询商品库阶段结束到首包: {elapsed:.2f}s"
                                    )
                            phase_logger.info(
                                f"request_id={request_id} 首字响应总耗时: {ttfb_ms / 1000.0:.2f}s"
                            )
                    yield chunk
            except Exception as e:
                stream_error = f"{type(e).__name__}:{e}"
                phase_logger.warning(
                    f"Stream error request_id={request_id} path={path} after_first_chunk={not first} {stream_error}",
                    exc_info=True,
                )
                raise
            finally:
                total_ms = (time.perf_counter() - request_start_time) * 1000
                # 单行汇总，便于 grep request_id 关联状态与总耗时
                parts = [
                    f"stream_complete request_id={request_id}",
                    f"{method} {path}",
                    f"status={status_code}",
                    f"header_ready_ms={header_ready_ms:.1f}",
                    f"total_ms={total_ms:.1f}",
                ]
                if ttfb_ms is not None:
                    parts.append(f"ttfb_ms={ttfb_ms:.1f}")
                if stream_error:
                    parts.append(f"error={stream_error}")
                phase_logger.info(" | ".join(parts))

        return StreamingResponse(
            wrapped_body(),
            status_code=getattr(response, "status_code", 200),
            headers=dict(getattr(response, "headers", {})),
            media_type=getattr(response, "media_type", "text/event-stream"),
        )

    async def dispatch(self, request: Request, call_next):
        if RequestLoggingMiddleware._request_logging_opts is None:
            RequestLoggingMiddleware._request_logging_opts = _load_request_logging_options()
        opts = RequestLoggingMiddleware._request_logging_opts

        start_time = time.perf_counter()
        request_id = uuid.uuid4().hex[:12]
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path or ""
        skip_info = _should_skip_info(path, opts)

        if skip_info:
            self.logger.debug(
                f"Request: {request.method} {path} from {client_ip} request_id={request_id}"
            )
        else:
            self.logger.info(
                f"Request: {request.method} {path} from {client_ip} request_id={request_id}"
            )

        try:
            response = await call_next(request)
            header_ready_ms = (time.perf_counter() - start_time) * 1000
            status_code = getattr(response, "status_code", 200)

            # call_next 在流式场景下返回的是 middleware.base._StreamingResponse；
            # 用 starlette.responses.StreamingResponse 判断会恒为 False，导致未包装、无首包/ stream_complete 日志
            body_stream = self._get_response_body_stream(response)
            is_middleware_streaming = isinstance(response, MiddlewareStreamingResponse)
            # 优先按中间件流式类型判断（与用户示例一致）；否则仍按可迭代 body 兜底
            should_wrap_stream = is_middleware_streaming or (body_stream is not None)

            if should_wrap_stream:
                # 流式：call_next 返回仅表示响应头/对象就绪，不表示传输完成
                if skip_info:
                    self.logger.debug(
                        f"Stream started: {request.method} {path} status={status_code} header_ready_ms={header_ready_ms:.1f} request_id={request_id}"
                    )
                else:
                    self.logger.info(
                        f"Stream started: {request.method} {path} status={status_code} header_ready_ms={header_ready_ms:.1f} request_id={request_id}"
                    )
                response = self._wrap_streaming_response(
                    response,
                    start_time,
                    request_id,
                    request.method,
                    path,
                    status_code,
                    header_ready_ms,
                )
            else:
                # 非流式：可视为完整请求已结束
                if skip_info:
                    self.logger.debug(
                        f"Response: {status_code} for {request.method} {path} in {header_ready_ms:.1f}ms request_id={request_id}"
                    )
                else:
                    self.logger.info(
                        f"Response: {status_code} for {request.method} {path} in {header_ready_ms:.1f}ms request_id={request_id}"
                    )

            return response

        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000
            self.logger.error(
                f"Error: {type(e).__name__}: {str(e)} for {request.method} {request.url.path} in {duration:.1f}ms request_id={request_id}"
            )
            raise
