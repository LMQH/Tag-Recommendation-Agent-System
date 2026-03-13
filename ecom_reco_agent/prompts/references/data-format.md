# 数据格式 reference

- `build_review_fields` 的 `recommendations` 必须是按节日分组的字典。
- `festival_scenes` 中每项必须包含 `id`、`festival_name`、`scene_type`。
- 节日内品牌按 `brandCode` 去重，品类按 `categoryCode` 去重。
- `brandCode`、`categoryCode` 必须来自真实工具返回值，禁止根据名称自造。
- 禁止把平铺列表直接传给 `build_review_fields`。
