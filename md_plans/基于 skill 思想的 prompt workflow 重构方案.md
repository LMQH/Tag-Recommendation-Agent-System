# 基于 skill 思想的 prompt workflow 重构方案

## 1. 背景与目标

当前系统将完整的系统提示词、7 阶段 workflow 细则、reasoning 说明一次性拼接后注入 Agent 运行时。该方式的优点是实现直接，但问题也比较明显：

- 每轮请求都重复注入大段固定说明，prompt token 成本高
- 模型在首包前需要先消化整套规则，拉长 `time_to_first_token`
- 规则、示例、流程、格式要求混杂在一起，维护和迭代成本高
- 一些本应由代码保证的约束，被放在 prompt 中反复提醒，收益递减

本方案借鉴 skill 的设计思想，将现有大 prompt 拆分为：

- 常驻核心约束
- 阶段级短 prompt
- 按需加载的 reference

目标不是单纯“改写文案”，而是建立一套更轻、更稳、更易维护的 prompt workflow 组织方式，使系统从“全量注入”转向“按需暴露”。

---

## 2. 设计原则

### 2.1 渐进加载

参考 skill 的 progressive disclosure 思路，将提示信息分为三层：

1. 常驻层：每轮都要注入，内容必须足够短，只保留高价值、不可丢失的约束
2. 阶段层：仅在对应阶段注入，描述该阶段目标、输入、允许工具、退出条件
3. 参考层：仅在需要时读取，不进入每轮上下文，包含详细示例、边界规则、复杂数据格式说明

### 2.2 代码优先于文案

凡是可以被代码稳定保证的规则，不再长期停留在 prompt 中反复声明。例如：

- 阶段跳转
- 数据结构校验
- 去重规则
- 工具入参格式
- 回退次数上限

prompt 应主要承担“指导模型做判断”的职责，而不是承担“替代代码控制器”的职责。

### 2.3 提示词最小闭包

每一层 prompt 只保留完成当前任务所必需的最小信息闭包：

- 角色是什么
- 当前阶段要做什么
- 可以用什么工具
- 不允许做什么
- 输出给谁看，输出什么

避免重复放入：

- 全量阶段说明
- 大段 JSON 示例
- 多处重复出现的硬性约束
- 与当前阶段无关的工具细节

### 2.4 文档化但不常驻

复杂规则不能丢，但不应该每轮都进入上下文。它们应移动到 reference 文档中，由代码或运行时按需加载。

---

## 3. 当前问题拆解

结合现有实现，当前 prompt 组织存在以下结构性问题：

### 3.1 全量注入

当前 `SYSTEM_INSTRUCTIONS` 由完整 workflow 与 reasoning instructions 拼接而成，每轮都进入上下文。

### 3.2 规则重复

以下信息在系统 prompt、workflow、reasoning 中存在重复表达：

- 必须先 think
- 数据必须真实，禁止编造
- festival/category/brand 的来源约束
- analyze 的使用时机
- 输出风格限制

### 3.3 示例占用上下文

`build_review_fields` 的长示例、数据结构示例、禁用工具说明等，属于高价值文档，但不适合每轮常驻。

### 3.4 阶段信息耦合

阶段 1 到阶段 7 的说明紧密串在一起，即便当前只运行某一个阶段，模型也需要阅读所有阶段内容。

### 3.5 运行时与设计文档混在一起

运行时 prompt 中包含大量“给开发者看的说明”，这些内容对模型执行帮助有限，却持续消耗 token。

---

## 4. 重构总体方案

### 4.1 新的 prompt 分层

建议将运行时 prompt 重构为以下三层：

#### A. 常驻核心约束 Core Prompt

每轮注入，目标控制在 300 到 800 中文字以内。只保留：

- 角色定义
- 数据真实性要求
- 语言要求
- 工具使用总原则
- 输出总原则

#### B. 阶段级短 Prompt Stage Prompt

按阶段动态注入，仅在当前阶段存在。每个阶段建议控制在 120 到 300 中文字以内。只说明：

- 当前阶段目标
- 已知输入
- 可用工具
- 本阶段禁止事项
- 阶段完成条件

#### C. 按需 Reference

不进入默认上下文，只有满足条件时才读取或摘要注入。包括：

