# {{title}}

template: bug-context-packet

> **生成时间**: {{generated_at}}
> **阶段**: {{stage_key}} / {{stage_name}}
> **规则**: 本文件是 bug 子Agent 和主Agent 的最小入口。先读本包，再按“必须读取清单”读取精确路径；禁止一次性加载无关全文。

---

#context-packet
#bugfix/{{workflow_id}}
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

## 6. 最近产物索引

```json
{{indexes}}
```

## 7. 禁止事项

- 不要把本包当成完整事实来源；事实以列出的根因、方案、任务和执行记录为准。
- 不要跳过 `state.json` 的 allowed_next_actions。
- 不要把推测写入测试记录或验收发布；必须写可验证证据。
