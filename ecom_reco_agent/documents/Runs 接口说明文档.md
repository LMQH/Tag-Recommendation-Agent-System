# runs 接口说明文档

## 概述

本文档说明AI自动装修助手的API接口。所有数据（聊天内容和推荐数据）通过同一个流式响应返回。

## 接口列表

- **POST /agents/ecom-reco-agent/runs** - Agent运行主接口（支持流式响应）

---

## POST /agents/ecom-reco-agent/runs

### 功能说明

Agent运行主接口，支持流式响应。返回混合事件流：包含聊天内容（RunOutput）和推荐数据（RecommendationDataEvent）。

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `message` | string | 是 | 用户消息 |
| `session_id` | string | 否 | 会话ID，用于关联对话历史。首次对话可不传，系统会自动创建新会话 |
| `user_id` | string | 否 | 用户ID，用于记忆功能。不传则使用空字符串，不会保存用户级记忆 |
| `stream` | boolean | 否 | 是否使用流式响应，默认为 `true` |

### 请求示例

```bash
curl -X POST "http://localhost:14466/agents/ecom-reco-agent/runs" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "message=推荐一些适合送礼的商品&session_id=your_session_id&user_id=user_12345&stream=true"
```

### 响应格式（流式SSE）

响应为Server-Sent Events (SSE)格式，包含多种类型的事件。根据 Agent 配置和运行状态，可能返回以下事件：

#### 核心事件（Core Events）

| 事件类型 | SSE event 字段值 | 说明 | 数据内容 |
|---------|-----------------|------|---------|
| `RunStarted` | `run_started` | 表示运行开始 | 包含 run_id 和初始状态信息 |
| `RunContent` | `run_content` | 模型响应的文本块（流式输出） | 包含 `content` 字段，为文本片段 |
| `RunContentCompleted` | `run_content_completed` | 内容流式输出完成 | 表示所有内容已输出完成 |
| `RunIntermediateContent` | `run_intermediate_content` | 模型的中间响应文本块（当设置了 output_model 时使用） | 包含 `content` 字段 |
| `RunCompleted` | `run_completed` | 运行成功完成 | 包含完整的运行结果和统计信息 |
| `RunError` | `run_error` | 运行过程中发生错误 | 包含错误信息和错误代码 |
| `RunCancelled` | `run_cancelled` | 运行被取消 | 包含取消原因 |

#### 控制流事件（Control Flow Events）

| 事件类型 | SSE event 字段值 | 说明 | 数据内容 |
|---------|-----------------|------|---------|
| `RunPaused` | `run_paused` | 运行已暂停 | 包含暂停原因（通常因工具需要确认而暂停） |
| `RunContinued` | `run_continued` | 暂停的运行已继续 | 包含继续执行的信息 |

#### 工具事件（Tool Events）

| 事件类型 | SSE event 字段值 | 说明 | 数据内容 |
|---------|-----------------|------|---------|
| `ToolCallStarted` | `tool_call_started` | 工具调用开始 | 包含工具名称、参数等信息 |
| `ToolCallCompleted` | `tool_call_completed` | 工具调用完成 | 包含工具执行结果 |

#### 推理事件（Reasoning Events）

| 事件类型 | SSE event 字段值 | 说明 | 数据内容 |
|---------|-----------------|------|---------|
| `ReasoningStarted` | `reasoning_started` | 推理过程开始 | 包含推理上下文信息 |
| `ReasoningStep` | `reasoning_step` | 推理过程中的单个步骤 | 包含步骤内容和步骤编号 |
| `ReasoningCompleted` | `reasoning_completed` | 推理过程完成 | 包含最终推理结果 |

#### 记忆事件（Memory Events）

| 事件类型 | SSE event 字段值 | 说明 | 数据内容 |
|---------|-----------------|------|---------|
| `MemoryUpdateStarted` | `memory_update_started` | Agent 开始更新记忆 | 包含记忆更新上下文 |
| `MemoryUpdateCompleted` | `memory_update_completed` | 记忆更新完成 | 包含更新后的记忆信息 |

#### 会话摘要事件（Session Summary Events）

| 事件类型 | SSE event 字段值 | 说明 | 数据内容 |
|---------|-----------------|------|---------|
| `SessionSummaryStarted` | `session_summary_started` | 会话摘要生成开始 | 包含会话上下文 |
| `SessionSummaryCompleted` | `session_summary_completed` | 会话摘要生成完成 | 包含生成的摘要内容 |

#### 钩子事件（Hook Events）

| 事件类型 | SSE event 字段值 | 说明 | 数据内容 |
|---------|-----------------|------|---------|
| `PreHookStarted` | `pre_hook_started` | 运行前钩子开始执行 | 包含钩子名称和参数 |
| `PreHookCompleted` | `pre_hook_completed` | 运行前钩子执行完成 | 包含钩子执行结果 |
| `PostHookStarted` | `post_hook_started` | 运行后钩子开始执行 | 包含钩子名称和参数 |
| `PostHookCompleted` | `post_hook_completed` | 运行后钩子执行完成 | 包含钩子执行结果 |

#### 解析模型事件（Parser Model Events）

