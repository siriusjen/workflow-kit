<!-- WORKFLOW-KIT:START -->
# 开发工作流入口（Claude Code / CLAUDE.md）

> Claude Code 启动时自动加载此文件。自动化开发工作流规范本体在 `docs/.workflow/工作流规范.md`。

## 主 Agent 职责

本项目采用大模型自动化开发工作流 v2.0。主 Agent 负责决策、指挥、检查和修正；具体需求交叉验证、技术方案、落地计划、任务拆分、任务实现、测试验证、HTTP 接口验收、全链路验证按标准流程必须交给 `docs/.workflow/agents/` 中定义的子 Agent 或并行 Agent。

如果当前 Claude Code 环境无法实际派遣子 Agent，或未获得明确授权，必须先记录 `exception subagent-fallback "原因"`，再按同一检查清单由主线临时执行并记录。不得静默跳过子 Agent 纪律。

## 启动协议

每次新会话必须先识别本地规范文档，不依赖用户重复说明：

1. 读 `docs/README.md` 的快速导航、文档结构和上下文加载原则，确认当前项目文档导航和目录约定。
2. 只读 `docs/.workflow/工作流规范.md` 的速查卡和最小加载地图；进入具体阶段后再按地图读取对应小节。
3. 只读 `docs/.workflow/Obsidian文档规范.md` 的目录总览和当前任务相关小节，确认需求、Bug、知识库等文档应放置的位置。
4. 如涉及项目知识沉淀，只读 `docs/.workflow/知识库规范.md` 的目录结构和当前知识类型相关小节。
5. Java 相关开发只读 `docs/.workflow/Java开发规范.md` 的速查卡和当前动作对应的最小加载地图；非 Java 项目按项目覆盖层改为对应语言规范。
6. 如存在进行中的 feature，读 `state.json` 后先检查 `context_manifest.current_packet`；若为空或阶段不匹配，先运行 `context_packets.py build` 生成当前阶段上下文包。
7. 恢复处理中断时，必须检查四项：未闭合的 `in_progress_step`、`subagent_log` 中未返回或失败的派遣、最近 `exception_log`、当前阶段上下文包。

上下文预算硬规则：

- 启动协议中的“读”均指读取指定文件的索引、速查卡、最小加载地图或明确小节，不得默认全文读取 `docs/.workflow/*.md`。
- 只有在修订规范、审计全流程、排查跨阶段规则冲突时，才允许全文读取单个规范文档；需要多个大文档时，先用 `rg`、目录和最小加载地图定位。
- 子 Agent 默认只读取上下文包和其中列出的精确路径；需要额外文件时，先定位再读取最小片段。

默认目录约定：

- 功能需求归档到 `docs/01-features/Fxx-功能名/00-需求输入/`。
- Bug 处理归档到 `docs/02-bug-fix/`。
- 长期架构、环境、业务规则沉淀归档到 `docs/03-knowledge/`。
- `.workflow/` 是大模型工作流规范区，不把具体业务需求直接放入该目录。

如存在进行中的 `docs/01-features/Fxx-*`：

- 读取对应 `state.json`
- 输出恢复确认卡
- 等待用户指令

如收到新需求：

- 询问输入模式：A=已有文档，B=只有想法
- 执行 `python3 docs/.workflow/scripts/init_feature.py "功能名"`
- 进入双轨入口流程

如收到新 Bug 描述（如包含“报错/异常/错误/导出失败/不准/崩了”等特征词意图，且非 BFxx 格式）：

- 主 Agent 必须进行前置智能拦截，不允许静默创建目录或文档。
- 拦截并询问：“检测到 Bug 描述，即将为您启动自动排查流程 BFxx，是否继续？”。
- 仅当用户明确回复“继续/确认/yes”时，才调用 `python3 docs/.workflow/scripts/init_bugfix.py "<问题描述>"` 初始化骨架，开启 B1-诊断阶段。

## 工作流脚本

