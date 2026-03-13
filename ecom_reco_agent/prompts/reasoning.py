"""
ReasoningTools 使用说明。
"""

REASONING_INSTRUCTIONS = """\
你可以使用 reasoning_tools 提供的 think 和 analyze 工具。

规则：
- 每次接收用户输入后，先使用 think 做内部判断与规划。
- think 仅用于内部推理，不向用户暴露思考过程。
- analyze 仅用于阶段 6 和阶段 7 的推荐摘要生成。
- 除阶段 6、阶段 7 外，不要额外输出面向用户的总结性文案。

analyze 输出要求：
- 使用中文。
- 使用简洁 Markdown。
- 可使用表格概括节日、场景和推荐方向。
- 语气友好，但不要输出具体推理过程。
"""

