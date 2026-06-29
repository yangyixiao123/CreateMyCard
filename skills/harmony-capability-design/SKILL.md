---
name: harmony-capability-design
description: "辅助鸿蒙 Create My Card / A2UI Form / 小艺卡片项目的端侧能力 input/output schema 设计。用于端侧同事提供底层数据接口、意图框架、UG 接口或本地服务的输入输出示例后，分析哪些参数应隐藏或端侧注入，哪些输入应改造成模型友好 inputSchema，哪些输出应裁剪、格式化、聚合为桌面卡片友好的 outputSchema，并输出函数封装建议和 data capability manifest 示例；当前阶段只设计 inputSchema 和 outputSchema。"
---

# Harmony 端侧能力封装设计

## 目标

把底层数据接口设计成云侧 Agent 可安全填写、端侧可稳定执行、桌面卡片可直接绑定的 `inputSchema` / `outputSchema`。

本 skill 不直接生成卡片 DSL；它服务于能力 schema 设计，产物可交给 `harmony-card-generation` 的 `reference/data-capability/` 使用。当前阶段只考虑输入和输出 schema。

## 输入材料

优先让用户提供以下信息；缺失时基于示例做合理假设并标注不确定点：

- 底层接口名称、用途、调用来源：意图框架、UG、本地数据库、系统服务、应用私有接口等。
- 底层入参 schema 或 1 到 3 个调用示例。
- 底层返回 schema 或 1 到 3 个真实/脱敏返回示例。
- 卡片目标场景：天气、日程、待办、通勤、设备状态、健康、提醒等。
- 端侧约束：隐私字段、端侧注入字段、长度/数量上限、展示格式要求。

不要要求云侧模型看到用户隐私样例原文；如用户提供了真实数据，输出时使用脱敏字段和值。

## 工作流

1. 识别底层接口语义和卡片展示目标。
2. 区分三类字段：模型可填、端侧注入、禁止暴露。
3. 把底层入参改造成模型友好输入。
4. 把底层返回改造成卡片友好输出。
5. 把数量、长度、排序和格式化要求写入 `inputSchema` 描述、`outputSchema` 字段描述或使用规则，不单独输出策略对象。
6. 输出封装建议、`inputSchema` / `outputSchema` 和 manifest 示例。

## 参考路由

处理任何能力 manifest 设计任务时，先读取：

- [`references/capability-manifest.md`](references/capability-manifest.md)

最终自检时读取：

- [`references/review-checklist.md`](references/review-checklist.md)

如果用户要求格式参考现有卡片生成 skill 的能力文档，可同时参考邻近项目中的：

- `../harmony-card-generation/reference/data-capability/calendar.md`
- `../harmony-card-generation/reference/data-capability/weather.md`

## 输出格式

默认使用中文 Markdown 输出，包含以下小节：

1. **底层接口理解**
2. **封装边界建议**
3. **模型可见输入设计**
4. **端侧注入与隐藏字段**
5. **卡片友好输出设计**
6. **数量、长度与格式化约束**
7. **data capability manifest 示例**
8. **端侧实现要点**
9. **待确认问题**

`data capability manifest 示例` 必须包含一个 JSON 代码块，且 manifest 顶层只能包含：

- `id`
- `version`
- `description`
- `inputSchema`
- `outputSchema`

如果该能力要直接进入 `harmony-card-generation`，再给出一个精简版 Markdown 段落，风格接近 `calendar.md`：manifest JSON + 使用规则 + 常用路径 + 初始 DataModel 示例。

## 设计原则

- 面向模型的是语义能力，不是底层 API。
- 输入尽量让模型容易填，输出尽量让 DSL 直接绑定。
- 端侧承担隐私、安全、转换、裁剪、聚合、默认值和本地化格式化。
- 端侧注入字段、隐藏字段、底层接口来源等只在正文分析中说明，不进入 manifest JSON。
- 不把全量原始数据暴露给云侧 Agent。
- 不让云侧模型负责毫秒时间戳、本地时区换算、复杂 code 映射、分页、token 或字符串裁剪。
- 输出 schema 中优先提供已格式化展示字段；数值字段可保留，但不应作为卡片唯一展示依据。
- 数组输出默认有上限；长字符串默认有最大展示长度和端侧裁剪策略。
- 每个 UI 可能绑定的路径都应在 `outputSchema` 或初始 DataModel 中可推导。
- 对点击详情所需的 ID，只输出最小必要字段，并说明是否展示。

## 不要做

- 不要把底层接口 schema 原样包装成 capability manifest。
- 不要暴露密钥、token、账号 ID、设备 ID、底层 debug 字段或内部凭证。
- 不要让模型生成高精度时间戳、复杂经纬度、内部枚举 code 或分页游标，除非用户明确说明模型侧已有可靠解析能力。
- 不要输出无限数组、无长度上限的长文本或不适合桌面卡片展示的大对象。
- 不要编造底层能力不存在的字段、枚举或可调用函数；不确定时放入待确认问题。
