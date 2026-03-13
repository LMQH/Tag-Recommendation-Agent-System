# Agno Workflow 迁移方案 A：保留 Agent 接口（前端尽可能不改）

## 方案目标

- **对外接口**：继续使用 `POST /agents/ecom-reco-agent/runs`，请求参数与响应格式与当前一致，**前端无需改动**。
- **内部实现**：用 Agno v2 **声明式 Workflow**（Step、Loop、Condition）替代 prompt 驱动的 7 阶段流程，流程控制由代码接管，不再覆写 `Workflow.run()`。

## 与 Agno v2 的对应关系

- Agno v2 的 `Workflow` 为**声明式**，不支持子类覆写 `run()`。
- 本方案在**内部**使用声明式 Workflow 执行逻辑，对外通过**自定义 FastAPI 兼容路由**保留 `/agents/ecom-reco-agent/runs`，并将 Workflow 的执行结果**转成与现有 Agent Run 一致的 SSE 事件流**，保证前端解析逻辑不变。

---

## 一、向后兼容约定（前端不变）

| 项目 | 约定 |
|------|------|
| **主入口** | `POST /agents/ecom-reco-agent/runs`（不变） |
| **Content-Type** | `application/x-www-form-urlencoded` |
| **请求参数** | `message`（必填）、`session_id`（可选）、`user_id`、`stream`、`version`、`background` 等与现有一致 |
| **响应** | SSE 流式；事件类型保持现有（如 `run_started`、`run_content`、`run_paused`、`run_completed` 及工具/推理事件） |
| **会话** | 不传或传空 `session_id` 自动创建新会话；传已有 `session_id` 继续该会话；HITL 确认流程不变 |
| **会话管理** | `GET /sessions`、`GET /sessions/{session_id}`、`GET /sessions/{session_id}/runs` 等行为不变，仍按 `type=agent` 使用 |

---

## 二、整体架构

```
前端
  │  POST /agents/ecom-reco-agent/runs (message, session_id, stream, ...)
  ▼
┌─────────────────────────────────────────────────────────────────┐
│  兼容层（FastAPI 自定义路由 + 响应转换）                           │
│  - 接收与现有 Agent 相同的 form 参数                             │
│  - 调用内部 Workflow 执行（传入 message、session_id 等）          │
│  - 将 Workflow 输出转换为 Agent 风格的 SSE 事件并流式返回           │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│  声明式 Workflow（Agno v2）                                       │
│  steps = [ Step(analyze_intent), Step(festival), Loop(query_retry),│
│            Step(integrate) ]                                      │
│  session_state 持久化、子 Agent 与 executor 同上                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、声明式 Workflow 设计（内部实现）

使用 Agno v2 的 `Workflow(steps=[...])`，不覆写 `run()`。各阶段用 `Step(executor=...)` 或 `Step(agent=...)` 表示；回退逻辑用 `Loop(max_iterations=3, end_condition=...)`。

### 3.1 步骤与结构

```python
from agno.workflow import Workflow, Step, Loop
from agno.workflow.step import StepInput, StepOutput
from agno.db.sqlite import SqliteDb

# 各 executor 为自定义函数，签名 (step_input: StepInput, run_context: RunContext) -> StepOutput
# 或直接使用 agent=xxx_agent

workflow = Workflow(
    name="ecom-reco-workflow",
    id="ecom-reco-workflow",  # 仅内部使用，对外不暴露此路径
    db=SqliteDb(db_url="sqlite:///...", session_table="ecom_reco_workflow_sessions"),
    session_state={
        "user_intent": {},
        "is_continuation": False,
        "festival_scenes": [],
        "query_results": {},
        "last_build_review_result": None,
        "retry_count": 0,
    },
    steps=[
        Step(name="analyze_intent", executor=stage1_analyze_intent),
        Step(name="recommend_festivals", executor=stage2_recommend_festivals),
        Step(name="normalize_and_plan", executor=stage3_4_normalize_and_plan),
        Loop(
            name="query_retry",
            max_iterations=3,
            end_condition=is_query_sufficient,
            steps=[
                Step(name="query_database", executor=stage5_query_database),
            ],
        ),
        Step(name="integrate_and_output", agent=integration_agent),
    ],
)
```

### 3.2 Executor 与 RunContext

- 各阶段逻辑放在 **executor 函数**中，通过 `run_context.session_state` 读写跨轮次状态。
- 续接与 HITL：`session_state["last_build_review_result"]`、`session_state["is_continuation"]` 等与现有语义一致，便于兼容层在「Agent session」与「Workflow session」之间做映射或复用。

示例（阶段 1）：

```python
def stage1_analyze_intent(step_input: StepInput, run_context: RunContext) -> StepOutput:
    message = step_input.input  # 或从 run_context 取
    response = intent_agent.run(f"分析用户意图：{message}", stream=False)
    intent_result = response.content.model_dump()
    run_context.session_state["user_intent"] = intent_result
    run_context.session_state["is_continuation"] = intent_result.get("is_continuation", False)
    return StepOutput(content=intent_result)
