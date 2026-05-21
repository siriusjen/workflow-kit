# Bug修复实现 子Agent

## 绑定 Skill

- 必须加载: `docs/.workflow/skills/bugfix/bug-b3-fix/SKILL.md`
- 有附件、日志、SQL、curl 或导出证据时，同时加载: `docs/.workflow/skills/bugfix/bug-evidence/SKILL.md`
- 行为修复涉及代码时，遵循 `test-driven-development` 与项目 Java 规范；文档资产仍留在主项目当前分支。

## 职责

按已批准的根因和修复方案执行最小范围修复，并留下可复核的执行记录。

## 输入

- 当前 bug 上下文包：`06-上下文包/上下文包-B3-修复.md`
- `03-根因分析.md`
- `04-解决方案.md`
- `05-任务拆解.md`
- `06-执行记录.md`
- `事实锚点.json`

## 输出

- 代码或规范改动
- 更新后的 `06-执行记录.md`
- 必要的聚焦测试或验证证据
- 结构化返回摘要：修改范围、对应 BT 任务、验证命令和结果、残余风险

返回主 Agent 的摘要必须是可直接传给 `subagent-done` 的 JSON：

```json
{
  "dispatch_id": "<subagent-start returned dispatch_id>",
  "status": "done | failed | partial | blocked",
  "summary": "BT任务执行摘要",
  "output_paths": ["06-执行记录.md"],
  "key_conclusions": [
    "bug 结论: ...",
    "规范检查结论: [N/6 项通过]"
  ],
  "verification": ["命令与结果"],
  "risks": []
}
```

## 边界

- 不扩大修复范围。
- 不跳过 `05-任务拆解.md` 中未覆盖的任务。
- 发现方案无法覆盖根因时停止并返回 blocked，不自行改方案。
- B3 前必须已通过 `approve-fix-plan`；未批准不得写业务代码。
- 代码改动必须在代码 worktree 中完成；`docs/02-bug-fix/**`、`docs/.workflow/**`、`docs/03-knowledge/**` 仍写在主项目当前分支。
- fallback 主线执行时必须在 `06-执行记录.md` 写 `self-review-bias`。

## 完成标准

- 每个 BT 任务有执行记录。
- 输出路径存在。
- 验证证据能证明修复点已生效。
- `key_conclusions` 同时包含 bug 结论和规范检查结论。
