"""
Nginx 路径转发测试脚本

测试内容：
1. 检查 Nginx 转发的路径是否正确
2. 检查路径前缀是否正确包含
3. 检查各个接口的路径是否正确
4. 检查 CORS 头是否正确
5. 检查响应状态码是否正确
"""

import requests
import json
from typing import Dict, List, Optional
from urllib.parse import urljoin


class NginxPathTester:
    """Nginx 路径转发测试器"""
    
    def __init__(self, base_url: str, path_prefix: str = "/ecom_reco_agent", agent_id: str = "ecom-reco-agent"):
        """
        初始化测试器
        
        Args:
            base_url: 基础 URL（如 https://ai-gateway-show.yunzhonghe.com）
            path_prefix: 路径前缀（如 /ecom_reco_agent）
            agent_id: Agent ID
        """
        self.base_url = base_url.rstrip('/')
        self.path_prefix = path_prefix.rstrip('/')
        self.agent_id = agent_id
        self.results: List[Dict] = []
    
    def test_endpoint(
        self,
        name: str,
        path: str,
        method: str = "GET",
        expected_status: int = 200,
        check_cors: bool = True,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict:
        """
        测试单个端点
        
        Args:
            name: 测试名称
            path: 路径（相对于 base_url）
            method: HTTP 方法
            expected_status: 期望的状态码
            check_cors: 是否检查 CORS 头
            data: 请求数据
            headers: 请求头
        
        Returns:
            测试结果字典
        """
        # 构建完整 URL
        if path.startswith('/'):
            full_path = path
        else:
            full_path = f'/{path}'
        
        full_url = f"{self.base_url}{full_path}"
        
        # 默认请求头
        default_headers = {
            "Content-Type": "application/json",
            "Origin": "https://www.baidu.com"  # 用于测试 CORS
        }
        if headers:
            default_headers.update(headers)
        
        result = {
            "name": name,
            "url": full_url,
            "path": full_path,
            "method": method,
            "expected_status": expected_status,
            "status": None,
            "success": False,
            "error": None,
            "cors_headers": {},
            "response_headers": {},
            "has_path_prefix": self.path_prefix in full_path,
        }
        
        try:
            # 发送请求
            if method == "GET":
                response = requests.get(full_url, headers=default_headers, timeout=10)
            elif method == "POST":
                if data:
                    if default_headers.get("Content-Type") == "application/json":
                        response = requests.post(full_url, json=data, headers=default_headers, timeout=10)
                    else:
                        response = requests.post(full_url, data=data, headers=default_headers, timeout=10)
                else:
                    response = requests.post(full_url, headers=default_headers, timeout=10)
            elif method == "OPTIONS":
                response = requests.options(full_url, headers=default_headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            result["status"] = response.status_code
            result["success"] = response.status_code == expected_status
            result["response_headers"] = dict(response.headers)
            
            # 检查 CORS 头
            if check_cors:
                cors_headers = {
                    "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
                    "Access-Control-Allow-Credentials": response.headers.get("Access-Control-Allow-Credentials"),
                    "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
                    "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers"),
                    "Access-Control-Expose-Headers": response.headers.get("Access-Control-Expose-Headers"),
                }
                result["cors_headers"] = cors_headers
                result["has_cors"] = any(cors_headers.values())
            
            # 尝试解析响应内容
            try:
                if response.text:
                    result["response_body"] = response.json() if response.headers.get("Content-Type", "").startswith("application/json") else response.text[:200]
            except:
                result["response_body"] = response.text[:200] if response.text else None
            
        except requests.exceptions.RequestException as e:
            result["error"] = str(e)
            result["success"] = False
        
        self.results.append(result)
        return result
    
    def run_all_tests(self) -> Dict:
        """运行所有测试"""
        print("=" * 80)
        print("Nginx 路径转发测试")
        print("=" * 80)
        print(f"基础 URL: {self.base_url}")
        print(f"路径前缀: {self.path_prefix}")
        print(f"Agent ID: {self.agent_id}")
        print("=" * 80)
        print()
        
        # 1. 测试健康检查接口
        print("1. 测试健康检查接口...")
        health_path = f"{self.path_prefix}/health"
        self.test_endpoint("健康检查", health_path, method="GET", expected_status=200)
        
        # 2. 测试 API 文档接口
        print("2. 测试 API 文档接口...")
        docs_path = f"{self.path_prefix}/docs"
        self.test_endpoint("API 文档 (Swagger)", docs_path, method="GET", expected_status=200, check_cors=False)
        
        # 3. 测试 OpenAPI JSON
        print("3. 测试 OpenAPI JSON...")
        openapi_path = f"{self.path_prefix}/openapi.json"
        self.test_endpoint("OpenAPI JSON", openapi_path, method="GET", expected_status=200)
        
        # 4. 测试主接口路径（不发送实际请求，只检查路径）
        print("4. 测试主接口路径...")
        runs_path = f"{self.path_prefix}/agents/{self.agent_id}/runs"
        self.test_endpoint(
            "主接口路径检查",
            runs_path,
            method="OPTIONS",  # 使用 OPTIONS 预检请求，不会触发实际处理
            expected_status=200,
            check_cors=True
        )
        
        # 5. 测试会话列表接口
        print("5. 测试会话列表接口...")
        sessions_path = f"{self.path_prefix}/sessions"
        self.test_endpoint("会话列表", sessions_path, method="GET", expected_status=200)
        
        # 6. 测试不带路径前缀的路径（应该失败或重定向）
        print("6. 测试不带路径前缀的路径...")
        self.test_endpoint(
            "不带前缀的健康检查（应该失败）",
            "/health",
            method="GET",
            expected_status=404,  # 期望 404，因为路径不匹配
            check_cors=False
        )
        
        # 7. 测试 CORS 预检请求
        print("7. 测试 CORS 预检请求...")
        self.test_endpoint(
            "CORS 预检请求",
            f"{self.path_prefix}/agents/{self.agent_id}/runs",
            method="OPTIONS",
            expected_status=200,
            check_cors=True,
            headers={
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type"
            }
        )
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """生成测试报告"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = total - passed
        
        report = {
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "success_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%"
            },
            "results": self.results,
            "path_prefix_analysis": self._analyze_path_prefix(),
            "cors_analysis": self._analyze_cors()
        }
        
        return report
    
    def _analyze_path_prefix(self) -> Dict:
        """分析路径前缀"""
        with_prefix = sum(1 for r in self.results if r.get("has_path_prefix", False))
        without_prefix = len(self.results) - with_prefix
        
        return {
            "path_prefix": self.path_prefix,
            "tests_with_prefix": with_prefix,
            "tests_without_prefix": without_prefix,
            "prefix_required": True
        }
    
    def _analyze_cors(self) -> Dict:
        """分析 CORS 配置"""
        cors_tests = [r for r in self.results if r.get("cors_headers")]
        has_cors = sum(1 for r in cors_tests if r.get("has_cors", False))
        
        cors_origins = set()
        for r in cors_tests:
            origin = r.get("cors_headers", {}).get("Access-Control-Allow-Origin")
            if origin:
                cors_origins.add(origin)
        
        return {
            "cors_tests": len(cors_tests),
            "has_cors_headers": has_cors,
            "cors_origins": list(cors_origins),
            "cors_enabled": has_cors > 0
        }
    
    def print_report(self, report: Optional[Dict] = None):
        """打印测试报告"""
        if report is None:
            report = self.generate_report()
        
        print()
        print("=" * 80)
        print("测试报告")
        print("=" * 80)
        print(f"总计: {report['summary']['total']}")
        print(f"通过: {report['summary']['passed']} ✅")
        print(f"失败: {report['summary']['failed']} ❌")
        print(f"成功率: {report['summary']['success_rate']}")
        print()
        
        print("=" * 80)
        print("路径前缀分析")
        print("=" * 80)
        prefix_analysis = report['path_prefix_analysis']
        print(f"路径前缀: {prefix_analysis['path_prefix']}")
        print(f"包含前缀的测试: {prefix_analysis['tests_with_prefix']}")
        print(f"不包含前缀的测试: {prefix_analysis['tests_without_prefix']}")
        print(f"前缀是否必需: {'是' if prefix_analysis['prefix_required'] else '否'}")
        print()
        
        print("=" * 80)
        print("CORS 配置分析")
        print("=" * 80)
        cors_analysis = report['cors_analysis']
        print(f"CORS 测试数: {cors_analysis['cors_tests']}")
        print(f"包含 CORS 头: {cors_analysis['has_cors_headers']}")
        print(f"CORS 允许的来源: {', '.join(cors_analysis['cors_origins']) if cors_analysis['cors_origins'] else '无'}")
        print(f"CORS 已启用: {'是' if cors_analysis['cors_enabled'] else '否'}")
        print()
        
        print("=" * 80)
        print("详细测试结果")
        print("=" * 80)
        for i, result in enumerate(report['results'], 1):
            status_icon = "✅" if result['success'] else "❌"
            print(f"{i}. {status_icon} {result['name']}")
            print(f"   URL: {result['url']}")
            print(f"   路径: {result['path']}")
            print(f"   方法: {result['method']}")
            print(f"   状态码: {result['status']} (期望: {result['expected_status']})")
            print(f"   包含路径前缀: {'是' if result.get('has_path_prefix') else '否'}")
            
            if result.get('cors_headers'):
                cors = result['cors_headers']
                print(f"   CORS 头:")
                if cors.get('Access-Control-Allow-Origin'):
                    print(f"     - Access-Control-Allow-Origin: {cors['Access-Control-Allow-Origin']}")
                if cors.get('Access-Control-Allow-Methods'):
                    print(f"     - Access-Control-Allow-Methods: {cors['Access-Control-Allow-Methods']}")
            
            if result.get('error'):
                print(f"   错误: {result['error']}")
            
            print()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Nginx 路径转发测试脚本")
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
        help="路径前缀（默认: /ecom_reco_agent）"
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
    
    args = parser.parse_args()
    
    # 创建测试器并运行测试
    tester = NginxPathTester(
        base_url=args.url,
        path_prefix=args.prefix,
        agent_id=args.agent_id
    )
    
    report = tester.run_all_tests()
    tester.print_report(report)
    
    # 保存 JSON 报告
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n报告已保存到: {args.output}")
    
    # 返回退出码
    exit(0 if report['summary']['failed'] == 0 else 1)


if __name__ == "__main__":
    main()
