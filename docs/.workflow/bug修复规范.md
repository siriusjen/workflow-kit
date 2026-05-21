# 02-Bug 修复规范

> **版本**: v1.3 · 2026-05-19
> **适用范围**: `docs/02-bug-fix/` 目录下所有 Bug 处理流程
> **使用方式**: 告诉大模型"请按 `docs/.workflow/bug修复规范.md` 来处理我的bug，bug描述如下：..."

---

## 速查卡（Bug 会话默认先读，15行以内）

```text
1. 先做只读预检/分流：查已有 BF 索引、日志、必要代码和复现线索，判断是否需要正式创建 BF。
2. 收到新 Bug 描述时必须先询问用户是否启动自动排查流程 BFxx；用户明确确认后，才运行 `init_bugfix.py` 建骨架，必须生成 `state.json` 和 `恢复包.md`。
3. 正式流程第一动作必须是先建本次 bug 的目录和总览，不允许在 BF 流程内先读代码。
4. 先查清问题：01 问题描述 → 02 影响范围 → 03 根因分析。
5. 先定方案再动手：04 解决方案 → 05 任务拆解。
6. P0/P1 默认标准模式；P2/P3 可选轻量模式，09/10 可按需保留或延后。
7. 排查期间的脚本、SQL、curl、导出数据、截图、日志摘录都要放进 `11-排查附件/`。
8. 每一步开始前先对照规范，确认当前允许动作。
9. 每一步结束时同时输出 bug 结论和规范检查结论。
10. 发现规范缺口时，先写进当前 bug 的执行记录或复盘/例外日志，再立即修订流程文档；修订后继续后续排查，并用新规范继续验证。
11. 文档写入后必须立即读回验证；补丁失败或读回仍为空时，禁止进入代码排查/测试。
12. 修复前先生成 bug 上下文包：`context_packets.py build BFxx B3`。
13. 每个小步必须 `stage_gates.py step-start` → `progress` → `step-done`，未关闭不得进入下一步。
14. 派 bug 子Agent前必须 `subagent-start`，返回必须 `subagent-done` 并携带 `dispatch_id`。
15. 关闭前必须过 `validators.py bug_chain BFxx`、`approve-release`。
16. `state.json` 是唯一机器状态；写 `state.json` 的命令禁止并行执行。
```

## 最小加载地图（默认按需，不整篇读）

| 当前任务 | 默认先读 | 只有需要时再读 |
|----------|----------|----------------|
| 新建 Bug | 速查卡 + `1. 目录结构规范` + `4.1 启动 Bug 处理` | `5. init_bugfix.py 脚本规范` |
| 恢复处理中断 | `恢复包.md` + `state.json` + `00-总览.md` | 对应阶段文档模板 |
| 记录问题 / 影响 / 根因 | `2.2`、`2.3`、`2.4` 对应小节 | `3. 严重程度分级` |
| 制定修复方案 | `2.5` + `2.6` | `2.3` / `2.4` |
| 执行与验证 | 当前 B 阶段上下文包 + `2.7` + `2.8` | `2.5` / `2.6` |
| 发布关闭 / 复盘 | `2.9` + `2.10` + `2.11` | 其他小节 |
| 归档排查附件 | `11-排查附件/00-附件索引.md` + 当前阶段文档 | 临时脚本输出仅可过渡使用 |

默认规则：
- Bug 处理 Agent 默认先读 `00-总览.md` 与当前阶段对应小节，不整篇读取本文。
- 只有在“设计 Bug 流程、修订 Bug 规范、跨阶段复盘”时，才整篇读取本文。

---

## 1. 目录结构规范

### 1.1 三层目录

```
docs/02-bug-fix/
└── {YYYY-MM-DD}/                     ← 一级：日期目录
    └── {BFxx}-{问题名}/              ← 二级：Bug 目录
        ├── 00-总览.md                ← 必读入口（最后完成）
        ├── state.json                ← 唯一机器状态索引
        ├── 恢复包.md                 ← 会话恢复入口
        ├── 01-问题描述.md
        ├── 02-环境与影响范围.md
        ├── 03-根因分析.md
        ├── 04-解决方案.md
        ├── 05-任务拆解.md
        ├── 06-执行记录.md
        ├── 07-测试验证.md
        ├── 08-验收发布.md
        ├── 09-复盘与沉淀.md
        ├── 10-AI协作记录.md
        ├── 11-排查附件/
        │   └── 00-附件索引.md
        ├── 事实锚点.json             ← 根因→方案→任务闭环锚点
        └── 06-上下文包/              ← bug 阶段最小上下文包
```

### 1.1.1 机器状态文件

每个 bug 目录必须包含 `state.json`，它是唯一权威机器状态文件。

最低字段：

```json
{
  "workflow_kind": "bugfix",
  "bug_id": "BF01",
  "bug_name": "问题名",
  "workflow_mode": "standard / lightweight",
  "current_stage": "B1-诊断 / B2-方案 / B3-修复 / B4-验证 / done",
  "current_step": "06-执行记录",
  "allowed_next_actions": [],
  "blocked_actions": [],
  "checklist": {},
  "context_manifest": {
    "current_packet": null,
    "packets": []
  },
  "subagent_log": [],
  "exception_log": []
}
```

强制规则：

