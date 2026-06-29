# 端侧能力封装与 Schema 设计指南

本文档用于指导端侧同事把底层数据能力（意图框架、UG 接口、系统服务或应用私有接口）封装成云侧 Agent 可使用的 `data-capability` manifest。

核心原则：不要把底层接口原样暴露给模型。端侧能力应是面向卡片生成场景的受控数据契约，负责隐藏敏感参数、转换模型不友好的入参、裁剪返回字段，并输出适合桌面卡片绑定的展示型 ViewModel。

## 1. 分层职责

```text
底层接口
  -> 端侧封装能力
      -> 云侧 Agent 可见 inputSchema / outputSchema
          -> CardSpec.dataBindings
              -> DSL 绑定 /data/... 路径
```

- 底层接口：可以复杂、私有、带鉴权、带内部 ID。
- 端侧封装能力：做默认值、时间转换、字段裁剪、排序、数量限制、格式化和失败态归一。
- 云侧可见 schema：只描述模型能安全填写的参数，以及卡片能稳定展示的字段。

## 2. inputSchema 设计原则

### 2.1 只暴露模型需要填写的参数

不要暴露这些字段：

- 用户 ID、账号 ID、设备 ID、session、token、密钥。
- 底层分页游标、内部索引字段、traceId。
- 可由端侧上下文确定的语言、地区、时区、当前位置状态。
- 底层接口需要但模型无法可靠生成的复杂结构。

推荐做法：

```json
{
  "inputSchema": {
    "type": "object",
    "properties": {
      "date": {
        "type": "string",
        "description": "查询日期，支持 today、tomorrow 或 yyyy-MM-dd。"
      },
      "maxItems": {
        "type": "integer",
        "description": "最多返回条数。默认 3，最大 5。"
      }
    }
  }
}
```

端侧内部再补齐：

```json
{
  "runtimeInjected": ["accountId", "timezone", "locale"]
}
```

### 2.2 输入要模型友好

模型更适合生成语义参数，不适合生成底层技术参数。端侧应提供转换层。

| 底层需要 | 不建议暴露 | 建议暴露 |
| --- | --- | --- |
| 毫秒时间戳区间 | `timeInterval: [1782518400000, 1782604799999]` | `date: "today"`、`timeRange: "allDay"` |
| 经纬度 | `latitude`、`longitude` | `destinationName: "公司"`，由端侧或意图能力解析 |
| 枚举 code | `sceneType: 17` | `scene: "commute"` |
| 内部过滤对象 | `filter: {...}` | `keyword`、`date`、`category` |

示例：日历查询可以让模型填写自然参数：

```json
{
  "id": "calendar.events.compact",
  "description": "查询适合桌面卡片展示的日程摘要。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "date": {
        "type": "string",
        "description": "today、tomorrow 或 yyyy-MM-dd。"
      },
      "timeRange": {
        "type": "string",
        "enum": ["allDay", "morning", "afternoon", "evening", "next24Hours"]
      },
      "maxItems": {
        "type": "integer",
        "description": "最多返回条数，默认 3，最大 5。"
      }
    },
    "required": ["date"]
  }
}
```

端侧负责把 `date + timeRange` 转换成本地时区时间戳。

## 3. outputSchema 设计原则

### 3.1 输出展示型 ViewModel

`outputSchema` 不应复刻底层返回，而应输出 DSL 可直接绑定的字段。优先提供带单位、已格式化、适合阅读的字符串。

不推荐：

```json
{
  "temperature": 28,
  "weatherCode": 101,
  "updateTime": 1782556200000
}
```

推荐：

```json
{
  "current": {
    "temperatureText": "28°C",
    "conditionText": "多云",
    "updatedAtText": "06-27 18:30"
  }
}
```

这样 DSL 可以直接绑定：

```json
{"content": {"path": "/data/weather/current/temperatureText"}}
```

### 3.2 隐藏不适合模型或 UI 的字段

不要输出这些字段：

- 底层 `code`、`message`、`status`、trace 信息。
- token、隐私标识、内部调试字段。
- 大段原始 JSON、原始 HTML、原始协议结构。
- 卡片不需要展示的低层字段。

必要的失败状态应归一为可展示字段：

```json
{
  "state": {
    "empty": false,
    "errorText": ""
  }
}
```

### 3.3 控制数量、长度和排序

桌面卡片无法承载无限列表。端侧能力必须限制返回规模。

当前阶段先不单独设计策略字段，建议直接在 `inputSchema` 和 `outputSchema` 中表达约束：

- `inputSchema` 暴露 `maxItems`，并在 `description` 中写清默认值和最大值。
- `outputSchema` 输出已裁剪的展示字段，例如 `titleText`、`locationText`。
- `outputSchema` 输出 `summaryText` 和 `moreCount`，表达还有多少条未展示。
- 排序规则写在能力 `description` 或数组字段 `description` 中，例如“按开始时间升序排列”。

