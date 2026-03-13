# AGNO 路由说明文档

## 概述

AGNO (AgentOS) 提供了三种不同的路由集成方案，适用于不同的使用场景。本文档将详细说明这三种方案的特点、适用场景，以及如何在 Nginx 网关环境下处理跨域访问。

## 目录

1. [方案一：get_app() - AgentOS 全权管理](#方案一get_app---agentos-全权管理)
2. [方案二：base_app - 合并模式（推荐）](#方案二base_app---合并模式推荐)
3. [方案三：get_routes() - 手动追加路由](#方案三get_routes---手动追加路由)
4. [Nginx 网关与跨域访问场景分析](#nginx-网关与跨域访问场景分析)
5. [方案对比与选择建议](#方案对比与选择建议)

---

## 方案一：get_app() - AgentOS 全权管理

### 基本用法

```python
from agno.os import AgentOS
from agno.agent import Agent

# 创建 AgentOS 实例
agent_os = AgentOS(agents=[agent])

# 直接获取 FastAPI app
app = agent_os.get_app()
```

### 特点说明

| 项目 | 说明 |
|------|------|
| **AgentOS 挂载位置** | AgentOS 自己创建 FastAPI app，路由直接注册在根路径 |
| **CORS 处理** | AgentOS 自动添加 CORSMiddleware（含默认 Agno 域名 + 你的 cors_allowed_origins） |
| **路由** | 全部是 AgentOS 的内置路由（/runs、/sessions、/health 等 50+ 端点） |
| **自定义能力** | ❌ 无法添加自定义路由或中间件 |
| **适用场景** | 纯 AgentOS 服务，不需要自定义接口 |

### 优点

- **简单直接**：无需额外配置，开箱即用
- **自动管理**：CORS、中间件、异常处理等均由 AgentOS 自动处理
- **零配置**：适合快速原型和纯 AgentOS 应用

### 缺点

- **灵活性受限**：无法添加自定义路由
- **无法扩展**：无法添加自定义中间件
- **完全依赖**：应用生命周期完全由 AgentOS 管理

### 使用示例

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.os import AgentOS

# 创建 Agent
agent = Agent(
    id="my-agent",
    model=OpenAIChat(id="gpt-4"),
    instructions="You are a helpful assistant."
)

# 创建 AgentOS（默认模式）
agent_os = AgentOS(
    agents=[agent],
    cors_allowed_origins=["https://example.com"]  # 可配置允许的跨域来源
)

# 获取 app
app = agent_os.get_app()

# 启动服务
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7777)
```

---

## 方案二：base_app - 合并模式（推荐）

### 基本用法

```python
from fastapi import FastAPI
from agno.os import AgentOS

# 创建自己的 FastAPI app
app = FastAPI(title="My App")

# 添加自定义路由
@app.get("/status")
async def status():
    return {"status": "ok"}

# 将 AgentOS 合并到现有 app
agent_os = AgentOS(agents=[agent], base_app=app)

# 获取合并后的 app
app = agent_os.get_app()  # 返回合并后的 app
```

### 特点说明

| 项目 | 说明 |
|------|------|
| **AgentOS 挂载位置** | AgentOS 将自己的路由合并注入到你的 base_app 中，同一个 app、同一层级 |
| **CORS 处理** | 如果 base_app 已有 CORSMiddleware → AgentOS 只更新 allowed origins；没有 → AgentOS 新增 |
| **路由** | 你的自定义路由 + AgentOS 内置路由共存，冲突通过 on_route_conflict 控制 |
| **自定义能力** | ✅ 完全支持自定义路由、中间件、依赖注入 |
| **适用场景** | 需要自定义接口 + 保留 AgentOS 全部功能 |

### 路由冲突处理

AgentOS 提供了 `on_route_conflict` 参数来控制路由冲突时的行为：

```python
agent_os = AgentOS(
    agents=[agent],
    base_app=app,
    on_route_conflict="preserve_base_app"  # 或 "preserve_agentos" 或 "error"
)
```

- `"preserve_base_app"`：保留你的自定义路由，跳过冲突的 AgentOS 路由
- `"preserve_agentos"`：保留 AgentOS 路由，跳过冲突的自定义路由（默认）
- `"error"`：遇到冲突时抛出异常

### 路径前缀处理

使用 `root_path` 而非 `mount` 来处理路径前缀：

```python
from fastapi import FastAPI
from agno.os import AgentOS

# 使用 root_path 设置 API 前缀
app = FastAPI(title="My App", root_path="/api/v1")

agent_os = AgentOS(agents=[agent], base_app=app)
app = agent_os.get_app()
```

### 优点

- **灵活性高**：可以添加任意自定义路由和中间件
- **功能完整**：保留 AgentOS 所有内置功能
- **CORS 智能合并**：自动处理 CORS 配置，避免重复
- **路由冲突可控**：通过参数控制冲突处理策略

### 缺点

- **配置稍复杂**：需要创建 base_app 并管理合并过程
- **需要理解路由冲突**：需要了解如何处理路由冲突

### 使用示例

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.os import AgentOS

# 创建自定义 FastAPI app
app = FastAPI(title="My Custom App")

# 添加自定义 CORS（可选，AgentOS 会自动合并）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myfrontend.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加自定义路由
@app.get("/api/custom/status")
async def custom_status():
    return {"service": "running", "version": "1.0.0"}

@app.get("/api/custom/users")
async def get_users():
    return {"users": ["user1", "user2"]}

# 创建 Agent
agent = Agent(
    id="my-agent",
    model=OpenAIChat(id="gpt-4"),
    instructions="You are a helpful assistant."
)

# 合并 AgentOS（推荐使用 preserve_base_app 保留自定义路由）
agent_os = AgentOS(
    agents=[agent],
    base_app=app,
    on_route_conflict="preserve_base_app",  # 自定义路由优先
    cors_allowed_origins=["https://myfrontend.com", "https://agno.com"]
)

# 获取合并后的 app
app = agent_os.get_app()

# 启动服务
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7777)
```

---

## 方案三：get_routes() - 手动追加路由

### 基本用法

```python
from fastapi import FastAPI
from agno.os import AgentOS

# 创建 AgentOS（不传入 base_app）
agent_os = AgentOS(agents=[agent])

# 创建自己的 FastAPI app
app = FastAPI(title="My App")

# 手动追加 AgentOS 的路由
for route in agent_os.get_routes():
    app.router.routes.append(route)
```

### 特点说明

| 项目 | 说明 |
|------|------|
| **AgentOS 挂载位置** | AgentOS 不挂载任何 app，只提供路由列表，由你手动追加到自己的 app |
| **CORS 处理** | AgentOS 完全不参与 CORS，你的 app 完全自主控制中间件栈 |
| **路由** | AgentOS 的路由作为"零件"被你挑选使用 |
| **自定义能力** | ✅✅ 最大自由度，完全掌控 app 生命周期 |
| **适用场景** | Nginx 管理 CORS 的场景最适合——Nginx 管 CORS，应用层零 CORS |

### 优点

- **完全控制**：对 app 生命周期有完全控制权
- **灵活选择**：可以选择性地添加 AgentOS 路由
- **CORS 独立**：CORS 完全由你或 Nginx 管理，AgentOS 不干预
- **适合网关场景**：非常适合 Nginx 反向代理场景

### 缺点

- **手动管理**：需要手动管理路由添加
- **可能遗漏**：需要确保添加了所有需要的路由
- **配置复杂**：需要理解 AgentOS 的路由结构

### 使用示例

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.os import AgentOS

# 创建 Agent
agent = Agent(
    id="my-agent",
    model=OpenAIChat(id="gpt-4"),
    instructions="You are a helpful assistant."
)

# 创建 AgentOS（不传入 base_app）
agent_os = AgentOS(agents=[agent])

# 创建自己的 FastAPI app
app = FastAPI(title="My Custom App")

# 添加自定义 CORS（如果需要，但通常由 Nginx 处理）
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# 添加自定义路由
@app.get("/api/custom/health")
async def health():
    return {"status": "healthy"}

# 手动追加 AgentOS 的路由
for route in agent_os.get_routes():
    # 可以在这里过滤不需要的路由
    if not route.path.startswith("/docs"):  # 例如：排除文档路由
        app.router.routes.append(route)

# 启动服务
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7777)
```

---

## Nginx 网关与跨域访问场景分析

### 场景描述

在实际生产环境中，常见的架构是：

```
前端 (Frontend)
    ↓
Nginx 网关 (反向代理 + CORS 处理)
    ↓
后端服务 (AgentOS)
```

在这种架构下，CORS 通常由 Nginx 统一处理，后端应用不需要关心跨域问题。

### 方案选择建议

#### 场景 1：纯 AgentOS 服务，Nginx 处理 CORS

**推荐方案：方案三（get_routes()）**

```python
from fastapi import FastAPI
from agno.os import AgentOS

# 创建 AgentOS
agent_os = AgentOS(agents=[agent])

# 创建 FastAPI app（不添加 CORS 中间件）
app = FastAPI(title="AgentOS Service")

# 手动追加 AgentOS 路由
for route in agent_os.get_routes():
    app.router.routes.append(route)
```

**Nginx 配置示例：**

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://localhost:7777;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS 处理
        add_header 'Access-Control-Allow-Origin' '$http_origin' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type' always;
        add_header 'Access-Control-Allow-Credentials' 'true' always;

        # 处理 OPTIONS 预检请求
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' '$http_origin' always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
            add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type' always;
            add_header 'Access-Control-Max-Age' 1728000;
            add_header 'Content-Type' 'text/plain; charset=utf-8';
            add_header 'Content-Length' 0;
            return 204;
        }
    }
}
```

#### 场景 2：AgentOS + 自定义 API，Nginx 处理 CORS

**推荐方案：方案二（base_app）**

```python
from fastapi import FastAPI
from agno.os import AgentOS

# 创建自定义 app
app = FastAPI(title="My App")

# 添加自定义路由
@app.get("/api/custom/status")
async def status():
    return {"status": "ok"}

# 合并 AgentOS
agent_os = AgentOS(agents=[agent], base_app=app)
app = agent_os.get_app()
```

**注意**：即使使用方案二，如果 Nginx 处理 CORS，也可以选择不在应用层添加 CORS 中间件，让 AgentOS 的 CORS 配置为空或最小化。

#### 场景 3：无 Nginx，应用层处理 CORS

**推荐方案：方案一或方案二**

- **方案一**：如果不需要自定义路由
- **方案二**：如果需要自定义路由

```python
# 方案一示例
agent_os = AgentOS(
    agents=[agent],
    cors_allowed_origins=["https://frontend.example.com"]
)
app = agent_os.get_app()

# 方案二示例
app = FastAPI(title="My App")
agent_os = AgentOS(
    agents=[agent],
    base_app=app,
    cors_allowed_origins=["https://frontend.example.com"]
)
app = agent_os.get_app()
```

### Nginx + AgentOS 最佳实践

#### 1. 路径前缀处理

如果使用 Nginx 作为网关，建议在 Nginx 层面处理路径前缀：

```nginx
# Nginx 配置
location /api/v1/ {
    proxy_pass http://localhost:7777/;  # 注意末尾的斜杠
    # ... 其他配置
}
```

或者在后端使用 `root_path`：

```python
# Python 代码
app = FastAPI(title="My App", root_path="/api/v1")
agent_os = AgentOS(agents=[agent], base_app=app)
app = agent_os.get_app()
```

#### 2. WebSocket 支持

如果使用 WebSocket，需要在 Nginx 中配置：

```nginx
location / {
    proxy_pass http://localhost:7777;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    # ... 其他配置
}
```

#### 3. 健康检查端点

建议在 Nginx 层面配置健康检查：

```nginx
location /health {
    proxy_pass http://localhost:7777/health;
    access_log off;
}
```

---

## 方案对比与选择建议

### 功能对比表

| 特性 | 方案一：get_app() | 方案二：base_app | 方案三：get_routes() |
|------|------------------|------------------|---------------------|
| **自定义路由** | ❌ | ✅ | ✅ |
| **自定义中间件** | ❌ | ✅ | ✅ |
| **CORS 自动处理** | ✅ | ✅（智能合并） | ❌（完全自主） |
| **路由冲突控制** | N/A | ✅ | N/A |
| **配置复杂度** | ⭐ 简单 | ⭐⭐ 中等 | ⭐⭐⭐ 复杂 |
| **灵活性** | ⭐ 低 | ⭐⭐ 中 | ⭐⭐⭐ 高 |
| **适用 Nginx 网关** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

### 选择决策树

```
需要自定义路由或中间件？
├─ 否 → 使用方案一（get_app()）
└─ 是 → Nginx 处理 CORS？
    ├─ 是 → 使用方案三（get_routes()）
    └─ 否 → 使用方案二（base_app）
```

### 具体场景推荐

1. **快速原型开发**
   - 推荐：方案一
   - 原因：简单快速，无需额外配置

2. **生产环境 + Nginx 网关**
   - 推荐：方案三
   - 原因：CORS 由 Nginx 统一管理，应用层零 CORS 配置

3. **需要自定义 API + AgentOS 功能**
   - 推荐：方案二
   - 原因：平衡了灵活性和易用性

4. **微服务架构**
   - 推荐：方案二或方案三
   - 原因：需要灵活的路由和中间件控制

5. **纯 AgentOS 服务**
   - 推荐：方案一
   - 原因：最简单直接

---

## 总结

AGNO 提供了三种灵活的路由集成方案，每种方案都有其适用场景：

- **方案一**：适合快速开发和纯 AgentOS 应用
- **方案二**：适合需要自定义功能但保留 AgentOS 全部能力的场景（**最推荐**）
- **方案三**：适合需要完全控制应用生命周期，特别是 Nginx 网关场景

在 Nginx 网关环境下，**方案三（get_routes()）** 是最佳选择，因为它允许你完全控制 CORS 配置，让 Nginx 统一处理跨域问题，实现关注点分离。

---

## 参考资源

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Nginx 反向代理配置](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [CORS 跨域资源共享](https://developer.mozilla.org/zh-CN/docs/Web/HTTP/CORS)

---

*文档版本：1.0*  
*最后更新：2024*