- 主 Agent 不得只读 `00-总览.md` 就继续执行，必须先读 `state.json`。
- 不得执行 `allowed_next_actions` 之外的动作。
- 任何会写 `state.json` 的命令不得并行执行，包括上下文包生成、校验器和状态门禁更新。
- README 索引状态必须来自 `state.json`，不得从 markdown 多选模板中猜测；`stage_gates.py` 更新 bug 状态时必须同步回写 README。
- 每一步结束时的记录必须同时包含两类结论：`bug 结论` 和 `规范检查结论`；缺任一项不得 `step-done`。
- 标准模式下，`approve-release` 前必须闭合 `bug_chain`、测试、发布、复盘与 AI 协作记录；轻量模式可只保留 01-08 为硬门禁，但要在 08 中说明为何采用轻量模式。
- 发现规范缺口时，必须先写入当前 bug 的执行记录、复盘或例外日志，再立即修订流程文档；如果修订会影响后续排查，必须用更新后的规范继续执行并验证修订是否正确。
- 排查材料不得长期停留在 `/private/tmp` 或个人临时目录，必须在本次 bug 目录的 `11-排查附件/` 中留存副本并在执行记录中登记路径。
- 任一文档补丁、脚本写入、附件同步失败后，必须立即停止后续排查，先读回目标文件确认内容已落库；未确认前不得宣称已完成文档或进入下一阶段。

### 1.1.2 流程模式

- `workflow_mode` 是本次 bug 的流程模式，取值仅允许 `standard` 或 `lightweight`。
- `standard` 适用于 P0/P1 或需要完整复盘沉淀的 bug；`lightweight` 适用于可控、影响面较小的 P2/P3。
- `standard` 模式下，`09-复盘与沉淀` 和 `10-AI协作记录` 是关门前置项；`lightweight` 模式下，这两个文档可按需保留，但必须在 `08-验收发布` 中说明理由。
- `state.json.current_stage` 只存 canonical 枚举值 `B1-诊断 / B2-方案 / B3-修复 / B4-验证 / done`；`00-总览.md`、恢复包和索引页只负责显示人类可读状态，不再承担状态机真值。
- 旧的 bug 目录如果还没有 `workflow_mode`，脚本按 `lightweight` 兼容处理；新建 bug 请在初始化时显式写入模式。

### 1.2 编号规则

- **日期目录**：`YYYY-MM-DD`，使用问题发现当天的日期
- **BF 编号**：`BF{nn}`，在整个 `docs/02-bug-fix/` 下全局递增，从 `BF01` 开始，不复用、不跳号
- **问题名**：2-6 个中文词，描述问题核心现象，不描述原因

```
✓ BF01-示例接口保存500错误
✓ BF02-字段完整性计算不正确
✓ BF03-审批消息通知未发送

✗ BF01-fix-bug          （英文，无业务语义）
✗ BF01-数据库连接问题    （描述的是原因而非现象）
✗ BF01                  （无问题名）
```

### 1.3 初始化命令

大模型接到 Bug 处理任务时，自动执行：

```bash
# 创建目录骨架
python3 docs/.workflow/scripts/init_bugfix.py "问题名称"
# 轻量模式（P2/P3 可选）
python3 docs/.workflow/scripts/init_bugfix.py --mode lightweight "问题名称"

# 示例
python3 docs/.workflow/scripts/init_bugfix.py "示例接口保存500错误"
```

脚本必须同时生成：

- `state.json`
- `恢复包.md`
- 10 个标准阶段文档
- README 中的 `02-Bug Fix 索引` 行

恢复命令：

```bash
python3 docs/.workflow/scripts/init_bugfix.py --recover BF01
python3 docs/.workflow/scripts/init_bugfix.py --recover 2026-05-19/BF01
```

列表命令必须读取 `state.json`：

```bash
python3 docs/.workflow/scripts/init_bugfix.py --list-all
```

### 1.3.1 预检/分流（可选）

- 预检阶段只允许只读操作：查看已有 BF 索引、日志、复现线索、必要代码片段和相邻规范，不得创建目录或写入流程文件。
- 预检的目标是判断这是不是一个需要正式进入 BF 流程的 bug，还是重复问题、配置问题、数据问题或已有 bug 的补充材料。
- 一旦确认要进入 bug 流程，才运行 `init_bugfix.py` 建骨架；进入正式 BF 流程后，第一动作仍然是先读 `state.json` 和 `00-总览.md`，再按照门禁继续。
- 预检结果要么落到现有问题记录，要么触发正式 BF 创建；不要把预检结论混进正式 bug 的 `01-问题描述.md`。

---

## 1.4 Bug 阶段与上下文包

Bug 流程使用 B 阶段，不复用 feature 的 S 阶段编号。
`state.json.current_stage` 只存 `B1-诊断 / B2-方案 / B3-修复 / B4-验证 / done`；`分析中 / 修复方案 / 修复中 / 验证 / 已关闭` 只用于展示层。

| 阶段 | 名称 | 典型输入 | 典型输出 |
|------|------|----------|----------|
| B1 | 诊断 | 01-问题描述、02-环境与影响范围、03-根因分析 | `03-根因分析.md`、`事实锚点.json` |
| B2 | 方案 | 03-根因分析、04-解决方案、事实锚点 | `04-解决方案.md`、`05-任务拆解.md` |
| B3 | 修复 | 03-05 文档、06-执行记录、事实锚点 | 代码/规范改动、`06-执行记录.md` |
| B4 | 验证 | 05-任务拆解、06-执行记录、07-测试验证 | `07-测试验证.md`、`08-验收发布.md` |

每个阶段开始前必须生成上下文包：

```bash
python3 docs/.workflow/scripts/context_packets.py build BF01 B3
python3 docs/.workflow/scripts/context_packets.py list BF01
```

生成后的 `state.json.context_manifest.current_packet` 必须指向最新上下文包。

## 1.4.1 Bug 步骤门禁与子Agent派遣

Bug 流程复用 feature 的 `stage_gates.py`，命令参数可以直接传 `BFxx`。

