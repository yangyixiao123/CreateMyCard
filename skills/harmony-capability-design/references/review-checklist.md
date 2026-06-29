# 能力封装评审清单

## 安全与隐私

- 没有把 token、secret、cookie、session、账号 ID、设备 ID、内部凭证暴露给模型。
- 内部 ID 只有在点击详情或后续查询必需时才输出，并默认不可展示。
- 输出示例使用脱敏数据，不包含真实用户隐私。

## 模型友好输入

- 模型只需要填写自然语言能稳定推导的参数。
- 日期和时间范围使用 `today`、`tomorrow`、`yyyy-MM-dd`、`next24Hours` 等语义值。
- 枚举值稳定、少量、易理解。
- 有默认值和最大值，尤其是 `maxItems`、`forecastDays` 等数量参数。
- 复杂底层参数由端侧转换或注入。

## 卡片友好输出

- 输出包含可直接绑定的展示字段，如 `summaryText`、`timeText`、`titleText`、`temperatureText`。
- 数组数量默认适合 `2x2` 或 `2x4`。
- 长文本有裁剪策略和展示字段。
- 结果包含 `moreCount`、`hasMore` 或摘要字段，避免卡片误以为只有当前几条。
- 空结果也能用同一个 `outputSchema` 表达，例如空数组、`summaryText` 或 `emptyText`。

## 与 CardSpec / DSL 对齐

- `capabilityId` 稳定且唯一。
- `arguments` 只包含 `inputSchema.properties` 中声明的字段。
- 推荐 `writeResultTo` 位于 `/data` 下。
- UI 常用路径能由 `writeResultTo + outputSchema` 推导。
- 初始 DataModel 可以安全初始化所有 UI 会访问的根结构。

## 端侧实现

- 明确前处理：参数默认值、语义日期转时间戳、枚举映射、端侧注入。
- 明确后处理：字段裁剪、排序、聚合、格式化、本地化。

## 阻塞问题

以下任一项出现时，不应交付 manifest：

- 直接暴露底层敏感参数。
- 输出无限数组或无长度限制的长文本。
- 模型必须生成毫秒时间戳、内部 code、token 或分页游标才能调用。
- `outputSchema` 只有原始值，没有桌面卡片可读展示字段。
- 空结果无法通过正常 `outputSchema` 表达，导致 DSL 需要表达式或特殊逻辑。
- 使用了未确认存在的底层接口或字段，却没有标注待确认。