| 事件类型 | SSE event 字段值 | 说明 | 数据内容 |
|---------|-----------------|------|---------|
| `ParserModelResponseStarted` | `parser_model_response_started` | 解析模型响应开始 | 包含解析请求信息 |
| `ParserModelResponseCompleted` | `parser_model_response_completed` | 解析模型响应完成 | 包含解析结果 |

#### 输出模型事件（Output Model Events）

| 事件类型 | SSE event 字段值 | 说明 | 数据内容 |
|---------|-----------------|------|---------|
| `OutputModelResponseStarted` | `output_model_response_started` | 输出模型响应开始 | 包含输出请求信息 |
| `OutputModelResponseCompleted` | `output_model_response_completed` | 输出模型响应完成 | 包含输出结果 |

#### 自定义事件（Custom Events）

| 事件类型 | SSE event 字段值 | 说明 | 数据内容 |
|---------|-----------------|------|---------|
| `RecommendationDataEvent` | `CustomEvent` | 推荐数据事件（本系统自定义） | 包含推荐数据，详见下方数据结构说明 |

**注意：** 
- 自定义事件的 `event` 字段值固定为 `"CustomEvent"`（Agno框架的默认值）
- 不同的事件类型可能以任意顺序出现在流式响应中
- 并非所有事件类型都会在每次运行中出现，具体取决于 Agent 配置和运行流程

### 数据格式说明

#### RecommendationDataEvent 数据结构

`RecommendationDataEvent` 是本系统自定义的事件类型，用于在流式响应中返回推荐数据。该事件通过 `CustomEvent` 类型发送。

**SSE 格式示例：**

```
event: CustomEvent
data: {
  "recommendations": [
    {
      "brandName": "苹果",
      "brandCode": "brand_001",
      "categoryName": "手机",
      "categoryCode": "category_001",
      "value": true
    }
  ],
  "total_count": 10,
  "festival_scenes": [
    {
      "festival_name": "春节",
      "scene_type": "节日营销"
    }
  ]
}
```

**TypeScript 类型定义：**

```typescript
interface RecommendationDataEvent {
    recommendations: RecommendationItem[];
    total_count: number;
    festival_scenes?: FestivalScene[];
}

interface RecommendationItem {
    brandName: string;         // 品牌名称，如 "苹果"
    brandCode: string;         // 品牌编码，如 "brand_001"
    categoryName: string;      // 品类名称，如 "手机"
    categoryCode: string;      // 品类编码，如 "category_001"
    value: boolean;            // 字段值，true=启用，false=禁用
}

interface FestivalScene {
    festival_name: string;     // 节日名称，如 "春节"
    scene_type: string;        // 场景类型，如 "节日营销"
}
```

#### 其他事件数据结构

其他标准事件的数据结构遵循 Agno 框架的规范，详细的数据结构请参考 [Agno AgentOS API 文档](https://opendeep.wiki/agno-agi/agno/api-reference)。

### 错误处理

#### HTTP错误码

- `200` - 成功（流式响应开始）
- `400` - 请求参数错误
- `404` - Agent不存在
- `500` - 服务器内部错误

#### 流式响应中的错误事件

当运行过程中发生错误时，会发送 `RunError` 事件，包含错误信息和错误代码。常见错误场景包括工具调用失败、模型响应超时、内存不足、网络连接问题等。

### 事件处理建议

1. **事件监听和处理**：由于这是 POST 请求，需要使用 `fetch` API 配合 `ReadableStream` 来接收 SSE 流，或使用专门的 SSE 解析库。前端应监听所有可能的事件类型，并根据 `event` 字段进行分发处理。

2. **事件顺序**：事件可能以任意顺序出现，不要依赖事件的严格顺序，应基于事件类型进行状态管理。通常遵循 `RunStarted` → `ToolCallStarted` → `ToolCallCompleted` → `RunContent` → `RunCompleted` 的模式，自定义事件可能在任意时刻出现。

3. **数据解析**：SSE 数据可能跨多行，需要正确处理换行符和缓冲区。每个事件的 `data` 字段是 JSON 字符串，需要解析。

4. **连接管理**：流式响应需要保持 HTTP 连接，注意处理网络断开重连、超时和用户取消操作。当收到 `RunCompleted` 或 `RunError` 事件时，应关闭连接。

5. **会话管理**：建议始终传递 `session_id` 以保持对话上下文。首次对话可以不传，系统会自动创建新会话；后续对话传入相同的 `session_id` 以保持上下文连续性。

6. **工具确认处理**：当工具调用需要用户确认时（`requires_confirmation=True`），会发送 `RunPaused` 事件。前端应提示用户进行确认，然后调用 `/agents/{agent_id}/runs/{run_id}/continue` 接口继续执行。

### 注意事项

1. **事件类型识别**：推荐数据的事件类型固定为 `"CustomEvent"`，需要通过 `data` 字段的内容来判断是否为推荐数据
2. **数据完整性**：`RunContent` 事件可能分多次发送，需要累积所有片段才能得到完整内容
3. **错误恢复**：遇到 `RunError` 事件时，应记录错误信息并关闭连接，避免继续等待
4. **性能优化**：对于高频事件（如 `RunContent`），建议使用防抖或节流来优化 UI 更新

---

## 参考

- [Agno AgentOS API 文档](https://opendeep.wiki/agno-agi/agno/api-reference)
- [Server-Sent Events (SSE) 规范](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