```bash
python3 docs/.workflow/scripts/stage_gates.py check BF01
python3 docs/.workflow/scripts/stage_gates.py step-start BF01 "03-根因分析" '{"goal":"确认根因","expected_outputs":["03-根因分析.md","事实锚点.json"],"done_definition":["根因有证据","事实锚点已更新"],"next_step":"bug-rootcause-done"}'
python3 docs/.workflow/scripts/stage_gates.py progress BF01 '{"completed_action":"完成日志与代码证据对照","key_conclusions":["根因定位到状态门禁缺失"],"outputs":["03-根因分析.md"],"verification":["人工复核待完成"],"next_step":"补齐事实锚点"}'
python3 docs/.workflow/scripts/stage_gates.py step-done BF01 "03-根因分析" '{"outputs":["03-根因分析.md","事实锚点.json"],"key_conclusions":["bug 结论: 根因已形成事实锚点","规范检查结论: [6/6 项通过]"],"next_step":"bug-rootcause-done"}'
python3 docs/.workflow/scripts/stage_gates.py auto BF01 bug-rootcause-done
python3 docs/.workflow/scripts/stage_gates.py approve BF01 approve-rootcause
```

硬规则：

- `step-start` 的 `goal`、`expected_outputs`、`done_definition`、`next_step` 必须非空。
- 当前存在 `in_progress_step` 时，禁止再次 `step-start`、禁止 `auto`、禁止 `approve`。
- `progress` 必须记录可恢复的小动作、关键结论和下一步。
- `step-done` 必须能找到对应未闭合的 `step-start`。
- Bug 标准步骤 `01` 到 `10` 的 `step-done` 必须同步置位 `state.json.checklist`，否则机器状态不可信。
- `subagent-start` 必须校验 `context_packet` 存在、等于 `state.json.context_manifest.current_packet`，且登记在 `context_manifest.packets`。
- `subagent-start` 必须提供非空 `input_paths`、`output_paths`、`instruction`；`input_paths` 必须存在。
- `subagent-done` 必须携带 `dispatch_id`，并校验 `output_paths` 已存在。
- 当前步骤最近一次子Agent结果若为 `dispatched`、`failed`、`partial` 或 `blocked`，禁止执行 `auto`、普通 `approve-*` 或把步骤标记为 `done`；必须先重派获得 `done`，或把当前步骤记录为失败/阻塞后触发修正流程；`approve-correction` 不受该阻断限制。

### step-done 规范检查结论

`step-done` 时必须在 `key_conclusions` 中包含 `"规范检查结论: [N/6 项通过]"` 格式的总结行。每步 `step-done` 时同步更新 `10-AI协作记录.md` 的 AI 参与范围表，不得堆积到最后一次性回忆填写。

| 检查项 | 证据来源 |
|--------|----------|
| 当前步骤的输出文件是否全部写入且读回验证非空 | `outputs` 数组 + 读回日志 |
| 操作是否在 `state.json.allowed_next_actions` 范围内 | `state.json` |
| `state.json.checklist` 对应条目是否已同步置位 | `state.json.checklist` |
| 排查附件是否已在 `11-排查附件/` 留存（如有） | `11-排查附件/00-附件索引.md` |
| 是否存在未写入的临时结论（`/tmp` 等） | Agent 自检 |
| 事实锚点是否已随本次结论更新（B1/B2 阶段） | `事实锚点.json` |

缺少任意一项或任一项未通过时，`step-done` 的 `key_conclusions` 必须如实记录未通过项及原因。
- 如果在本步骤中发现了流程规范缺口，必须把缺口、修改文件、验证方式和验证结果写进 `06-执行记录.md` 或 `09-复盘与沉淀.md`，并在后续步骤中继续使用修订后的规范；不能等 bug 完结后再补修规范。
- `standard` 模式下，`09-复盘与沉淀.md` 和 `10-AI协作记录.md` 也要走这套双结论检查；`lightweight` 模式下可以按需保留，但 `08-验收发布.md` 必须说明为何未走完整闭环。

Bug 专用子Agent：

| 子Agent | 阶段 | 必载 Skill | 主要输出 | 依赖前置文档 |
|---------|------|------------|----------|-------------|
| Bug根因分析 | B1-诊断 | `bug-b1-diagnose`，有附件时加 `bug-evidence` | `03-根因分析.md`、`事实锚点.json` | `01-问题描述.md`、`02-环境与影响范围.md` |
| Bug独立复核 | B1/B2/B3/B4 | 按复核阶段加载 `bug-b1-diagnose` / `bug-b2-plan` / `bug-b3-fix` / `bug-b4-verify` | 闭环复核摘要或 `10-AI协作记录.md` | 复核对象阶段的全部文档 |
| Bug修复实现 | B3-修复 | `bug-b3-fix`，有附件时加 `bug-evidence` | 代码/规范改动、`06-执行记录.md` | `03-根因分析.md`、`04-解决方案.md`、`05-任务拆解.md`、`事实锚点.json` |
| Bug回归验证 | B4-验证 | `bug-b4-verify`，有附件时加 `bug-evidence` | `07-测试验证.md` | `05-任务拆解.md`、`06-执行记录.md` |

子Agent 返回主Agent的摘要必须能直接传给 `stage_gates.py subagent-done`，至少包含 `dispatch_id`、`status`、`summary`、`output_paths`、`key_conclusions`。`key_conclusions` 必须同时包含 bug 结论和 `规范检查结论: [N/6 项通过]`。

人工锚点：

```bash
python3 docs/.workflow/scripts/stage_gates.py approve BF01 approve-rootcause
python3 docs/.workflow/scripts/stage_gates.py approve BF01 approve-fix-plan
python3 docs/.workflow/scripts/stage_gates.py approve BF01 approve-release
```

未通过根因锚点不得进入方案确认；未通过方案锚点不得进入修复；未通过发布锚点不得关闭 bug。