输出示例：

```json
{
  "summaryText": "今日 4 个日程",
  "moreCount": 1,
  "items": [
    {
      "titleText": "产品方案评审",
      "timeText": "09:30-10:00",
      "locationText": "A座 12F",
      "entityId": "calendar-001"
    }
  ]
}
```

规则：

- 默认返回 2 到 3 条，除非卡片场景确实需要更多。
- `titleText`、`locationText` 等展示字段由端侧截断或归一，避免 DSL 布局失控。
- 保留跳转所需的稳定 ID，例如 `entityId`，但只在确实用于点击事件时输出。
- 提供 `summaryText`、`moreCount`，让卡片表达“还有更多”而不是展示全部。

## 4. 推荐 Manifest 结构

```json
{
  "id": "calendar.events.compact",
  "version": "1.0",
  "description": "查询适合桌面卡片展示的日程摘要。",
  "inputSchema": {},
  "outputSchema": {}
}
```

必需字段：

- `id`：稳定能力 ID，CardSpec 的 `capabilityId` 使用它。
- `description`：让模型判断何时选择该能力。
- `inputSchema`：模型可填写参数。
- `outputSchema`：端侧写入 `writeResultTo` 后，DSL 可绑定的字段。

## 5. 完整示例：今日紧凑日程

```json
{
  "id": "calendar.events.compact",
  "version": "1.0",
  "description": "查询用户日历，并返回适合桌面卡片展示的紧凑日程摘要。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "date": {
        "type": "string",
        "description": "查询日期，支持 today、tomorrow 或 yyyy-MM-dd。"
      },
      "timeRange": {
        "type": "string",
        "enum": ["allDay", "morning", "afternoon", "evening", "next24Hours"]
      },
      "maxItems": {
        "type": "integer",
        "description": "最多返回条数，默认 3，最大 5。"
      }
    },
    "required": ["date"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "summaryText": {
        "type": "string",
        "description": "日程概览，例如“今日 4 个日程”。"
      },
      "moreCount": {
        "type": "integer",
        "description": "未展示的剩余日程数量。"
      },
      "items": {
        "type": "array",
        "description": "按开始时间升序排列的紧凑日程。",
        "items": {
          "type": "object",
          "properties": {
            "titleText": {
              "type": "string",
              "description": "适合卡片展示的标题，建议不超过 18 个中文字符。"
            },
            "timeText": {
              "type": "string",
              "description": "适合展示的时间段，例如“09:30-10:00”。"
            },
            "locationText": {
              "type": "string",
              "description": "适合展示的地点，过长时端侧裁剪。"
            },
            "entityId": {
              "type": "string",
              "description": "用于点击查看日程详情的稳定 ID。"
            }
          },
          "required": ["titleText", "timeText", "entityId"]
        }
      },
      "state": {
        "type": "object",
        "properties": {
          "empty": {"type": "boolean"},
          "errorText": {"type": "string"}
        }
      }
    }
  }
}
```

对应 CardSpec 使用方式：

```json
{
  "suggestSize": "2x4",
  "dataBindings": [
    {
      "capabilityId": "calendar.events.compact",
      "arguments": {
        "date": "today",
        "timeRange": "allDay",
        "maxItems": 3
      },
      "writeResultTo": "/data/calendar"
    }
  ]
}
```

DSL 绑定路径应从 `writeResultTo + outputSchema` 推导：

- `/data/calendar/summaryText`
- `/data/calendar/items`
- 模板项内：`titleText`、`timeText`、`locationText`、`entityId`
- `/data/calendar/state/empty`
- `/data/calendar/state/errorText`

## 6. 设计检查清单

提交一个新能力 manifest 前，检查：

- [ ] `inputSchema` 只包含模型能安全、稳定填写的字段。
- [ ] 敏感参数、账号参数、敏感 token 和内部 ID 没有暴露给模型。
- [ ] 时间、地点、枚举等参数对模型友好，复杂转换由端侧完成。
- [ ] `outputSchema` 是卡片 ViewModel，而不是底层接口原始返回。
- [ ] 输出字段包含展示友好的文本，例如 `temperatureText`、`timeText`、`summaryText`。
- [ ] 列表能力定义了默认数量、最大数量、排序和超出数量字段。
- [ ] 长字符串有端侧裁剪或摘要策略。
- [ ] 无数据和接口失败时有稳定 fallback 字段。
- [ ] `id` 稳定，且能直接作为 CardSpec `capabilityId`。
- [ ] DSL 所需字段都能从 `writeResultTo + outputSchema` 推导。
