import requests

# 测试不同路径的 CORS 头
paths = [
    "/ecom_reco_agent/health",
    "/ecom_reco_agent/sessions", 
    "/ecom_reco_agent/agents/ecom-reco-agent",
    "/ecom_reco_agent/agents/ecom-reco-agent/runs",
    "/ecom_reco_agent/v1/agents/ecom-reco-agent/chat",
]

headers = {"Origin": "https://example.com"}

for path in paths:
    url = f"https://ai-gateway-show.yunzhonghe.com{path}"
    try:
        resp = requests.get(url, headers=headers, timeout=5, allow_redirects=False)
        print(f"\n路径: {path}")
        print(f"状态码: {resp.status_code}")
        print("CORS 头:")
        for key, value in resp.headers.items():
            if 'access-control' in key.lower():
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"\n路径: {path}")
        print(f"错误: {e}")