### exception subagent-fallback 补偿与降级自律硬限制

当系统离线或派遣子 Agent 遭遇失败/超时，将异常追加记录至 `state.json` 的 `exception_log`，此时主 Agent 自动降级为“主线串行执行”并启动自律隔离模式：

0. **状态门禁保留原则**:
   - 记录 `exception subagent-fallback` 时，只能在 `allowed_next_actions` 中追加主线 fallback 动作，不得覆盖当前阶段已有的 `step-start xx`、`approve-*` 或 `context_packets.py build BFxx Bn` 等精确动作。
   - 若覆盖了当前精确动作，后续 `step-start` 会被状态机误拦截，视为流程规范实现缺陷，必须先修复门禁脚本后继续当前 bug。

1. **自律硬限制 (B1/B2 禁用代码修改)**:
   - 在 **B1-诊断**与**B2-方案**阶段，主 Agent 可用工具仅限于只读及搜索工具（如 `read_file`, `grep_search`, `list_dir`, `view_file` 等）。
   - 主 Agent **绝对禁止**在此期间使用任何修改或写入工具（如 `write_to_file`, `replace_file_content`, `multi_replace_file_content`）修改 Java 业务代码或 `src/` 下的任何源文件，确保“先证据、后修复”的纪律，防止边看边写导致分析偏离。
2. **自省声明 (self-review-bias)**:
   - 本步骤结束时，必须在协作记录中追加 `self-review-bias` 声明：

```markdown
## self-review-bias（主线 fallback 补偿）
- **认知盲区 1**: [主 Agent 在本步骤中可能因已有结论而产生的确认偏误]
- **自检方式 1**: [如何用独立证据排除]
- **认知盲区 2**: [另一盲区]
- **自检方式 2**: [自检方式]
```

至少列出 2 个盲区及对应自检方式。未声明 `self-review-bias` 或在 B1/B2 阶段违规动用写代码工具修改业务代码的 fallback 执行视为未闭环。

---

## 1.4.2 Superpowers 技能使用规范

Bug 处理允许用 Superpowers 里的技能，但必须按环节使用，不得混用、跳用、事后补用。

项目内 Bugfix Skills 位于 `docs/.workflow/skills/bugfix/`，用于约束本项目的 BF 文档、门禁和 Agent 输出契约；Superpowers 用于通用执行纪律。两者不互相替代。

| BF 场景 | 项目内 Skill | 用法 |
|---------|--------------|------|
| 预检/分流 | `bug-router` | 创建 BF 前只读判断：新 bug、已有 BF、配置、数据、feature、文档或不明确 |
| 会话恢复 | `bug-recovery` | 从 `state.json`、恢复包和当前上下文包恢复下一步 |
| 证据归档 | `bug-evidence` | 日志、截图、SQL、curl、导出文件、临时脚本必须归入 `11-排查附件/` |
| B1 诊断 | `bug-b1-diagnose` | 产出 01/02/03 与根因锚点 |
| B2 方案 | `bug-b2-plan` | 产出 04/05，并更新方案/任务映射 |
| B3 修复 | `bug-b3-fix` | 按 BT 执行代码或规范修复，更新 06 |
| B4 验证 | `bug-b4-verify` | 产出 07/08，执行 bug_chain 和关闭检查 |

| 环节 | 适合使用的技能 | 约束 |
|------|----------------|------|
| 01-03 问题描述 / 影响范围 / 根因分析 | `systematic-debugging` | 先证据、后修复；未完成根因分析前不得写生产代码 |
| 04-05 解决方案 / 任务拆解 | `writing-plans` | 方案与任务必须可执行、可验收、可分工 |
| 05-06 任务拆解后进入实现 | `using-git-worktrees` | 仅在代码实现阶段创建 worktree；**不允许**把 bug 文档、附件或规范文档放进 worktree |
| 06 代码修复 | `test-driven-development` | 改代码前先写失败测试；先红后绿 |
| 07-08 测试验证 / 验收发布 | `test-driven-development` + `verification-before-completion` | 先跑验证命令，再写结论；没有 fresh evidence 不得宣称完成 |
| 08-10 验收发布 / 复盘 / 协作记录 | `verification-before-completion` + `finishing-a-development-branch` | 只有在测试与构建都通过后，才进入收口与分支整理 |
| 多个互不依赖的任务并行 | `dispatching-parallel-agents` / `subagent-driven-development` | 仅适用于彼此独立、互不共享状态的任务；不得为了省事强行并行 |

硬规则：

- `systematic-debugging` 是 bug 修复的起点；任何测试失败、构建失败、复现不一致，都先回到它。
- `writing-plans` 产出的任务必须和 `05-任务拆解.md` 对齐，不能在计划外临时加活。
- `using-git-worktrees` 只用于代码和测试实现，不用于写 bug 文档、流程文档、知识库文档、附件索引或流程规范。
- `test-driven-development` 适用于所有行为变更和 bug 修复；先写失败测试，再改代码。
- `verification-before-completion` 适用于所有“已完成/已通过/可以关闭”类表述；没有新鲜验证结果不得下结论。
- `finishing-a-development-branch` 只在测试与构建结果已确认后使用，用于决定 merge / push / 保留 / 丢弃。

---

## 1.4.3 worktree 与文档边界

为了避免把流程文档和实现代码混在不同工作区，必须遵守以下边界：