- 数据格式 reference
- 节日匹配 reference
- 品类标准化 reference
- 历史对话整合 reference
- 最终输出格式 reference

---

## 5. 推荐的新目录结构

建议在现有 `ecom_reco_agent/prompts/` 下重构为：

```text
ecom_reco_agent/
  prompts/
    __init__.py
    core.py
    stages/
      stage_01_requirement.md
      stage_02_festival.md
      stage_03_category.md
      stage_04_planning.md
      stage_05_query.md
      stage_06_integration.md
      stage_07_confirmation.md
    references/
      data-format.md
      festival-matching.md
      category-normalization.md
      continuation-rules.md
      output-style.md
    builders/
      prompt_registry.py
      prompt_loader.py
      context_selector.py
```

说明：

- `core.py` 保存常驻核心约束
- `stages/` 保存阶段级短 prompt
- `references/` 保存按需文档
- `builders/` 负责根据当前阶段和上下文选择需要注入的内容

---

## 6. 各层内容设计

### 6.1 常驻核心约束

建议保留以下内容：

#### 角色

- 你是电商推荐选品助手
- 目标是基于真实工具查询结果输出推荐结果

#### 数据真实性

- 只允许使用工具返回的真实数据
- 禁止编造 brandCode、categoryCode、festival_scenes
- 查询为空时必须明确视为无结果，不自行补全

#### 执行原则

- 必须遵循当前阶段指令
- 不输出内部思考过程
- 仅在允许的阶段生成面向用户的总结文本

#### 语言与风格

- 对用户始终使用中文
- 非输出阶段不产生多余自然语言

不建议保留在常驻层的内容：

- 7 个阶段的详细说明
- 复杂示例
- 历史整合细节
- 每个工具的参数说明
- analyze 的完整风格模板

### 6.2 阶段级短 prompt

每个阶段只保留最小闭包。

#### 阶段 1：需求解析与规划

保留：

- 判断新需求还是继续对话
- 如为继续对话，检查是否存在历史推荐结果
- 输出下一阶段决策

移出：

- 历史解析的完整长说明
- 多组关键词示例

#### 阶段 2：节日匹配

保留：

- 获取日期信息和节日全集
- 只提取与用户意图匹配的 festival_scenes
- 无匹配时必须保存空列表

移出：

- 详细反例
- 大量禁用场景展开说明

#### 阶段 3：品类标准化

保留：

- 优先使用用户明确品类，否则结合节日推断候选品类
- 调用标准化工具
- 优先三/f级粒度结果

移出：

- 多个节日与品类映射的扩展示例

#### 阶段 4：查询规划

保留：

- 基于节日与品类关系形成查询计划
- 优先选择细粒度品类进入查询

移出：

- 重复出现的节日样例

#### 阶段 5：商品库查询

保留：

- 按节日分组查询
- 记录每个节日对应的查询结果
- 结果不足时允许回退细化

移出：

- 长篇回退说明
- 展开式举例

#### 阶段 6：结果整合与输出

保留：

- 将数据按节日分组传入 `build_review_fields`
- 有历史时执行整合策略
- 仅在此阶段生成面向用户的摘要

移出：

- 大段 JSON 输入输出示例
- 所有去重细节

#### 阶段 7：最终确认

保留：

- 判断用户是否确认
- 确认则发送最终结果并生成最终摘要
- 否则回到阶段 1

移出：

- 确认分支的长篇解释

### 6.3 按需 reference

按主题拆分，而不是按文件长度拆分。

推荐拆分如下：

#### `data-format.md`

包含：

- `build_review_fields` 入参要求
- 返回结构说明
- 去重规则
- 关键字段说明

触发时机：

- 阶段 6 前
- 数据结构校验失败时
- 调试模式下

#### `festival-matching.md`

包含：

- 节日筛选规则
- 用户明确指定节日但数据库无匹配时的处理
- `save_matched_festivals([])` 的语义

触发时机：

- 阶段 2
- 节日匹配异常时

#### `category-normalization.md`

包含：

- `search_category_by_name` 使用策略
- `category_level` 选择规则
- 细化和回退策略

触发时机：

- 阶段 3
- 阶段 5 回退时

