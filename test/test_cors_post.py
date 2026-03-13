import requests
import json

# 测试 POST /runs 端点
url = "https://ai-gateway-show.yunzhonghe.com/ecom_reco_agent/agents/ecom-reco-agent/runs"
headers = {
    "Origin": "https://example.com",
    "Content-Type": "application/json"
}
data = {
    "message": "你好",
    "stream_events": False  # 不使用流式，方便测试
}

try:
    # 只测试 POST 请求的前几秒，不等待完整响应
    resp = requests.post(url, json=data, headers=headers, timeout=3, stream=True)
    print(f"状态码: {resp.status_code}")
    print("CORS 头:")
    for key, value in resp.headers.items():
        if 'access-control' in key.lower():
            print(f"  {key}: {value}")
    
    # 读取一小部分响应
    try:
        chunk = next(resp.iter_content(1024))
        print(f"\n响应前几个字节: {chunk[:100]}")
    except:
        pass
        
except requests.exceptions.Timeout:
    print("请求超时（这是正常的，因为是流式响应）")
except Exception as e:
    print(f"错误: {e}")

print("\n" + "="*60)

# 也测试一下 OPTIONS 预检
print("\n测试 OPTIONS 预检:")
options_headers = {
    "Origin": "https://example.com",
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "content-type"
}
try:
    resp = requests.options(url, headers=options_headers, timeout=5)
    print(f"OPTIONS 状态码: {resp.status_code}")
    print("OPTIONS CORS 头:")
    for key, value in resp.headers.items():
        if 'access-control' in key.lower():
            print(f"  {key}: {value}")
except Exception as e:
    print(f"OPTIONS 错误: {e}")
