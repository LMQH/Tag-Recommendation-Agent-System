"""
CORS 问题诊断测试脚本

测试目标：
① 与 credentials 冲突（当 allow_credentials=True 且 allow_origins=["*"] 时）
② 预检 OPTIONS 请求失败
③ Nginx/网关没覆盖到（特别是 stream/SSE 接口）
④ mount() 子应用没上 CORS

使用方法：
    python test_cors_issues.py --url https://ai-gateway-show.yunzhonghe.com --prefix /ecom_reco_agent
"""

import requests
import json
import sys
import io
from typing import Dict, List, Optional, Tuple
from enum import Enum

# 修复 Windows GBK 编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class TestStatus(Enum):
    """测试状态"""
    PASS = "✅ 通过"
    FAIL = "❌ 失败"
    WARN = "⚠️  警告"
    INFO = "ℹ️  信息"


class CorsIssueTester:
    """CORS 问题诊断测试器"""

    def __init__(self, base_url: str, path_prefix: str = "/ecom_reco_agent", agent_id: str = "ecom-reco-agent"):
        """
        初始化测试器

        Args:
            base_url: 基础 URL
            path_prefix: 路径前缀
            agent_id: Agent ID
        """
        self.base_url = base_url.rstrip('/')
        self.path_prefix = path_prefix.rstrip('/')
        self.agent_id = agent_id
        self.issues: List[Dict] = []

    def _make_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict] = None,
        data: Optional[Dict] = None,
        timeout: int = 10
    ) -> requests.Response:
        """
        发送 HTTP 请求

        Args:
            method: HTTP 方法
            path: 路径
            headers: 请求头
            data: 请求数据
            timeout: 超时时间

        Returns:
            响应对象
        """
        url = f"{self.base_url}{path}"
        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        if headers:
            default_headers.update(headers)

        try:
            if method == "GET":
                return requests.get(url, headers=default_headers, timeout=timeout)
            elif method == "POST":
                return requests.post(url, json=data, headers=default_headers, timeout=timeout)
            elif method == "OPTIONS":
                return requests.options(url, headers=default_headers, timeout=timeout)
            else:
                raise ValueError(f"不支持的方法: {method}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"请求失败: {e}")

    def _check_cors_headers(self, response: requests.Response) -> Dict:
        """
        检查 CORS 响应头

        Args:
            response: 响应对象

        Returns:
            CORS 头信息字典
        """
        return {
            "access_control_allow_origin": response.headers.get("Access-Control-Allow-Origin"),
            "access_control_allow_credentials": response.headers.get("Access-Control-Allow-Credentials"),
            "access_control_allow_methods": response.headers.get("Access-Control-Allow-Methods"),
            "access_control_allow_headers": response.headers.get("Access-Control-Allow-Headers"),
            "access_control_expose_headers": response.headers.get("Access-Control-Expose-Headers"),
            "access_control_max_age": response.headers.get("Access-Control-Max-Age"),
        }

    def test_issue_1_credentials_conflict(self) -> Dict:
        """
        测试问题 ①：与 credentials 冲突

        当 allow_credentials=True 且 allow_origins=["*"] 时，
        浏览器会拒绝请求。需要检查是否正确配置。
        """
        print("\n" + "=" * 80)
        print("问题 ①：测试 credentials 冲突")
        print("=" * 80)

        results = []

        # 测试 1.1：检查是否同时存在 allow_origins="*" 和 allow_credentials=true
        print("\n1.1 检查 CORS 头中的 credentials 配置冲突...")
        try:
            path = f"{self.path_prefix}/health"
            headers = {
                "Origin": "https://example.com",
            }
            response = self._make_request("GET", path, headers=headers)
            cors_headers = self._check_cors_headers(response)

            has_wildcard_origin = cors_headers["access_control_allow_origin"] == "*"
            has_credentials = cors_headers["access_control_allow_credentials"] == "true"

            if has_wildcard_origin and has_credentials:
                results.append({
                    "test": "credentials 冲突检查",
                    "status": TestStatus.FAIL,
                    "message": "检测到冲突：allow_origins='*' 且 allow_credentials=true",
                    "details": {
                        "allow_origin": cors_headers["access_control_allow_origin"],
                        "allow_credentials": cors_headers["access_control_allow_credentials"]
                    },
                    "recommendation": "当 credentials=true 时，origins 不能使用 '*'，需要指定具体域名"
                })
            else:
                results.append({
                    "test": "credentials 冲突检查",
                    "status": TestStatus.PASS,
                    "message": "未检测到 credentials 冲突",
                    "details": {
                        "allow_origin": cors_headers["access_control_allow_origin"],
                        "allow_credentials": cors_headers["access_control_allow_credentials"]
                    }
                })

        except Exception as e:
            results.append({
                "test": "credentials 冲突检查",
                "status": TestStatus.WARN,
                "message": f"测试失败: {e}",
                "details": {}
            })

        # 测试 1.2：模拟浏览器发送 withCredentials 请求
        print("\n1.2 模拟浏览器凭证请求...")
        try:
            path = f"{self.path_prefix}/health"
            headers = {
                "Origin": "https://example.com",
                "Cookie": "session=abc123"
            }
            response = self._make_request("GET", path, headers=headers)
            cors_headers = self._check_cors_headers(response)

            # 检查响应的 origin 是否与请求的 origin 匹配
            requested_origin = headers["Origin"]
            allowed_origin = cors_headers["access_control_allow_origin"]

            if cors_headers["access_control_allow_credentials"] == "true":
                if allowed_origin == requested_origin or allowed_origin == "*":
                    results.append({
                        "test": "浏览器凭证请求",
                        "status": TestStatus.PASS,
                        "message": "凭证请求配置正确",
                        "details": {
                            "requested_origin": requested_origin,
                            "allowed_origin": allowed_origin,
                            "allow_credentials": cors_headers["access_control_allow_credentials"]
                        }
                    })
                else:
                    results.append({
                        "test": "浏览器凭证请求",
                        "status": TestStatus.WARN,
                        "message": "允许的 origin 与请求的 origin 不匹配",
                        "details": {
                            "requested_origin": requested_origin,
                            "allowed_origin": allowed_origin
                        }
                    })
            else:
                results.append({
                    "test": "浏览器凭证请求",
                    "status": TestStatus.INFO,
                    "message": "未启用 credentials 支持",
                    "details": cors_headers
                })

        except Exception as e:
            results.append({
                "test": "浏览器凭证请求",
                "status": TestStatus.WARN,
                "message": f"测试失败: {e}",
                "details": {}
            })

        return {
            "issue": "① credentials 冲突",
            "results": results,
            "summary": self._summarize_results(results)
        }

    def test_issue_2_options_preflight(self) -> Dict:
        """
        测试问题 ②：预检 OPTIONS 请求失败

        检查 OPTIONS 预检请求是否正确响应
        """
        print("\n" + "=" * 80)
        print("问题 ②：测试 OPTIONS 预检请求")
        print("=" * 80)

        results = []

        # 测试 2.1：基本 OPTIONS 请求
        print("\n2.1 测试基本 OPTIONS 预检请求...")
        try:
            path = f"{self.path_prefix}/agents/{self.agent_id}/runs"
            headers = {
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization"
            }
            response = self._make_request("OPTIONS", path, headers=headers)
            cors_headers = self._check_cors_headers(response)

            # 检查状态码（OPTIONS 应该返回 200 或 204）
            if response.status_code in [200, 204]:
                results.append({
                    "test": "基本 OPTIONS 预检",
                    "status": TestStatus.PASS,
                    "message": f"OPTIONS 请求成功 (状态码: {response.status_code})",
                    "details": {
                        "status_code": response.status_code,
                        "cors_headers": cors_headers
                    }
                })
            else:
                results.append({
                    "test": "基本 OPTIONS 预检",
                    "status": TestStatus.FAIL,
                    "message": f"OPTIONS 请求失败 (状态码: {response.status_code})",
                    "details": {
                        "status_code": response.status_code,
                        "response_text": response.text[:200]
                    }
                })

        except Exception as e:
            results.append({
                "test": "基本 OPTIONS 预检",
                "status": TestStatus.FAIL,
                "message": f"请求失败: {e}",
                "details": {}
            })

        # 测试 2.2：OPTIONS 带自定义头
        print("\n2.2 测试 OPTIONS 带自定义请求头...")
        try:
            path = f"{self.path_prefix}/agents/{self.agent_id}/runs"
            headers = {
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization,x-custom-header"
            }
            response = self._make_request("OPTIONS", path, headers=headers)
            cors_headers = self._check_cors_headers(response)

            allowed_headers = cors_headers["access_control_allow_headers"]
            if allowed_headers and "x-custom-header" in allowed_headers.lower():
                results.append({
                    "test": "OPTIONS 自定义头",
                    "status": TestStatus.PASS,
                    "message": "支持自定义请求头",
                    "details": {
                        "allowed_headers": allowed_headers
                    }
                })
            else:
                results.append({
                    "test": "OPTIONS 自定义头",
                    "status": TestStatus.WARN,
                    "message": "可能不支持自定义请求头",
                    "details": {
                        "allowed_headers": allowed_headers
                    }
                })

        except Exception as e:
            results.append({
                "test": "OPTIONS 自定义头",
                "status": TestStatus.WARN,
                "message": f"测试失败: {e}",
                "details": {}
            })

        # 测试 2.3：OPTIONS 到不同路径
        print("\n2.3 测试多个端点的 OPTIONS 支持...")
        endpoints = [
            ("健康检查", f"{self.path_prefix}/health"),
            ("会话列表", f"{self.path_prefix}/sessions"),
            ("API 运行", f"{self.path_prefix}/agents/{self.agent_id}/runs"),
            ("流式端点", f"{self.path_prefix}/v1/agents/{self.agent_id}/chat"),
        ]

        options_results = []
        for name, path in endpoints:
            try:
                headers = {
                    "Origin": "https://example.com",
                    "Access-Control-Request-Method": "GET"
                }
                response = self._make_request("OPTIONS", path, headers=headers)
                options_results.append({
                    "endpoint": name,
                    "path": path,
                    "status_code": response.status_code,
                    "success": response.status_code in [200, 204]
                })
            except Exception as e:
                options_results.append({
                    "endpoint": name,
                    "path": path,
                    "status_code": None,
                    "success": False,
                    "error": str(e)
                })

        success_count = sum(1 for r in options_results if r.get("success", False))
        results.append({
            "test": "多端点 OPTIONS 支持",
            "status": TestStatus.PASS if success_count == len(endpoints) else TestStatus.WARN,
            "message": f"{success_count}/{len(endpoints)} 个端点支持 OPTIONS",
            "details": {"endpoints": options_results}
        })

        return {
            "issue": "② OPTIONS 预检请求",
            "results": results,
            "summary": self._summarize_results(results)
        }

    def test_issue_3_nginx_gateway_coverage(self) -> Dict:
        """
        测试问题 ③：Nginx/网关没覆盖到（特别是 stream/SSE 接口）

        检查流式接口和特殊路径是否被 CORS 配置覆盖
        """
        print("\n" + "=" * 80)
        print("问题 ③：测试 Nginx/网关 CORS 覆盖范围")
        print("=" * 80)

        results = []

        # 测试 3.1：流式/SSE 接口的 CORS
        print("\n3.1 测试流式/SSE 接口的 CORS 支持...")
        stream_endpoints = [
            ("Agent Chat (SSE)", f"{self.path_prefix}/v1/agents/{self.agent_id}/chat", "GET"),
            ("Agent Chat (Stream)", f"{self.path_prefix}/agents/{self.agent_id}/runs", "POST"),
        ]

        for name, path, method in stream_endpoints:
            try:
                headers = {
                    "Origin": "https://example.com",
                }
                # 根据端点使用正确的 HTTP 方法
                data = {"message": "test", "stream_events": False} if method == "POST" else None
                response = self._make_request(method, path, headers=headers, data=data, timeout=5)
                cors_headers = self._check_cors_headers(response)

                has_cors = any(cors_headers.values())
                results.append({
                    "test": f"流式接口 CORS - {name}",
                    "status": TestStatus.PASS if has_cors else TestStatus.FAIL,
                    "message": f"流式接口有 CORS 支持 (方法: {method})" if has_cors else f"流式接口缺少 CORS 支持 (方法: {method})",
                    "details": {
                        "path": path,
                        "method": method,
                        "status_code": response.status_code,
                        "cors_headers": cors_headers
                    }
                })
            except Exception as e:
                results.append({
                    "test": f"流式接口 CORS - {name}",
                    "status": TestStatus.WARN,
                    "message": f"测试失败: {e}",
                    "details": {}
                })

        # 测试 3.2：检查不同路径层级的 CORS
        print("\n3.2 检查不同路径层级的 CORS...")
        test_paths = [
            ("根路径", f"{self.path_prefix}/", "GET"),
            ("一级路径", f"{self.path_prefix}/health", "GET"),
            ("二级路径", f"{self.path_prefix}/sessions", "GET"),
            ("三级路径", f"{self.path_prefix}/agents/{self.agent_id}", "GET"),
            ("四级路径", f"{self.path_prefix}/agents/{self.agent_id}/runs", "POST"),
            ("API v1 路径", f"{self.path_prefix}/v1/agents/{self.agent_id}/chat", "POST"),
        ]

        cors_coverage = []
        for name, path, method in test_paths:
            try:
                headers = {"Origin": "https://example.com"}
                data = {"message": "test", "stream_events": False} if method == "POST" else None
                response = self._make_request(method, path, headers=headers, data=data, timeout=5)
                cors_headers = self._check_cors_headers(response)
                has_cors = cors_headers["access_control_allow_origin"] is not None

                cors_coverage.append({
                    "name": name,
                    "path": path,
                    "method": method,
                    "status_code": response.status_code,
                    "has_cors": has_cors,
                    "allow_origin": cors_headers["access_control_allow_origin"]
                })
            except Exception as e:
                cors_coverage.append({
                    "name": name,
                    "path": path,
                    "method": method,
                    "has_cors": False,
                    "error": str(e)
                })

                cors_coverage.append({
                    "name": name,
                    "path": path,
                    "has_cors": has_cors,
                    "allow_origin": cors_headers["access_control_allow_origin"]
                })
            except Exception as e:
                cors_coverage.append({
                    "name": name,
                    "path": path,
                    "has_cors": False,
                    "error": str(e)
                })

        coverage_count = sum(1 for c in cors_coverage if c.get("has_cors", False))
        results.append({
            "test": "路径层级 CORS 覆盖",
            "status": TestStatus.PASS if coverage_count == len(test_paths) else TestStatus.WARN,
            "message": f"{coverage_count}/{len(test_paths)} 个路径层级有 CORS",
            "details": {"coverage": cors_coverage}
        })

        # 测试 3.3：检查是否有重复的 CORS 头（可能来自多个层级）
        print("\n3.3 检查是否有重复的 CORS 头...")
        try:
            path = f"{self.path_prefix}/health"
            headers = {"Origin": "https://example.com"}
            response = self._make_request("GET", path, headers=headers)

            # 获取所有响应头
            all_headers = dict(response.headers)
            cors_related = {k: v for k, v in all_headers.items() if "access-control" in k.lower()}

            # 检查是否有重复的头（例如，Nginx 和 FastAPI 都添加了）
            header_names = list(cors_related.keys())
            has_duplicates = len(header_names) != len(set(h.lower() for h in header_names))

            results.append({
                "test": "重复 CORS 头检查",
                "status": TestStatus.WARN if has_duplicates else TestStatus.PASS,
                "message": "检测到可能的重复 CORS 头" if has_duplicates else "未检测到重复 CORS 头",
                "details": {
                    "cors_headers": cors_related,
                    "all_headers": list(all_headers.keys())
                }
            })

        except Exception as e:
            results.append({
                "test": "重复 CORS 头检查",
                "status": TestStatus.WARN,
                "message": f"测试失败: {e}",
                "details": {}
            })

        return {
            "issue": "③ Nginx/网关 CORS 覆盖",
            "results": results,
            "summary": self._summarize_results(results)
        }

    def test_issue_4_mount_subapp_cors(self) -> Dict:
        """
        测试问题 ④：mount() 子应用没上 CORS

        检查使用 FastAPI mount() 挂载的子应用是否正确继承 CORS 配置
        """
        print("\n" + "=" * 80)
        print("问题 ④：测试 mount() 子应用 CORS 继承")
        print("=" * 80)

        results = []

        # 测试 4.1：检查挂载点本身是否有 CORS
        print("\n4.1 检查挂载点路径的 CORS...")
        try:
            mount_point = self.path_prefix
            headers = {"Origin": "https://example.com"}
            response = self._make_request("GET", mount_point, headers=headers)
            cors_headers = self._check_cors_headers(response)

            has_cors_at_mount = cors_headers["access_control_allow_origin"] is not None
            results.append({
                "test": "挂载点 CORS",
                "status": TestStatus.PASS if has_cors_at_mount else TestStatus.FAIL,
                "message": f"挂载点{'有' if has_cors_at_mount else '没有'} CORS",
                "details": {
                    "mount_point": mount_point,
                    "cors_headers": cors_headers
                }
            })
        except Exception as e:
            results.append({
                "test": "挂载点 CORS",
                "status": TestStatus.WARN,
                "message": f"测试失败: {e}",
                "details": {}
            })

        # 测试 4.2：检查子应用路径是否有 CORS
        print("\n4.2 检查子应用路径的 CORS...")
        subapp_paths = [
            f"{self.path_prefix}/health",
            f"{self.path_prefix}/docs",
            f"{self.path_prefix}/openapi.json",
            f"{self.path_prefix}/sessions",
        ]

        subapp_cors_results = []
        for path in subapp_paths:
            try:
                headers = {"Origin": "https://example.com"}
                response = self._make_request("GET", path, headers=headers)
                cors_headers = self._check_cors_headers(response)

                subapp_cors_results.append({
                    "path": path,
                    "has_cors": cors_headers["access_control_allow_origin"] is not None,
                    "allow_origin": cors_headers["access_control_allow_origin"],
                    "allow_credentials": cors_headers["access_control_allow_credentials"]
                })
            except Exception as e:
                subapp_cors_results.append({
                    "path": path,
                    "has_cors": False,
                    "error": str(e)
                })

        cors_count = sum(1 for r in subapp_cors_results if r.get("has_cors", False))
        results.append({
            "test": "子应用路径 CORS",
            "status": TestStatus.PASS if cors_count == len(subapp_paths) else TestStatus.FAIL,
            "message": f"{cors_count}/{len(subapp_paths)} 个子应用路径有 CORS",
            "details": {"paths": subapp_cors_results}
        })

        # 测试 4.3：检查子应用 OPTIONS 预检
        print("\n4.3 检查子应用 OPTIONS 预检...")
        try:
            path = f"{self.path_prefix}/health"
            headers = {
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET"
            }
            response = self._make_request("OPTIONS", path, headers=headers)
            cors_headers = self._check_cors_headers(response)

            options_works = response.status_code in [200, 204]
            has_cors = cors_headers["access_control_allow_origin"] is not None

            if options_works and has_cors:
                results.append({
                    "test": "子应用 OPTIONS 预检",
                    "status": TestStatus.PASS,
                    "message": "子应用 OPTIONS 预检正常",
                    "details": {
                        "status_code": response.status_code,
                        "cors_headers": cors_headers
                    }
                })
            else:
                results.append({
                    "test": "子应用 OPTIONS 预检",
                    "status": TestStatus.FAIL,
                    "message": f"子应用 OPTIONS 预检异常 (状态码: {response.status_code}, 有CORS: {has_cors})",
                    "details": {
                        "status_code": response.status_code,
                        "cors_headers": cors_headers
                    }
                })
        except Exception as e:
            results.append({
                "test": "子应用 OPTIONS 预检",
                "status": TestStatus.FAIL,
                "message": f"测试失败: {e}",
                "details": {}
            })

        # 测试 4.4：比较根应用和子应用的 CORS
        print("\n4.4 比较根应用和子应用的 CORS 一致性...")
        try:
            # 假设根应用不带前缀（需要根据实际情况调整）
            # 这里比较路径前缀下的不同路径
            paths_to_compare = [
                f"{self.path_prefix}/health",
                f"{self.path_prefix}/sessions",
            ]

            cors_configs = []
            for path in paths_to_compare:
                try:
                    headers = {"Origin": "https://example.com"}
                    response = self._make_request("GET", path, headers=headers)
                    cors_headers = self._check_cors_headers(response)
                    cors_configs.append({
                        "path": path,
                        "cors_headers": cors_headers
                    })
                except:
                    pass

            # 检查所有路径的 CORS 配置是否一致
            if len(cors_configs) > 1:
                first_config = cors_configs[0]["cors_headers"]
                all_same = all(
                    c["cors_headers"] == first_config
                    for c in cors_configs[1:]
                )

                results.append({
                    "test": "CORS 配置一致性",
                    "status": TestStatus.PASS if all_same else TestStatus.WARN,
                    "message": "CORS 配置一致" if all_same else "CORS 配置可能不一致",
                    "details": {"configs": cors_configs}
                })
            else:
                results.append({
                    "test": "CORS 配置一致性",
                    "status": TestStatus.WARN,
                    "message": "无法比较（测试数据不足）",
                    "details": {}
                })

        except Exception as e:
            results.append({
                "test": "CORS 配置一致性",
                "status": TestStatus.WARN,
                "message": f"测试失败: {e}",
                "details": {}
            })

        return {
            "issue": "④ mount() 子应用 CORS",
            "results": results,
            "summary": self._summarize_results(results)
        }

    def _summarize_results(self, results: List[Dict]) -> Dict:
        """汇总测试结果"""
        total = len(results)
        passed = sum(1 for r in results if r["status"] == TestStatus.PASS)
        failed = sum(1 for r in results if r["status"] == TestStatus.FAIL)
        warned = sum(1 for r in results if r["status"] == TestStatus.WARN)

        status = TestStatus.PASS if failed == 0 else (TestStatus.WARN if warned > 0 else TestStatus.FAIL)

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "warned": warned,
            "status": status.value  # 转换为字符串以便 JSON 序列化
        }

    def run_all_tests(self) -> Dict:
        """运行所有 CORS 问题测试"""
        print("=" * 80)
        print("CORS 问题诊断测试")
        print("=" * 80)
        print(f"目标 URL: {self.base_url}")
        print(f"路径前缀: {self.path_prefix}")
        print(f"Agent ID: {self.agent_id}")
        print("=" * 80)

        # 运行四个问题的测试
        issue_1 = self.test_issue_1_credentials_conflict()
        issue_2 = self.test_issue_2_options_preflight()
        issue_3 = self.test_issue_3_nginx_gateway_coverage()
        issue_4 = self.test_issue_4_mount_subapp_cors()

        report = {
            "target": {
                "base_url": self.base_url,
                "path_prefix": self.path_prefix,
                "agent_id": self.agent_id
            },
            "issues": [
                issue_1,
                issue_2,
                issue_3,
                issue_4
            ],
            "overall_summary": self._create_overall_summary([issue_1, issue_2, issue_3, issue_4])
        }

        return report

    def _create_overall_summary(self, issues: List[Dict]) -> Dict:
        """创建整体汇总"""
        total_tests = sum(i["summary"]["total"] for i in issues)
        total_passed = sum(i["summary"]["passed"] for i in issues)
        total_failed = sum(i["summary"]["failed"] for i in issues)
        total_warned = sum(i["summary"]["warned"] for i in issues)

        failed_issues = [i["issue"] for i in issues if i["summary"]["failed"] > 0]
        warned_issues = [i["issue"] for i in issues if i["summary"]["warned"] > 0 and i["summary"]["failed"] == 0]

        return {
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_warned": total_warned,
            "success_rate": f"{(total_passed / total_tests * 100):.1f}%" if total_tests > 0 else "0%",
            "failed_issues": failed_issues,
            "warned_issues": warned_issues,
            "overall_status": "通过" if total_failed == 0 and total_warned == 0 else ("警告" if total_failed == 0 else "失败")
        }

    def print_report(self, report: Dict):
        """打印测试报告"""
        print("\n" + "=" * 80)
        print("CORS 问题诊断报告")
        print("=" * 80)

        summary = report["overall_summary"]
        print(f"\n📊 整体汇总:")
        print(f"   总测试数: {summary['total_tests']}")
        print(f"   通过: {summary['total_passed']} ✅")
        print(f"   失败: {summary['total_failed']} ❌")
        print(f"   警告: {summary['total_warned']} ⚠️")
        print(f"   成功率: {summary['success_rate']}")
        print(f"   整体状态: {summary['overall_status']}")

        if summary["failed_issues"]:
            print(f"\n❌ 发现问题的测试:")
            for issue in summary["failed_issues"]:
                print(f"   - {issue}")

        if summary["warned_issues"]:
            print(f"\n⚠️  需要关注的测试:")
            for issue in summary["warned_issues"]:
                print(f"   - {issue}")

        # 打印每个问题的详细结果
        for issue in report["issues"]:
            print("\n" + "=" * 80)
            print(f"{issue['issue']} - 详细结果")
            print("=" * 80)

            for result in issue["results"]:
                # 转换 status 为字符串（用于 JSON 序列化）
                if isinstance(result["status"], TestStatus):
                    result["status"] = result["status"].value

                status_icon = result["status"]
                print(f"\n{status_icon} {result['test']}")
                print(f"   {result['message']}")

                if result.get("details"):
                    details = result["details"]
                    if isinstance(details, dict):
                        for key, value in details.items():
                            if key == "cors_headers" or key == "headers":
                                print(f"   {key}:")
                                if isinstance(value, dict):
                                    for hk, hv in value.items():
                                        if hv:
                                            print(f"     - {hk}: {hv}")
                            elif key == "endpoints" or key == "paths" or key == "coverage":
                                print(f"   {key}:")
                                if isinstance(value, list):
                                    for item in value:
                                        print(f"     - {item}")
                            elif isinstance(value, (dict, list)):
                                print(f"   {key}: {json.dumps(value, ensure_ascii=False, indent=6)}")
                            else:
                                print(f"   {key}: {value}")

                if result.get("recommendation"):
                    print(f"   💡 建议: {result['recommendation']}")

        print("\n" + "=" * 80)
        print("测试完成")
        print("=" * 80)

        # 输出 JSON 格式的报告
        print("\n📋 JSON 报告:")
        print(json.dumps(report, ensure_ascii=False, indent=2))


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="CORS 问题诊断测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
测试示例：
  python test_cors_issues.py --url https://ai-gateway-show.yunzhonghe.com
  python test_cors_issues.py --url http://localhost:8887 --prefix ""
  python test_cors_issues.py --url https://example.com --prefix /api --agent-id my-agent
        """
    )

    parser.add_argument(
        "--url",
        type=str,
        default="https://ai-gateway-show.yunzhonghe.com",
        help="基础 URL（默认: https://ai-gateway-show.yunzhonghe.com）"
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="/ecom_reco_agent",
        help="路径前缀（默认: /ecom_reco_agent）。注意：必须以 / 开头"
    )
    parser.add_argument(
        "--agent-id",
        type=str,
        default="ecom-reco-agent",
        help="Agent ID（默认: ecom-reco-agent）"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出 JSON 报告文件路径（可选）"
    )
    parser.add_argument(
        "--issue",
        type=int,
        choices=[1, 2, 3, 4],
        help="仅测试特定问题 (1-4)，不指定则测试所有问题"
    )

    args = parser.parse_args()

    # 确保 prefix 以 / 开头
    if args.prefix and not args.prefix.startswith('/'):
        args.prefix = f"/{args.prefix}"

    # 创建测试器
    tester = CorsIssueTester(
        base_url=args.url,
        path_prefix=args.prefix,
        agent_id=args.agent_id
    )

    # 运行测试
    if args.issue:
        # 只运行指定的测试
        issue_tests = {
            1: tester.test_issue_1_credentials_conflict,
            2: tester.test_issue_2_options_preflight,
            3: tester.test_issue_3_nginx_gateway_coverage,
            4: tester.test_issue_4_mount_subapp_cors,
        }
        result = issue_tests[args.issue]()
        report = {
            "target": {
                "base_url": args.url,
                "path_prefix": args.prefix,
                "agent_id": args.agent_id
            },
            "issues": [result],
            "overall_summary": tester._create_overall_summary([result])
        }
    else:
        # 运行所有测试
        report = tester.run_all_tests()

    # 打印报告
    tester.print_report(report)

    # 保存 JSON 报告
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n📄 报告已保存到: {args.output}")

    # 返回退出码
    exit_code = 0 if report["overall_summary"]["total_failed"] == 0 else 1
    exit(exit_code)


if __name__ == "__main__":
    main()
