---
name: bug-b3-fix
description: Use when a BF is in B3 repair and approved BT tasks must be implemented, documented, and verified.
---

# bug-b3-fix — Bug 修复阶段

> 所属: `docs/.workflow/skills/bugfix/bug-b3-fix`
> 作用: 子 Agent 加载此 Skill 后，按 05-任务拆解 逐项执行 BT 任务，产出代码/规范改动和 06-执行记录

---

## 输入

- **bug_dir**: bug 目录路径（必填）
- **05-任务拆解.md**: B2 阶段产出（必读）
- **事实锚点.json**: B2 阶段已更新的锚点（必读）
- **04-解决方案.md**: B2 产出（参考）

收到输入后先读 `05-任务拆解.md` 获取任务清单和执行顺序，再读 `事实锚点.json` 确认 `task_mappings` 待执行。

---

## 输出

| 输出 | 说明 |
|------|------|
| 代码/规范改动 | 按 BT 任务具体执行 |
| `06-执行记录.md` | 每个 BT 的执行细节 |
| `事实锚点.json` | 更新 `task_mappings[].status` 为 `covered` |

---

## 执行前准备

B3 开始前必须生成上下文包：

```bash
python3 docs/.workflow/scripts/context_packets.py build {bug_id} B3
```

---

## 执行门禁

每批 BT 任务：

```bash
python3 docs/.workflow/scripts/stage_gates.py step-start {bug_id} "06-执行记录" \
  '{"goal":"按05-任务拆解顺序执行BTxx","expected_outputs":["06-执行记录.md"],"done_definition":[...],"next_step":"07-测试验证"}'

# 每完成一个 BT 批次:
python3 docs/.workflow/scripts/stage_gates.py progress {bug_id} \
  '{"completed_action":"BTxx完成: ...","key_conclusions":[...],"outputs":[...],"verification":[...],"next_step":"BTxx+1"}'

# 全部 BT 完成后关闭 06-执行记录
python3 docs/.workflow/scripts/stage_gates.py step-done {bug_id} "06-执行记录" \
  '{"outputs":["06-执行记录.md","事实锚点.json"],"key_conclusions":["bug 结论: BT任务已按方案完成并记录验证证据","规范检查结论: [6/6 项通过]"],"next_step":"bug-execution-done"}'
```

---

## 06-执行记录模板

```markdown
# 06-执行记录

## BT01 - {任务名}
- 执行时间:
- 文件:
- 实际改动:
- 执行结果: ✓ 成功 / ✗ 失败
- 验证:

## BT02 - {任务名}
...

## 异常记录
| 时间 | 异常 | 处理方式 |
|------|------|----------|
```

---

## worktree 边界规则

- **worktree 只放实现代码、测试代码、必要脚本和生成产物。**
- `docs/02-bug-fix/**`、`docs/.workflow/**`、`docs/03-knowledge/**` 全部留在当前分支工作区编辑。
- bug 目录文档、`11-排查附件/`、`state.json`、`事实锚点.json`、`恢复包.md` 不能在 worktree 中新建或修改。
- 如果一个任务同时涉及代码与文档，必须先在当前分支完成文档，再进 worktree 做代码；代码结束后如需补文档，回当前分支写入。
- 不允许通过复制、软链、临时目录挂载把文档带进 worktree。

---

## 规范检查（step-done 时）

| 检查项 | 证据来源 |
|--------|----------|
| 输出文件全部写入且读回验证非空 | `outputs` + 读回日志 |
| 操作在 `state.json.allowed_next_actions` 范围内 | `state.json` |
| `state.json.checklist` 对应条目已同步置位 | `state.json.checklist` |
| 排查附件已归档 | `11-排查附件/00-附件索引.md` |
| 不存在未写入的临时结论 | Agent 自检 |

每步 step-done 同步更新 `10-AI协作记录.md` 的 AI 参与范围表。

---

## 子 Agent 派遣

B3 阶段可派遣以下子 Agent：

| 子Agent | 依赖前置文档 |
|---------|-------------|
| Bug修复实现 | `03-根因分析.md`、`04-解决方案.md`、`05-任务拆解.md`、`事实锚点.json` |
| Bug独立复核 | 复核对象阶段的全部文档 |

派遣时必须：

```bash
python3 docs/.workflow/scripts/stage_gates.py subagent-start {bug_id} "Bug修复实现" \
  '{"context_packet":"06-上下文包/上下文包-B3-修复.md","input_paths":["05-任务拆解.md"],"output_paths":["06-执行记录.md"],"instruction":"实现 BT01"}'
```

返回时携带 `dispatch_id`。

---

## 异常处理

如无法实际派遣子 Agent（fallback 到主线），必须在执行记录中追加 `self-review-bias` 声明：

```markdown
## self-review-bias（主线 fallback 补偿）
- **认知盲区 1**: [可能因已有结论产生的确认偏误]
- **自检方式 1**: [独立证据排除]
- **认知盲区 2**: [另一盲区]
- **自检方式 2**: [自检方式]
```

---

## 关闭条件

所有 BT 任务完成后，触发阶段转移：

```bash
python3 docs/.workflow/scripts/stage_gates.py auto {bug_id} bug-execution-done
```

此时 bug 进入 **验证** 阶段。
