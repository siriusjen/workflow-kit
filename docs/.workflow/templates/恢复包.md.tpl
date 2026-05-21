# {{feature_id}}-{{feature_name}} 恢复包

> 会话中断后，主Agent 启动的第一步读这个文件

---

## 当前恢复确认卡

```
[恢复确认] {{feature_id}} · init · step 0/1
当前状态: awaiting-req-input-discussion
工作流模式: {{workflow_mode}}（流程深度）
执行模式: {{execution_mode}}（执行方式）
输入模式: {{input_mode}}
基线: requirement=未设置 | tech_spec=未设置 | task_split=未设置
当前上下文包: 未生成
已完成步骤: 骨架初始化 ✓
当前进行中步骤: 无
待办步骤: req-input-discussion
关键结论: 无（尚未开始讨论）
当前小步下一步: 与人工讨论需求输入
当前合法下一动作:
  → 与人工讨论需求输入
  → approve-req-input
恢复检查: 无
明确不能做: 写代码 / 拆任务 / 创建技术方案 / 派遣子Agent
风险项: 无
上下文用量: 0%
---
确认恢复完成，等待指令。
```

---

## 执行日志

| 时间 | 阶段 | 步骤 | 结果 | 关键结论 |
| ---- | ---- | ---- | ---- | -------- |

---

## 失败现场记录

*（本节由工作流自动追加，初始为空）*

---

## 失败现场格式（发生中断时填写）

```markdown
## 失败现场 YYYY-MM-DD HH:mm
- 失败阶段:
- 当前正在做:
- 已完成到:
- 哪一步失败:
- 失败原因:
- 受影响范围:
- 建议恢复起点:
```

---

## 会话恢复协议（主Agent 必读）

1. 读 `state.json` 确认 current_stage / current_step_log
2. 读 state.baseline 中的基线文档
3. 对照规范检查当前阶段是否完成且正确
4. 输出恢复确认卡
5. 等待指令，不允许提前行动
