# bug-b1-diagnose — Bug 诊断阶段

> 所属: `docs/.workflow/skills/bugfix/bug-b1-diagnose`
> 作用: 子 Agent 加载此 Skill 后，根据输入的问题描述，产出 01/02/03 三份文档和事实锚点

---

## 输入

- **problem_description**: 用户提供的 bug 描述文本（必填）
- **bug_dir**: bug 目录路径，如 `docs/02-bug-fix/2026-05-20/BF03-xxx/`（必填）
- 可选: 截图路径、日志片段路径

收到输入后，先读 `bug_dir/state.json` 确认当前状态，再读 `bug_dir/恢复包.md`。

---

## 输出

所有输出写入 `bug_dir/`：

| 文件 | 说明 |
|------|------|
| `01-问题描述.md` | 结构化问题描述 |
| `02-环境与影响范围.md` | 影响范围评估与定级 |
| `03-根因分析.md` | 5-Why 追溯与代码定位 |
| `事实锚点.json` | 根因→方案→任务闭环锚点 |

---

## 执行顺序与门禁

每步必须执行 `stage_gates.py`：

```bash
# 第一步开始
python3 docs/.workflow/scripts/stage_gates.py step-start {bug_id} "01-问题描述" \
  '{"goal":"...","expected_outputs":["01-问题描述.md"],"done_definition":[...],"next_step":"02-环境与影响范围"}'

# 填写完成后记录进展
python3 docs/.workflow/scripts/stage_gates.py progress {bug_id} \
  '{"completed_action":"...","key_conclusions":[...],"outputs":["01-问题描述.md"],"verification":[...],"next_step":"02-环境与影响范围"}'

# 验证写入后关闭步骤
python3 docs/.workflow/scripts/stage_gates.py step-done {bug_id} "01-问题描述" \
  '{"outputs":["01-问题描述.md"],"key_conclusions":[...],"next_step":"02-环境与影响范围"}'
```

02、03 同理。**必须 step-done 后才进入下一步。**

---

## 01-问题描述模板

```markdown
# 01-问题描述

## 现象
- （描述用户/监控看到的现象，不描述原因）

## 复现步骤
1.
2.
3.

## 必现条件
- 环境:
- 特殊输入:
- 操作路径:

## 截图 / 日志
```

## 发现渠道
- [ ] 用户反馈  [ ] 监控告警  [ ] 测试发现  [ ] 代码审查

## 关联信息
- 环境:
- 版本:
- 关联需求:
```

**验证规则**: 现象不描述原因，复现步骤可独立执行，关键日志已粘贴。

---

## 02-环境与影响范围模板

```markdown
# 02-环境与影响范围

## 受影响环境
- [ ] 生产环境  [ ] 预发布环境  [ ] 测试环境

## 功能影响
| 功能 | 是否受影响 | 影响描述 |
|------|-----------|----------|

## 文件影响
| 文件 | 受影响原因 | 影响类型 |
|------|-----------|----------|

## 用户影响
- 受影响范围:
- 影响时段:

## 数据影响
- [ ] 有数据损坏  [ ] 有数据错误  [ ] 无数据影响

## 严重程度定级
- **P?-** （原因: ）

## 临时规避方案
```

**严重程度**: P0 线上阻塞/1h, P1 核心受损/4h, P2 功能异常/1工作日, P3 体验问题/下迭代

---

## 03-根因分析模板

```markdown
# 03-根因分析

## 5-Why 根因追溯
| Why | 问题 | 答案 |
|-----|------|------|
| Why 1 | | |

## 根因定位
- **直接原因**:
- **深层原因**:

## 相关代码定位
- 文件:
- 行号:

## 是否存在类似问题
- [ ] 已排查  [ ] 待排查

## 影响评估
- 代码层面:
- 数据层面:
```

**验证规则**: 5-Why 至少 3 层，代码定位到行号，区分直接/深层原因。

---

## 事实锚点.json schema

```json
{
  "_comment": "Bug 根因→方案→任务事实链锚点；validators.py bug_chain 读取",
  "bug_id": "BFxx",
  "last_updated": "ISO时间戳",
  "rootcause_anchors": [
    {"id": "RC01", "summary": "...", "source": "03-根因分析.md#锚点"}
  ],
  "solution_mappings": [
    {"rootcause_id": "RC01", "solution_ref": "04-解决方案.md#方案", "status": "covered"}
  ],
  "task_mappings": [
    {"solution_ref": "04-解决方案.md#方案", "task_id": "BT01", "task_ref": "05-任务拆解.md#任务清单", "status": "covered"}
  ]
}
```

**硬规则**: 三个数组元素必须是 JSON 对象，不允许用字符串。`id` 格式 RC+数字唯一。`status` 只接受 `covered`/`partial`/`uncovered`。

---

B1 全部完成后触发: `python3 docs/.workflow/scripts/stage_gates.py auto {bug_id} bug-rootcause-done`
