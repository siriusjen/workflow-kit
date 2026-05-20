# bug-b2-plan — Bug 方案阶段

> 所属: `docs/.workflow/skills/bugfix/bug-b2-plan`
> 作用: 子 Agent 加载此 Skill 后，根据 B1 产出的根因分析，产出 04/05 两份文档

---

## 输入

- **bug_dir**: bug 目录路径（必填）
- **03-根因分析.md**: B1 阶段产出（必读）
- **事实锚点.json**: B1 阶段产出（必读）

收到输入后，先读 `03-根因分析.md` 提取根因列表，再读 `事实锚点.json` 确认 `solution_mappings` 待填充。

---

## 输出

| 文件 | 说明 |
|------|------|
| `04-解决方案.md` | 方案对比、选型理由、完整措施 |
| `事实锚点.json` | 更新 `solution_mappings`（每个根因需有方案覆盖） |

---

## 执行门禁

```bash
python3 docs/.workflow/scripts/stage_gates.py step-start {bug_id} "04-解决方案" \
  '{"goal":"...","expected_outputs":["04-解决方案.md"],"done_definition":[...],"next_step":"05-任务拆解"}'

python3 docs/.workflow/scripts/stage_gates.py progress {bug_id} \
  '{"completed_action":"...","key_conclusions":[...],"outputs":["04-解决方案.md"],"verification":[...],"next_step":"05-任务拆解"}'

python3 docs/.workflow/scripts/stage_gates.py step-done {bug_id} "04-解决方案" \
  '{"outputs":["04-解决方案.md"],"key_conclusions":[...],"next_step":"05-任务拆解"}'
```

---

## 04-解决方案模板

```markdown
# 04-解决方案

## 方案对比
| 方案 | 描述 | 优点 | 缺点 | 推荐 |
|------|------|------|------|------|

## 选择方案 {X}，理由

## 完整解决措施
### 紧急措施（立即，治标）
### 根本修复（治本）
### 数据修复（如有）
### 预防措施

## 方案影响
- 是否需要数据库迁移:
- 是否需要停机:
- 预计修复时长:
- 回滚方案:
```

**验证规则**:
- 每个根因至少有 1 个方案覆盖
- 方案对比有选型理由
- 区分紧急措施和根本修复
- 回滚方案明确

---

## 05-任务拆解模板

```markdown
# 05-任务拆解

## 任务清单
| 编号 | 任务 | 文件/范围 | 验收标准 | 预计时长 |
|------|------|-----------|----------|----------|

## 执行顺序

## 注意事项
```

**验证规则**:
- 每个方案有对应任务覆盖
- 任务编号 BT 连续不跳号
- 执行顺序无循环依赖
- 每个任务有明确的文件范围和验收标准

---

## 事实锚点更新

04-解决方案 完成后更新 `事实锚点.json` 的 `solution_mappings`，每个根因至少一条映射且 `status` 为 `covered`。

05-任务拆解 完成后更新 `task_mappings`，每个方案至少一条映射且 `status` 为 `covered`。

---

B2 全部完成后，由主 Agent 触发人工锚点：
```bash
python3 docs/.workflow/scripts/stage_gates.py approve {bug_id} approve-fix-plan
```