- `worktree` 只放实现代码、测试代码、必要的脚本和生成产物。
- `docs/02-bug-fix/**`、`docs/.workflow/**`、`docs/03-knowledge/**`、`workflow-kit` 同步内容，全部留在**当前分支工作区**编辑，不得放进 worktree。
- 本次 bug 的目录文档、`11-排查附件/`、`state.json`、`事实锚点.json`、`恢复包.md` 都属于当前分支的流程资产，不能在 worktree 中新建或修改。
- 如果一个任务同时涉及代码与文档，必须先在当前分支完成文档，再进入 worktree 做代码；代码结束后如需补文档，再回到当前分支写入。
- 不允许把文档通过复制、软链、临时目录挂载等方式“带进” worktree；review 时发现即视为违规。

---

## 1.5 Bug 校验器

当前最低门禁是根因→方案→任务闭环：

```bash
python3 docs/.workflow/scripts/validators.py bug_chain BF01
```

`bug_chain` 检查：

- `01-问题描述.md` 至 `06-执行记录.md` 存在且非空。
- `state.json` 存在。
- `事实锚点.json.rootcause_anchors` 中每个根因都被 `solution_mappings` 覆盖。
- `solution_mappings` 中每个方案都被 `task_mappings` 覆盖。

未通过时不得进入验收发布。

---

## 2. 各文档内容规范

### 2.1 00-总览.md（最后完成，贯穿全程更新）

这是整个 Bug 处理的**指挥中心**，其他所有文档都从这里链接出去。

```markdown
# BF01-示例接口保存500错误 总览

> **所属**: docs/02-bug-fix/2026-05-15/BF01-示例接口保存500错误
> **发现时间**: 2026-05-15 14:30
> **严重程度**: P0-线上阻塞 / P1-核心功能受损 / P2-功能异常 / P3-体验问题
> **当前状态**: 分析中 / 修复中 / 验证中 / 已解决 / 已关闭
> **负责人**: [人名]
> **解决时限**: 2026-05-15 18:00

---

## 处理进度

| 步骤 | 状态 | 完成时间 | 说明 |
|------|------|----------|------|
| 01-问题描述 | ✓ 完成 | 14:35 | |
| 02-环境与影响范围 | ✓ 完成 | 14:45 | 影响全部用户 |
| 03-根因分析 | ✓ 完成 | 15:10 | 数据库字段长度不足 |
| 04-解决方案 | ✓ 完成 | 15:20 | |
| 05-任务拆解 | ✓ 完成 | 15:25 | |
| 06-执行记录 | 🔄 进行中 | | |
| 07-测试验证 | ⏳ 待开始 | | |
| 08-验收发布 | ⏳ 待开始 | | |
| 09-复盘沉淀 | ⏳ 待开始 | | |

---

## 关键结论

- **根因**: ExampleRecord 表的 reason 字段 varchar(100) 不足，超长备注导致截断异常
- **影响范围**: 备注超过 100 字的申请全部失败，约影响 XX 用户
- **解决方案**: 扩字段 + 前端长度校验 + 数据修复
- **是否需要数据修复**: 是，历史截断数据需要回溯

---

## 文档导航

- [[01-问题描述]] · [[02-环境与影响范围]] · [[03-根因分析]]
- [[04-解决方案]] · [[05-任务拆解]] · [[06-执行记录]]
- [[07-测试验证]] · [[08-验收发布]] · [[09-复盘与沉淀]]
- [[10-AI协作记录]]
```

---

### 2.2 01-问题描述.md

**目标**：让任何人读完后能精确复现问题。

```markdown
# 01-问题描述

## 现象
- 用户在提交示例接口保存时，点击提交按钮后页面报错"系统繁忙，请稍后重试"
- 后台日志显示 HTTP 500

## 复现步骤
1. 登录系统，进入示例接口保存页面
2. 填写备注（超过 100 个字符）
3. 点击提交
4. 必现报错

## 必现条件
- 备注字段输入超过 100 字

## 截图/日志
- 错误截图: [粘贴或链接]
- 关键日志:
  ```
  ERROR 2026-05-15 14:30:12 [ExampleUseCase] - Data truncation: Data too long for column 'reason'
  ```

## 发现渠道
- [ ] 用户反馈  [x] 监控告警  [ ] 测试发现  [ ] 代码审查

## 关联信息
- 环境: 生产环境 / 测试环境
- 版本: v2.3.1
- 关联需求: [[F01-需求说明书-v1]] R01
```

---

### 2.3 02-环境与影响范围.md

**目标**：量化影响，确定优先级。

```markdown
# 02-环境与影响范围

## 受影响环境
- [x] 生产环境  [ ] 预发布环境  [ ] 测试环境

## 影响范围评估

### 功能影响
| 功能 | 是否受影响 | 影响描述 |
|------|-----------|----------|
| 示例接口保存提交 | ✓ 是 | 备注超100字时必现 |
| 示例查询 | ✗ 否 | |
| 相关功能 | ✗ 否 | |

### 用户影响
- 受影响用户数: 约 XX 人（备注有超长输入历史的用户）
- 影响时段: 2026-05-10 上线后至今
- 高峰影响: 周一上午（集中提交时段）

### 数据影响
- [ ] 有数据损坏  [x] 有数据截断  [ ] 无数据影响
- 数据详情: 2026-05-10 至今，约 XX 条备注被截断至 100 字

### 严重程度定级
- **P1-核心功能受损**（示例接口保存是核心功能，影响所有有超长原因输入的用户）

## 临时规避方案
- 前端临时限制 reason 字段最多 100 字（治标，防止新增）
- 通知运营临时人工处理超长原因申请（治标）
```

---

### 2.4 03-根因分析.md

**目标**：找到真正的根因，不止于表面现象。使用 5-Why 或鱼骨图方法。

