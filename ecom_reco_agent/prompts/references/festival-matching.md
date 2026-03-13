# 节日匹配 reference

- 只保留与用户意图匹配的节日记录。
- 用户明确指定节日但库中无匹配时，必须调用 `save_matched_festivals([])`。
- `festival_scenes` 只能来自 `get_all_festivals()` 的真实结果。
- 不要根据时间、季节或语义擅自替换用户指定节日。