```bash
# 初始化新 feature
python3 docs/.workflow/scripts/init_feature.py "功能名"

# 查看当前状态
python3 docs/.workflow/scripts/stage_gates.py check <FID>

# 生成阶段上下文包（每个阶段开始、派遣子Agent前必须调用）
python3 docs/.workflow/scripts/context_packets.py build <FID> S6 --task T01
python3 docs/.workflow/scripts/context_packets.py build <FID> S8
python3 docs/.workflow/scripts/context_packets.py build <FID> S10
python3 docs/.workflow/scripts/context_packets.py list <FID>

# 输出恢复确认卡
python3 docs/.workflow/scripts/init_feature.py --recover <FID>

# 记录步骤开始（每开始一小步必须调用；四项必须非空）
python3 docs/.workflow/scripts/stage_gates.py step-start <FID> "步骤名" '{"goal":"...","expected_outputs":["..."],"done_definition":["..."],"next_step":"..."}'

# 记录进行中进展（当前步骤未完成，但一个可检查小动作已完成时调用）
python3 docs/.workflow/scripts/stage_gates.py progress <FID> '{"completed_action":"...","key_conclusions":["..."],"outputs":["..."],"verification":["..."],"next_step":"..."}'

# 记录步骤完成；若当前存在唯一 in_progress_step，可省略“步骤名”
python3 docs/.workflow/scripts/stage_gates.py step-done <FID> "步骤名" '{"outputs":["..."],"key_conclusions":["..."],"next_step":"..."}'
python3 docs/.workflow/scripts/stage_gates.py step-done <FID> '{"outputs":["..."],"key_conclusions":["..."],"next_step":"..."}'

# 记录子Agent派遣和返回（真实派遣或并行派遣都必须记录；只有单个未完成同名派遣时 subagent-done 可省 dispatch_id）
python3 docs/.workflow/scripts/stage_gates.py subagent-start <FID> "任务实现" '{"context_packet":"06-上下文包/上下文包-S6-实现.md","input_paths":["03-落地计划/任务清单.json"],"output_paths":["04-实现记录/实现记录-YYYYMMDD-T01.md"],"instruction":"实现 T01"}'
python3 docs/.workflow/scripts/stage_gates.py subagent-done <FID> "任务实现" '{"dispatch_id":"d-YYYYMMDDHHMMSS-xxxxxxxx","status":"done","summary":"...","output_paths":["..."],"key_conclusions":["..."]}'
python3 docs/.workflow/scripts/stage_gates.py subagent-done <FID> "任务实现" '{"status":"done","summary":"...","output_paths":["..."],"key_conclusions":["..."]}'

# OpenSpec 决策、事实继承、一致性校验、构建产物和 HTTP 验收门禁
python3 docs/.workflow/scripts/stage_gates.py auto <FID> openspec-decision-recorded
python3 docs/.workflow/scripts/validators.py fact_inheritance <FID>
python3 docs/.workflow/scripts/stage_gates.py auto <FID> artifact-package-done
python3 docs/.workflow/scripts/stage_gates.py auto <FID> http-acceptance-done

# 人工锚点
python3 docs/.workflow/scripts/stage_gates.py approve <FID> approve-req-input
python3 docs/.workflow/scripts/stage_gates.py approve <FID> approve-req-final
python3 docs/.workflow/scripts/stage_gates.py approve <FID> approve-tech-question
python3 docs/.workflow/scripts/stage_gates.py approve <FID> approve-verify
python3 docs/.workflow/scripts/stage_gates.py approve <FID> approve-release

# 校验器
python3 docs/.workflow/scripts/validators.py req_coverage <FID>
python3 docs/.workflow/scripts/validators.py rdt_mapping <FID>
python3 docs/.workflow/scripts/validators.py impl_drift <FID> <T_NUMBER>
python3 docs/.workflow/scripts/validators.py rdtv_closure <FID>

# 上下文用量
python3 docs/.workflow/scripts/stage_gates.py ctx-update <FID> <百分比>
```

S8 构建产物默认按 Java/Maven/Jar 校验，配置在 `docs/.workflow/project_config.json`；非 Java 项目必须按实际产物覆盖。`project_config.json` 的 `workflow` 段还包含上下文提醒阈值、压缩阈值、子Agent修正阈值、feature/bugfix 流程启用开关，详见 `docs/.workflow/工作流规范.md` 的子Agent派遣原则。
技术方案阶段必须先输出 `01-需求确认/需求事实锚点.json`，再输出 `02-技术方案/代码影响点与依赖逻辑清单.md` 和 `02-技术方案/技术方案一致性检查.json`，避免方案自洽但偏离需求或现有实现。

