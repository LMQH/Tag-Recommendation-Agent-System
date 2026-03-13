## 阶段 2：节日匹配

目标：
- 获取当前日期信息和节日全集。
- 只提取与用户意图匹配的 `festival_scenes`。

允许工具：
- `get_festival_date_info`
- `get_all_festivals`
- `save_matched_festivals`

本阶段要求：
- 有匹配时仅保存真实节日记录。
- 无匹配时必须调用 `save_matched_festivals([])`。
- 禁止把用户指定节日替换成其他节日。
