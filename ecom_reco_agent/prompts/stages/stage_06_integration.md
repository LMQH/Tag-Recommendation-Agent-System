## 阶段 6：结果整合与输出

目标：
- 将查询结果按节日分组传入 `build_review_fields`。
- 如有历史结果，执行安全整合策略。

允许工具：
- `think`
- `build_review_fields`
- `analyze`

本阶段要求：
- 仅在本阶段生成面向用户的推荐摘要。
- `build_review_fields` 的输入必须按节日分组。
- 不输出伪造品牌、品类或节日数据。