```markdown
# 03-根因分析

## 5-Why 根因追溯

| Why | 问题 | 答案 |
|-----|------|------|
| Why 1 | 为什么提交 500？ | 数据库写入异常 |
| Why 2 | 为什么数据库写入异常？ | reason 字段超长，varchar(100) 不够 |
| Why 3 | 为什么字段设计只有 100？ | 早期版本估算不足，未考虑长备注场景 |
| Why 4 | 为什么没有前端校验？ | 需求文档未明确字段长度限制，开发未主动添加 |
| Why 5 | 为什么需求未明确？ | 需求评审时未覆盖边界条件（字段长度是典型边界） |

## 根因定位
**直接原因**: `example_record.reason` 字段 varchar(100) 设计不足
**深层原因**: 需求评审边界条件未覆盖（字段长度），导致前后端均无校验

## 相关代码定位
- 表结构: `V003__create_example_record.sql` line 15
- 实体类: `ExampleRecordPO.reason` 无 `@Column(length=?)` 约束
- 前端: `ExampleRecordForm.vue` reason 字段无 maxlength

## 是否存在类似问题
- [ ] 已排查其他字段，无类似问题
- [x] 待排查：`approval_comment` 字段也可能存在同样问题

## 影响评估
- 代码层面: 需改数据库 DDL + 实体注解 + 前端校验
- 数据层面: 已截断的历史数据需要决策（保留/提示用户补充）
```

### 2.4.1 事实锚点.json 结构规范

`事实锚点.json` 是 `validators.py bug_chain` 校验的输入文件，必须严格遵循以下结构。**任意数组的元素不得使用纯字符串**，必须是 JSON 对象。

```json
{
  "_comment": "Bug 根因→方案→任务事实链锚点；validators.py bug_chain 读取",
  "bug_id": "BFxx",
  "last_updated": "ISO时间戳（如 2026-05-20T10:00:00）",

  "rootcause_anchors": [
    {
      "id": "RC01",
      "summary": "根因一句话描述",
      "source": "03-根因分析.md#锚点段落"
    }
  ],

  "solution_mappings": [
    {
      "rootcause_id": "RC01",
      "solution_ref": "04-解决方案.md#方案锚点",
      "status": "covered"
    }
  ],

  "task_mappings": [
    {
      "solution_ref": "04-解决方案.md#方案锚点",
      "task_id": "BT01",
      "task_ref": "05-任务拆解.md#任务清单",
      "status": "covered"
    }
  ]
}
```

**必填字段说明**：

| 数组 | 必填字段 | 说明 |
|------|----------|------|
| `rootcause_anchors[]` | `id`、`summary`、`source` | `id` 格式 `RC` + 数字，全局唯一 |
| `solution_mappings[]` | `rootcause_id`、`solution_ref`、`status` | `rootcause_id` 必须对应已存在的根因 |
| `task_mappings[]` | `solution_ref`、`task_id`、`status` | `solution_ref` 必须对应已存在的方案 |

**status 枚举**：`covered`（已覆盖）、`partial`（部分覆盖）、`uncovered`（未覆盖）。`bug_chain` 只将 `covered` 计为已覆盖。

**硬规则**：

- 三个数组的元素必须是 JSON 对象，不允许用字符串。`bug_chain` 遇到字符串时会报 `rootcause_anchors[X] 不是 JSON 对象` 并中断校验。
- `rootcause_anchors[].id` 必须唯一。
- `solution_mappings[].rootcause_id` 必须对应到已存在的根因 id，否则 `bug_chain` 报「根因未被方案覆盖」。
- `task_mappings[].solution_ref` 必须对应到已存在的方案 ref，否则 `bug_chain` 报「方案未被任务覆盖」。
- `03-根因分析.md` 中每个 `rootcause_anchors[].id` 都必须有对应的物理 HTML 注释锚点 `<!-- anchor: RCxx -->`；`source` 只负责可读定位，不替代物理锚点。

---

### 2.5 04-解决方案.md

**目标**：明确方案选型和决策理由，不只说"怎么做"还要说"为什么这么做"。

```markdown
# 04-解决方案

## 方案对比

| 方案 | 描述 | 优点 | 缺点 | 推荐 |
|------|------|------|------|------|
| A | 扩字段至 varchar(500) | 改动小，兼容历史数据 | 不够长远 | |
| B | 改为 TEXT 类型 | 彻底解决长度问题 | 索引限制需评估 | ✓ |
| C | 前端截断至 100 字 | 无需改库 | 数据损失，体验差 | ✗ |

## 选择方案 B，理由
- 备注是业务描述字段，无索引需求，TEXT 类型适合
- 避免将来再次扩容
- 业界实践：描述类文本字段普遍使用 TEXT

## 完整解决措施

### 紧急措施（当前立即执行）
1. 前端添加 maxlength=500 临时限制，防止新增超长数据

### 根本修复
1. `example_record.reason` 字段从 varchar(100) 改为 TEXT
2. 实体类 `ExampleRecordPO` 移除长度注解
3. 前端 reason 字段 maxlength 改为 500（业务合理上限）
4. 添加后端参数校验 `@Size(max=500)`

### 数据修复
1. 查询所有被截断的历史记录（创建时间在 2026-05-10 后，reason 长度恰好为 100）
2. 评估是否联系用户重新填写，或保留现状并加"数据已截断"标记

### 预防措施
1. 在需求评审 checklist 中增加"字段长度边界"检查项
2. 代码模板增加描述类字段默认使用 TEXT 的规范

## 方案影响
- 是否需要数据库迁移: 是，需要 Flyway 脚本
- 是否需要停机: 否，在线 DDL
- 预计修复时长: 2 小时
- 回滚方案: Flyway 回滚脚本已准备
```

---

### 2.6 05-任务拆解.md

**目标**：把解决方案拆成可执行的最小单元，每个任务有明确验收标准。