#### `continuation-rules.md`

包含：

- 新需求/继续对话识别规则
- 历史推荐结果提取策略
- 历史数据可整合与不可整合边界

触发时机：

- 阶段 1
- 阶段 6 历史整合时

#### `output-style.md`

包含：

- 阶段 6 和阶段 7 的输出风格
- Markdown 表格要求
- 友好语气限制

触发时机：

- 阶段 6 输出前
- 阶段 7 输出前

---

## 7. 运行时装配方案

### 7.1 新的装配原则

运行时不再使用：

- `完整 workflow + reasoning + 所有规则 + 所有示例`

改为：

- `core prompt + 当前阶段 prompt + 需要的少量 reference 摘要`

### 7.2 推荐装配公式

每轮运行上下文建议近似为：

```text
Runtime Prompt =
  CorePrompt
  + StagePrompt(current_stage)
  + OptionalReferenceSummary(selected_by_context)
  + ConversationStateSummary
  + UserInput
```

其中：

- `CorePrompt` 常驻
- `StagePrompt` 只取当前阶段
- `OptionalReferenceSummary` 只在必要时追加
- `ConversationStateSummary` 用结构化摘要替代长历史

### 7.3 reference 的加载方式

建议不要把 reference 全文直接注入模型，而是使用两步法：

1. 代码判断当前阶段需要哪份 reference
2. 将 reference 提炼成 3 到 8 条摘要后再注入

这样可以避免 reference 再次演化成“大 prompt 第二版”。

---

## 8. 推荐的数据流与控制流改造

### 8.1 从“prompt 控流程”转为“代码控流程”

建议引入轻量级 workflow controller，负责：

- 记录当前阶段
- 管理阶段跳转
- 控制回退次数
- 决定需要加载哪些 reference
- 生成结构化状态摘要

模型只负责：

- 当前阶段判断
- 当前阶段工具调用决策
- 当前阶段结果解释

### 8.2 建议新增的运行时对象

```python
class PromptContext:
    current_stage: str
    is_continuation: bool
    has_history_result: bool
    needs_data_format_ref: bool
    needs_output_style_ref: bool
    retry_count: int
    state_summary: str
```

```python
class PromptBundle:
    core_prompt: str
    stage_prompt: str
    references: list[str]
    final_prompt: str
```

### 8.3 推荐的选择器职责

#### `prompt_registry.py`

负责注册：

- core prompt
- 各阶段 prompt
- references 元信息

#### `context_selector.py`

负责根据运行状态决定：

- 当前阶段 prompt
- 需要加载哪些 reference
- 是否只注入 reference 摘要

#### `prompt_loader.py`

负责：

- 读取 prompt 文件
- 缓存内容
- 生成最终运行时 prompt

---

## 9. 预期收益评估

### 9.1 token 收益

在不改变业务逻辑的前提下，这一方案预计可以取得以下收益：

- 常驻 prompt 体积下降明显
- 绝大部分请求不再携带完整 7 阶段细则
- 示例与格式文档退出默认上下文
- reasoning 规则与 workflow 规则减少重复注入

保守预估：

- 总 prompt token 降低 35% 到 55%

如果后续再把阶段跳转、去重、校验进一步代码化：

- 总 prompt token 进一步降低到 60% 以上是可预期的

### 9.2 响应时间收益

该方案主要改善：

- 首包前模型阅读成本
- 多轮请求中的重复上下文负担
- 阶段切换时的无效提示冗余

保守预估：

- `time_to_first_token` 改善 15% 到 30%

注意：

- 若瓶颈主要在 `search_category_by_name` 或 `query_brand_by_category`，则该方案无法单独解决全部耗时问题
- 它更偏向优化模型侧延迟和上下文成本

### 9.3 维护性收益

- prompt 拆分后可局部调整，不再牵一发动全身
- reference 文档可单独演进
- 更方便后续过渡到 workflow orchestrator
- 便于做 A/B 测试和阶段级调优

---

## 10. 推荐实施步骤

### 阶段一：静态拆分

目标：先拆文件，不改业务行为。

步骤：

1. 提取常驻核心约束到 `core.py`
2. 将 7 阶段拆成独立 stage prompt 文件
3. 将长示例、数据格式、边界规则迁移到 `references/`
4. 保持当前 Agent 接口不变，仅替换 prompt 来源