```

### 3.3 Loop 与 end_condition

- `end_condition`：接收当前 Loop 内 step 的 outputs，返回 `True` 表示结束循环。
- 查询是否充足（如各节日至少 3 条）在该 callable 中判断，与现有「回退细化」逻辑等价。

```python
def is_query_sufficient(outputs: List[StepOutput]) -> bool:
    # 从 outputs 或 run_context.session_state["query_results"] 判断
    results = ...  # 从最后一步输出或 session_state 取
    return bool(results) and all(len(v) >= 3 for v in results.values())
```

### 3.4 子 Agent 与数据模型

- 与方案 B 共用：`intent_agent`、`festival_agent`、`category_agent`、`query_agent`、`integration_agent`；各 Agent 的 `response_model`、工具、提示词设计一致。
- `sub_agents/models.py` 中 Pydantic 模型（IntentResult、FestivalResult、CategoryResult、QueryResult 等）共用。

---

## 四、兼容层实现要点

### 4.1 自定义路由

- 在现有 FastAPI app 上**优先**注册：`POST /agents/ecom-reco-agent/runs`（与 AgentOS 的 agents 路由路径一致时，需保证该自定义路由优先或替代默认 agent 路由，具体依框架路由顺序而定）。
- Handler 从 request 读取 form：`message`、`session_id`、`stream`、`user_id` 等，与现有接口文档一致。

### 4.2 调用 Workflow 并绑定 Session

- 使用 Agno 提供的「按 session 运行 workflow」的方式（如带 `session_id` 的 run 接口或等价 API），将请求中的 `session_id` 传入，确保 Workflow 使用同一 session 的 `session_state`，实现续接与 HITL。
- 若框架以 workflow 为单位管理 session，需在兼容层维护 **agent session_id ↔ workflow session_id** 的映射（或统一使用同一 session 存储，仅 type 不同），以便 `GET /sessions?type=agent` 等仍可用。

### 4.3 响应格式转换（关键）

- Workflow 原生返回的可能是 `WorkflowRunOutput`（含 `step_results`、`step_executor_runs` 等）及 Workflow 特有 SSE 事件（如 `workflow_started`、`step_started`）。
- 兼容层需将流式输出**转换为**当前前端所期望的 Agent Run 事件序列，例如：
  - `run_started` / `run_content` / `run_content_completed` / `run_completed`
  - `run_paused` / `run_continued`
  - 工具/推理等现有事件类型
- 这样前端**无需修改**现有 SSE 解析与展示逻辑。

### 4.4 会话列表与详情

- 若仍希望 `GET /sessions`、`GET /sessions/{session_id}` 返回与现在一致的 Agent 会话结构，可选做法：
  - 继续使用现有 Agent 的 session 存储，兼容层在调用 Workflow 时把「agent session_id」传给 Workflow 的 session 上下文；或
  - 使用 Workflow session 存储，但在兼容层或单独接口中，按需将 workflow session 转成 agent 会话视图（仅当需要完全一致时）。

---

## 五、目录与文件

| 文件/目录 | 说明 |
|-----------|------|
| `workflows/ecom_reco_workflow.py` | 声明式 Workflow 定义（steps、Loop、end_condition） |
| `workflows/step_executors.py` | 各阶段 executor 函数（stage1_analyze_intent 等） |
| `sub_agents/` | 与方案 B 共用（models、intent/festival/category/query/integration agents） |
| `agent/agent_os.py` | 注册 AgentOS；**不再**将当前业务注册为 agents，改为挂载自定义路由 |
| `agent/compat_routes.py` | **新建**：`POST /agents/ecom-reco-agent/runs` 的实现及 SSE 转换逻辑 |
| `prompts/` | 精简后的 system + stage_prompts，与方案 B 共用 |

---

## 六、实施顺序建议

1. 实现声明式 Workflow + 各 Step executor + Loop，在**内部**用 `workflow.run(message)` 或等价 API 自测通过。
2. 实现兼容层：自定义路由、session_id 传递、Workflow 调用。
3. 实现 SSE 转换：Workflow 输出 → Agent 风格事件流，用现有前端或 curl 校验事件类型与顺序。
4. 确认会话与续接、HITL 行为与现有一致；必要时调整 session 映射或存储策略。
5. 清理：移除或替换原单体 Agent 的注册，避免与兼容路由重复。

---

## 七、风险与注意

- **响应转换**：依赖 Agno Workflow 的 SSE 事件与 RunOutput 结构，若框架升级导致事件类型或字段变化，需同步更新兼容层。
- **Session 双轨**：若同时保留 Agent 会话与 Workflow 会话，需明确以哪一侧为事实来源，避免列表/详情不一致。
- **维护成本**：兼容层需长期维护，适合「前端不能改、必须保留原接口」的场景；若未来允许前端改一次，可评估切到方案 B 以降低复杂度。

---

## 八、验证清单

- [ ] 使用现有前端或 curl，不改 URL/参数，调用 `POST /agents/ecom-reco-agent/runs`，能收到与迁移前一致的 SSE 事件类型与顺序。
- [ ] 同一 `session_id` 续接对话、HITL 确认流程与现有一致。
- [ ] `GET /sessions?type=agent`、`GET /sessions/{session_id}` 行为符合当前前端预期。
- [ ] 内部 Workflow 各 Step、Loop 执行正确，`session_state` 持久化与续接正确。
