# {{title}}

template: feature-context-packet

> **生成时间**: {{generated_at}}
> **阶段**: {{stage_key}} / {{stage_name}}
> **任务**: {{task_label}}
> **规则**: 本文件是子Agent默认入口。先读本包，再按“必须读取清单”读取精确路径；禁止一次性加载无关全文。

---

#context-packet
#feature/{{workflow_id}}
#stage/{{stage_name}}

## 1. 加载策略

1. 先读本上下文包。
2. 只读取“必须读取清单”中的路径。
3. 需要额外文件时，先用 `rg` 定位，再读取最小片段，并在返回摘要中说明原因。
4. 禁止加载完整代码库、完整历史会话、完整测试日志。
5. 子Agent 返回主Agent 时只返回结构化摘要、输出路径、关键结论和阻塞项。

## 2. 状态摘要

```json
{{state_summary}}
```

## 3. 必须读取清单（精确路径）

{{must_read}}

## 待生成/待定位清单

{{pending_must_read}}

## 4. 按需加载清单

{{on_demand}}

## 5. 预期输出

{{outputs}}

## 6. 当前任务片段

{{task_section}}

## 7. RDTV相关片段

```json
{{rdtv_rows}}
```

## 8. 最近产物索引

```json
{{indexes}}
```

## 9. 禁止事项

- 不要把本包当成完整事实来源；事实以列出的基线文档和代码文件为准。
- 不要读取未列入清单的整目录；确需读取时必须先说明原因。
- 不要把推测写入实现记录或测试记录；必须写可验证证据。