```markdown
# 05-任务拆解

## 任务清单

| 编号 | 任务 | 文件/范围 | 验收标准 | 预计时长 |
|------|------|-----------|----------|----------|
| BT01 | 数据库 DDL 迁移脚本 | `V004__fix_reason_field.sql` | Flyway 执行成功，字段类型变更 | 30min |
| BT02 | 实体类字段注解更新 | `ExampleRecordPO.java` | 移除 length 限制 | 10min |
| BT03 | 后端参数校验 | `ExampleRecordRequest.java` | `@Size(max=500)` 生效 | 15min |
| BT04 | 前端长度限制更新 | `ExampleRecordForm.vue` | maxlength=500 | 15min |
| BT05 | 数据修复脚本 | SQL 脚本 | 截断数据标记完成 | 30min |
| BT06 | 单元测试更新 | `ExampleUseCaseTest` | 500字备注提交成功 | 20min |

## 执行顺序
BT01（DDL）→ BT02+BT03（后端）→ BT04（前端）→ BT06（测试）→ BT05（数据修复，最后执行）

## 注意事项
- BT05 数据修复脚本执行前必须备份
- BT01 需要 DBA 权限，提前申请
```

---

### 2.7 06-执行记录.md

**目标**：记录每个任务的实际执行过程和关键决策，支持中断后恢复。

```markdown
# 06-执行记录

## BT01 - 数据库 DDL 迁移脚本
- **执行时间**: 2026-05-15 15:30
- **执行人**: [人名] / AI
- **实际改动**: `resources/db/migration/V004__fix_reason_field.sql`
- **执行结果**: ✓ 成功
- **验证**: `DESC example_record;` 确认 reason 字段类型为 TEXT

## BT02 - 实体类字段注解更新
- **执行时间**: 2026-05-15 15:45
- **执行结果**: ✓ 成功
- **备注**: 同时移除了注释中的"100字"描述

## BT03 - 后端参数校验
...

## 异常记录
| 时间 | 异常 | 处理方式 |
|------|------|----------|
| 15:35 | Flyway 校验失败，checksum 不匹配 | 删除旧迁移记录，重新执行 |

## 规范缺口与即时修订

- 发现的流程缺口:
- 已修改的规范/脚本:
- 用新规范继续执行的步骤:
- 验证结果:
```

---

### 2.8 07-测试验证.md

**目标**：从测试架构师视角，确保修复彻底且没有引入新问题。

```markdown
# 07-测试验证

## 验证矩阵

### 核心修复验证（必须全部通过）

| 编号 | 测试场景 | 输入 | 预期结果 | 实际结果 | 通过 |
|------|----------|------|----------|----------|------|
| V01 | 备注 100 字以内 | reason="正常长度..." | 提交成功，返回 201 | | |
| V02 | 备注恰好 500 字 | reason="..." (500字) | 提交成功，返回 201 | | |
| V03 | 备注 501 字 | reason="..." (501字) | 前端阻止，提示"最多500字" | | |
| V04 | 备注为空 | reason="" | 根据需求决定（允许或拒绝） | | |

### 回归验证（防止修复引入新问题）

| 编号 | 测试场景 | 验证目的 |
|------|----------|----------|
| R01 | 正常示例接口保存全流程 | 修复未影响主流程 |
| R02 | 字段完整性扣减 | 数据库改动未影响额度计算 |
| R03 | 审批流程 | 修复未影响审批 |
| R04 | 历史数据查询 | 截断数据仍可查询，不报错 |

### 数据修复验证

| 编号 | 验证内容 | SQL | 预期 |
|------|----------|-----|------|
| D01 | 被截断记录已标记 | `SELECT COUNT(*) FROM example_record WHERE is_truncated=1` | = XX |
| D02 | 无新增截断 | `SELECT COUNT(*) FROM example_record WHERE LENGTH(reason)=100 AND create_time > '2026-05-15'` | = 0 |

## 测试结论
- [ ] 核心修复验证：全部通过
- [ ] 回归验证：全部通过
- [ ] 数据修复验证：全部通过
- [ ] **整体结论：可以发布**
```

---

### 2.9 08-验收发布.md

**目标**：上线前的最后确认清单和上线过程记录。

```markdown
# 08-验收发布

## 发布前检查清单

### 代码检查
- [ ] 所有 BT 任务代码已提交，PR 已合并
- [ ] 代码已通过 CI 所有检查
- [ ] 07-测试验证所有用例通过
- [ ] 当前流程模式已确认（standard / lightweight）

### 数据库检查
- [ ] DDL 迁移脚本已在测试环境验证
- [ ] 数据修复脚本已在测试环境验证
- [ ] 生产数据库备份已完成（DDL 变更前）

### 回滚准备
- [ ] 回滚脚本已准备：`V004__fix_reason_field_rollback.sql`
- [ ] 回滚步骤已确认，预计回滚时间 < 5 分钟

## 发布步骤
1. 执行生产数据库备份
2. 部署后端代码（含 Flyway DDL 自动执行）
3. 部署前端代码
4. 执行核心验证与回归验证
5. 执行数据修复脚本（如有）
6. 标准模式下补齐 09-复盘与沉淀、10-AI协作记录；轻量模式下说明为何不展开完整复盘
7. 全部验证通过后宣告修复完成

## 发布记录
- **发布时间**: 2026-05-15 17:00
- **发布人**: [人名]
- **发布结果**: ✓ 成功
- **上线验证**: V01-V04 全部通过
- **数据修复**: 执行成功，共修复 XX 条记录

## 关闭条件
- [x] 所有验收场景通过
- [x] 监控无新增错误
- [x] 数据修复完成
- **关闭时间**: 2026-05-15 17:30
```

---

### 2.10 09-复盘与沉淀.md