产出：

- 新 prompt 目录结构
- 可对比的新旧 prompt 体积统计

### 阶段二：动态装配

目标：不再全量注入 7 阶段内容。

步骤：

1. 新增 `prompt_loader.py`
2. 根据当前阶段装配运行时 prompt
3. 为阶段 2、3、6 加入 reference 选择逻辑
4. 对历史上下文做结构化摘要，减少长文本历史直注

产出：

- 动态 prompt 构建器
- 首包前 token 下降

### 阶段三：代码接管部分规则

目标：让 prompt 继续变薄。

步骤：

1. 将阶段跳转移到代码
2. 将回退次数上限移到代码
3. 将 `build_review_fields` 数据格式校验移到代码
4. 将继续对话识别规则固化成代码策略

产出：

- 更短的阶段 prompt
- 更稳定的行为一致性

### 阶段四：度量与迭代

重点监控：

- 平均 prompt token
- `time_to_first_token`
- 阶段 3 耗时
- 阶段 5 耗时
- 阶段结束到首包
- 推荐结果正确率与回退率

---

## 11. 与当前项目的兼容建议

### 11.1 优先保持 Agent 接口不变

当前建议不要立刻切到多智能体，也不要大改工具层。第一步只重构 prompt 组织方式，保持：

- `Agent`
- `ReasoningTools`
- 现有 toolkits
- 现有事件与日志机制

### 11.2 优先改动位置

第一批建议改动的位置：

- `ecom_reco_agent/prompts/`
- `ecom_reco_agent/agent/agent_os.py`

低风险，因为：

- 不直接修改工具实现
- 不影响 API 协议
- 容易做新旧版本切换

### 11.3 保留兼容开关

建议增加配置项，例如：

- `prompt_mode = "legacy" | "layered"`

以便：

- 快速回滚
- 灰度测试
- 对比日志指标

---

## 12. 风险与注意事项

### 12.1 风险一：拆分后信息丢失

如果阶段 prompt 过短，而代码又没有及时接管关键规则，可能出现行为偏移。

应对：

- 常驻层保留最关键的真实性和禁止编造约束
- 高风险规则放入 reference，并在关键阶段强制注入摘要

### 12.2 风险二：reference 重新膨胀

如果 reference 每次都全文注入，最后会退化成新的大 prompt。

应对：

- reference 默认不常驻
- 只按阶段选择
- 只注入摘要，不直接全量注入正文

### 12.3 风险三：阶段边界不清

如果没有代码层的阶段管理，模型可能仍然跨阶段思考，导致加载收益被削弱。

应对：

- 逐步引入 workflow controller
- 至少先在代码中维护 `current_stage`

### 12.4 风险四：历史上下文仍然过大

即便 prompt 拆得很好，如果历史对话仍然全量注入，收益会被部分抵消。

应对：

- 用结构化摘要替代原始长历史
- 控制 `num_history_runs`
- 避免把历史工具调用详情无差别放入上下文

---

## 13. 最终建议

本方案适合作为当前系统的下一步优化方向，定位如下：

- 不是简单文案压缩
- 不是直接切多智能体
- 也不是仅靠外部 skill 运行时解决问题

它本质上是将 skill 的组织思想内化到你自己的运行时中：

- 用更短的常驻 prompt 保留核心约束
- 用阶段级 prompt 实现最小必要指导
- 用按需 reference 保存复杂知识
- 用代码承担越来越多的流程控制职责

这是当前项目最稳妥、投入产出比最高的一条重构路径。它可以作为“短期精简 prompt”和“中期代码化 workflow”之间的桥梁，同时为后续 orchestrator 化、多智能体化保留演进空间。

---

## 14. 建议后续落地清单

1. 新建 `core.py`、`stages/`、`references/`、`builders/`
2. 把现有 `workflow.py` 拆成常驻层、阶段层、reference 层
3. 保留 legacy 模式，新增 layered 模式
4. 在 `agent_os.py` 中接入动态 prompt 装配
5. 建立 prompt token、TTFT、阶段耗时对比基线
6. 完成一次灰度验证后，再推进代码化阶段控制