## 子 Agent 派遣原则

子 Agent 定义在 `docs/.workflow/agents/`。标准流程必须使用多 Agent；派遣时必须提供独立上下文、明确输入输出、限定范围，并要求结构化摘要返回。同一任务连续修正 3 次仍不通过时，停止并请求人工介入。

派遣前必须先生成阶段上下文包。子 Agent 默认只读取上下文包和其中列出的精确路径；需要额外文件时，先用 `rg` 定位，再按最小片段读取，并在返回摘要中说明原因。

## 上下文加载协议

本项目必须执行“索引 + 摘要 + 按需加载”：

- `docs/README.md` 是全局索引。
- 每个 feature 的 `导航.md` 是 feature 索引。
- `state.json` 是机器状态索引。
- `06-上下文包/上下文包-Sx-*.md` 是阶段最小上下文摘要。
- 子 Agent 和主 Agent 不允许默认加载完整需求历史、完整代码库或完整测试日志。
- 每阶段开始和每次派遣子 Agent 前必须运行 `context_packets.py build`。

## 恢复与验收硬门禁

- `step-start` 缺少非空 `goal`、`expected_outputs`、`done_definition`、`next_step` 时，脚本必须失败。
- `progress` 必须记录非空 `completed_action`、`key_conclusions`、`next_step`，且 `outputs` 与 `verification` 不能同时为空。
- `step-done` 必须有对应未闭合的 `step-start`，并提供非空 `key_conclusions` 与 `next_step`；若当前只有一个 `in_progress_step`，CLI 可省略步骤名。
- 未生成当前阶段上下文包，不得派遣子 Agent。
- `subagent-start` 必须提供非空 `context_packet/input_paths/output_paths/instruction`，且 `input_paths` 必须存在；`subagent-start` 会输出 `dispatch_id`，并行或同名子 Agent 返回时 `subagent-done` 必须携带该值；只有单个未完成同名派遣时可省略 `dispatch_id`；`output_paths` 必须存在。
- 子 Agent 定义文件 frontmatter 声明 `prerequisites` 时，`subagent-start` 必须先校验其中的 `path` 或 `glob` 是否存在。
- 当前步骤最近一次子Agent结果若为 `dispatched`、`failed`、`partial` 或 `blocked`，禁止把步骤标记为 `done`，也禁止执行 `auto` 或普通人工锚点；必须先重派获得 `done`，或把当前步骤记录为失败/阻塞后触发修正流程；`approve-correction` 不受该阻断限制。
- 每个 `implement-Txx` 完成前必须增量更新 `04-实现记录/*.md`，并在 `step-done` 的 `outputs` 中列出该实现记录。
- 单元测试、聚焦测试通过后必须按 `project_config.json` 打包构建产物；构建完成后提示人工本地启动/部署服务，并通过真实 HTTP API 请求完成验收；未执行 `artifact-package-done` 和 `http-acceptance-done` 不允许 `approve-release`。

## 严格禁止

- 跳过 `state.json` 直接行动
- 执行 `allowed_next_actions` 之外的行为
- 未 `step-start` 就开始执行当前小步骤
- 未 `step-done` 就进入下一步
- 未生成/读取当前阶段上下文包就派遣子 Agent 或加载大量上下文
- `implement-Txx` 未写入对应实现记录就标记完成
- 未打包构建产物、未完成人工本地部署后的 HTTP API 验收就关闭需求
- 未读规范就开始实现
- 在未确认需求基线前写代码或拆任务

> 保留此受管块，`python3 docs/.workflow/scripts/install_entry.py` 会据此刷新工作流入口内容。
<!-- WORKFLOW-KIT:END -->

## 项目覆盖层

安装到具体项目后，在本文件下方补充项目自己的 `Repository Guidelines`：

- 技术栈和目录结构
- 构建、测试、运行命令
- 语言专项规范
- 安全与配置要求
- PR、提交和发布约定
- 业务知识库入口