**目标**：把这次 Bug 变成团队资产，避免下次同类问题。

```markdown
# 09-复盘与沉淀

## 时间线回顾

| 时间 | 事件 |
|------|------|
| 14:30 | 用户反馈问题 / 监控告警 |
| 14:35 | 问题定位开始 |
| 15:10 | 根因确认 |
| 15:25 | 任务拆解完成，开始修复 |
| 17:00 | 上线修复 |
| 17:30 | 关闭 |

**总历时**: 3 小时

## 好的做法（保持）
- 根因分析用了 5-Why，找到了边界条件缺失的深层原因
- 数据修复脚本在测试环境充分验证后才在生产执行

## 需要改进（行动项）

| 改进项 | 行动 | 负责人 | 完成时间 |
|--------|------|--------|----------|
| 需求评审缺少字段长度检查 | 需求评审 checklist 增加"文本字段长度边界"检查项 | | |
| 开发未主动添加参数校验 | 开发规范增加"描述类文本字段必须有 @Size 约束" | | |

## 规范修订与验证

- 本次发现的规范缺口:
- 已更新的流程文档/脚本:
- 后续使用新规范继续执行的步骤:
- 验证结论:

## 知识沉淀
以下内容已同步到知识库：

- [[03-knowledge/02-架构设计/数据库字段设计规范]] — 增加"描述类文本字段使用 TEXT"规范
- [[03-knowledge/04-运维手册/数据库迁移操作手册]] — 增加在线 DDL 操作步骤

## 同类风险排查
- [ ] 已排查所有 varchar 类型的描述字段，无类似风险
- [ ] 排查结果: `approval_comment` 字段已于本次同步修改
```

---

### 2.11 10-AI协作记录.md

**目标**：记录 AI 在此次 Bug 处理中的参与情况，用于评估 AI 协作质量。

> **填写规则**：每步 `step-done` 时同步更新本表的对应环节行，不得堆积到最后一次性回忆填写。规范检查结论也记录在此表中。
> `standard` 模式下，10 文档是关门前置项；`lightweight` 模式下可按需保留，但必须在 08 中说明原因。

```markdown
# 10-AI协作记录

## AI 参与范围

| 环节 | AI 参与 | 人工参与 | 说明 |
|------|---------|---------|------|
| 问题描述整理 | ✓ 主导 | 补充截图 | |
| 根因分析 | ✓ 辅助 | ✓ 最终确认 | 5-Why 由 AI 生成，人工验证 |
| 解决方案设计 | ✓ 生成方案 | ✓ 选型决策 | |
| 代码修复 | ✓ 实现 | Code Review | |
| 测试用例设计 | ✓ 主导 | 补充边界场景 | |
| 测试执行 | ✗ | ✓ 主导 | 生产验证必须人工 |
| 数据修复脚本 | ✓ 生成 | ✓ 审核执行 | |

## AI 执行情况评估
- 根因分析准确率: ✓ 准确
- 代码修复完整性: ✓ 完整，无遗漏
- 测试场景覆盖: ✓ 覆盖主要场景，人工补充了数据修复验证
- 是否出现跑偏: ✗ 未跑偏

## 规范修订协作

- 发现并修订了哪些流程缺口:
- 哪些步骤用新规范重新验证过:
- 需要继续观察的风险:

## 本次协作的改进建议
- AI 在 02-环境与影响范围 的用户影响数量估算需要真实数据，下次明确告知数据来源
```

---

## 3. 严重程度分级

| 级别 | 定义 | 响应时限 | 示例 |
|------|------|----------|------|
| P0-线上阻塞 | 核心功能完全不可用，大量用户受影响 | 1 小时内 | 系统无法登录、支付失败 |
| P1-核心功能受损 | 核心功能部分不可用，有规律地出现 | 4 小时内 | 特定条件下提交失败 |
| P2-功能异常 | 非核心功能异常，有规避方案 | 1 个工作日 | 导出功能偶发失败 |
| P3-体验问题 | 不影响使用，但体验较差 | 下个迭代 | 分页总数显示不正确 |

默认模式建议：
- P0 / P1 → `standard`
- P2 / P3 → `lightweight`（如业务允许）

---

## 4. 大模型使用方式

### 4.1 启动 Bug 处理

在 Claude Code 中说：

```
请按 docs/.workflow/bug修复规范.md 来处理我的 bug

bug 描述如下：
用户反馈在提交示例接口保存时，如果备注输入超过100个字，
点击提交后页面报错"系统繁忙"。后台日志有 Data truncation 错误。
```

大模型会自动：
1. 创建今天的日期目录和 BFxx 目录
2. 生成 10 个标准子文档骨架
3. 开始填写 01-问题描述

### 4.2 会话中断后恢复

```
继续处理 docs/02-bug-fix/2026-05-15/BF01-示例接口保存500错误
从 03-根因分析 继续
```

大模型会读取已有文档，从中断处继续，不重复已完成的内容。

---

## 5. init_bugfix.py 脚本规范

大模型在处理 bug 时会自动调用此脚本创建目录骨架。脚本位于 `docs/.workflow/scripts/init_bugfix.py`，自动完成：

- 创建今天的日期目录（已存在则复用）
- 扫描全部日期目录已有 BFxx 编号，全局自动递增
- 创建 10 个子文档，每个文档有对应模板内容
- 在 `docs/README.md` 中更新 Bug 索引
- `--recover BFxx` 如遇跨日期重复编号必须提示使用 `YYYY-MM-DD/BFxx` 或 `BFxx@YYYY-MM-DD`
- `--mode lightweight` 可选，用于 P2/P3 等轻量流程；默认 `standard`

---

*Bug 修复规范 v1.2 · 测试架构师视角 · 2026-05-19*
