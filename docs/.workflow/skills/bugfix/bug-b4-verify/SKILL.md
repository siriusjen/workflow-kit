---
name: bug-b4-verify
description: Use when a BF is in B4 verification, release validation, bug_chain closure, or standard/lightweight closeout.
---

# bug-b4-verify — Bug 验证与发布阶段

> 所属: `docs/.workflow/skills/bugfix/bug-b4-verify`
> 作用: 子 Agent 加载此 Skill 后，执行验证矩阵和 bug_chain 关门校验，产出 07/08

---

## 输入

- **bug_dir**: bug 目录路径（必填）
- **05-任务拆解.md**: 任务清单（必读）
- **06-执行记录.md**: B3 产出（必读）

---

## 输出

| 文件 | 说明 |
|------|------|
| `07-测试验证.md` | 验证矩阵和测试结论 |
| `08-验收发布.md` | 发布检查清单和关闭确认 |

---

## 执行前准备

B4 开始前必须生成上下文包：

```bash
python3 docs/.workflow/scripts/context_packets.py build {bug_id} B4
```

---

## 执行门禁

```bash
python3 docs/.workflow/scripts/stage_gates.py step-start {bug_id} "07-测试验证" \
  '{"goal":"验证全部修复有效，确保无回归","expected_outputs":["07-测试验证.md"],"done_definition":["核心修复全部通过","回归无新增问题","bug_chain通过"],"next_step":"08-验收发布"}'

python3 docs/.workflow/scripts/stage_gates.py step-done {bug_id} "07-测试验证" \
  '{"outputs":["07-测试验证.md"],"key_conclusions":["bug 结论: 修复有效且相关回归通过","规范检查结论: [6/6 项通过]"],"next_step":"08-验收发布"}'
```

---

## 07-测试验证模板

```markdown
# 07-测试验证

## 核心修复验证

| 编号 | 测试场景 | 输入 | 预期结果 | 实际结果 | 通过 |
|------|----------|------|----------|----------|------|
| V01 | | | | | |

## 回归验证

| 编号 | 测试场景 | 验证目的 | 通过 |
|------|----------|----------|------|
| R01 | | | |

## 测试结论
- [ ] 核心修复验证: N/N 通过
- [ ] 回归验证: N/N 通过
- [ ] **整体结论: 可以发布 / 不可发布**
```

**验证规则**:
- 核心修复覆盖所有 BT 任务
- 回归至少验证相关主流程
- 测试结论不能模棱两可

---

## bug_chain 关门校验

测试验证通过后，必须运行：

```bash
python3 docs/.workflow/scripts/validators.py bug_chain {bug_id}
```

未通过时不得进入 08-验收发布。

通过后更新 `事实锚点.json` 的最终状态。

---

## 08-验收发布模板

```markdown
# 08-验收发布

## 发布前检查清单
### 代码检查
- [ ] BT 任务代码已全部完成
- [ ] 07-测试验证全部通过

### 规范检查
- [ ] 规范改动已落盘（如有）

### 数据检查
- [ ] 数据修复已完成（如有）
- [ ] 备份已留存（如有）

### 回滚准备
- [ ] 回滚方案已确认

## 关闭条件
- [ ] bug_chain 通过
- [ ] 07-测试验证全部通过
- [ ] 无新增错误

## 发布记录
- 完成时间:
- 改动范围:
- 验证结果:
```

---

## 关闭流程

```bash
# 1. 先确认 bug_chain 通过
python3 docs/.workflow/scripts/validators.py bug_chain {bug_id}

# 2. 触发阶段转移
python3 docs/.workflow/scripts/stage_gates.py auto {bug_id} bug-test-done
python3 docs/.workflow/scripts/stage_gates.py auto {bug_id} bug-release-done

# 3. 人工锚点关闭
python3 docs/.workflow/scripts/stage_gates.py approve {bug_id} approve-release
```

---

## 子 Agent 派遣

B4 可派遣：

| 子Agent | 依赖前置文档 |
|---------|-------------|
| Bug回归验证 | `05-任务拆解.md`、`06-执行记录.md` |
| Bug独立复核 | 复核对象阶段的全部文档 |

---

## 09/10 关门规则

- `standard` 模式下，`09-复盘与沉淀.md` 和 `10-AI协作记录.md` 是 `approve-release` 前置项，必须在关闭前完成并通过 step-done 双结论。
- `lightweight` 模式下可以不展开 09/10，但必须在 `08-验收发布.md` 说明原因、残余风险和后续补充条件。
- 不允许 standard 模式关闭后再补写 09/10。
