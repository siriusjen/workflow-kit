# 开发工作流入口（Codex / AGENTS.md）

> Codex 启动时自动加载此文件。自动化开发工作流规范本体在 `docs/.workflow/工作流规范.md`。

## 主 Agent 职责

本项目采用大模型自动化开发工作流 v2.0。主 Agent 负责决策、指挥、检查和修正；具体需求交叉验证、技术方案、落地计划、任务拆分、任务实现、测试验证、HTTP 接口验收、全链路验证按标准流程必须交给 `docs/.workflow/agents/` 中定义的子 Agent 或并行 Agent。

在当前 Codex 环境中，实际派遣前必须确认用户已明确授权使用子 Agent / 多 Agent；未授权或平台不可用时，必须先记录 `exception subagent-fallback "原因"`，再按同一检查清单在主线内临时执行并记录。

## 启动协议

每次新会话必须先识别本地规范文档，不依赖用户重复说明：

1. 读 `docs/README.md`，确认当前项目文档导航和目录约定。
2. 读 `docs/.workflow/工作流规范.md` 的速查卡。
3. 读 `docs/.workflow/Obsidian文档规范.md`，确认需求、Bug、知识库等文档应放置的位置。
4. 如涉及项目知识沉淀，读 `docs/.workflow/知识库规范.md`。
5. Java 相关开发还要读 `docs/.workflow/Java开发规范.md` 的速查卡；非 Java 项目按项目覆盖层改为对应语言规范。
6. 如存在进行中的 feature，读 `state.json` 后先检查 `context_manifest.current_packet`；若为空或阶段不匹配，先运行 `context_packets.py build` 生成当前阶段上下文包。

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

## 工作流脚本

```bash
# 初始化新 feature
python3 docs/.workflow/scripts/init_feature.py "功能名"

# 查看当前状态
python3 docs/.workflow/scripts/stage_gates.py check <FID>

# 生成阶段上下文包（每个阶段开始、派遣子Agent前必须调用）
python3 docs/.workflow/scripts/context_packets.py build <FID> S6 --task T01
python3 docs/.workflow/scripts/context_packets.py build <FID> S8
python3 docs/.workflow/scripts/context_packets.py list <FID>

# 输出恢复确认卡
python3 docs/.workflow/scripts/init_feature.py --recover <FID>

# 记录步骤开始（每开始一小步必须调用；四项必须非空）
python3 docs/.workflow/scripts/stage_gates.py step-start <FID> "步骤名" '{"goal":"...","expected_outputs":["..."],"done_definition":["..."],"next_step":"..."}'

# 记录进行中进展（当前步骤未完成，但一个可检查小动作已完成时调用）
python3 docs/.workflow/scripts/stage_gates.py progress <FID> '{"completed_action":"...","key_conclusions":["..."],"outputs":["..."],"verification":["..."],"next_step":"..."}'

# 记录步骤完成
python3 docs/.workflow/scripts/stage_gates.py step-done <FID> "步骤名" '{"outputs":["..."],"key_conclusions":["..."],"next_step":"..."}'

# 记录子Agent派遣和返回（真实派遣或并行派遣都必须记录）
python3 docs/.workflow/scripts/stage_gates.py subagent-start <FID> "任务实现" '{"context_packet":"06-上下文包/上下文包-S6-实现.md","input_paths":["03-落地计划/任务清单.json"],"output_paths":["04-实现记录/实现记录-YYYYMMDD-T01.md"],"instruction":"实现 T01"}'
python3 docs/.workflow/scripts/stage_gates.py subagent-done <FID> "任务实现" '{"status":"done","summary":"...","output_paths":["..."],"key_conclusions":["..."]}'

# OpenSpec 决策、Jar 构建和 HTTP 验收门禁
python3 docs/.workflow/scripts/stage_gates.py auto <FID> openspec-decision-recorded
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

## 子 Agent 派遣原则

子 Agent 定义在 `docs/.workflow/agents/`。标准流程必须使用多 Agent；派遣时必须提供独立上下文、明确输入输出、限定范围，并要求结构化摘要返回。同一任务连续修正 3 次仍不通过时，停止并请求人工介入。

若当前环境不能实际派遣，必须写入 `exception subagent-fallback`，不得静默主线替代。

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
- `step-done` 必须有对应未闭合的 `step-start`，并提供非空 `key_conclusions` 与 `next_step`。
- 未生成当前阶段上下文包，不得派遣子 Agent。
- `subagent-start` 必须提供非空 `context_packet/input_paths/output_paths/instruction`，且 `input_paths` 必须存在；`subagent-done` 必须匹配当前阶段、当前步骤中未关闭的 `subagent-start`，且 `output_paths` 必须存在。
- 每个 `implement-Txx` 完成前必须增量更新 `04-实现记录/*.md`，并在 `step-done` 的 `outputs` 中列出该实现记录。
- 单元测试、聚焦测试通过后必须打包；打包完成后提示人工本地启动/部署服务，并通过真实 HTTP API 请求完成验收；未执行 `artifact-package-done` 和 `http-acceptance-done` 不允许 `approve-release`。

## 严格禁止

- 跳过 `state.json` 直接行动
- 执行 `allowed_next_actions` 之外的行为
- 未 `step-start` 就开始执行当前小步骤
- 未 `step-done` 就进入下一步
- 未生成/读取当前阶段上下文包就派遣子 Agent 或加载大量上下文
- `implement-Txx` 未写入对应实现记录就标记完成
- 未打包、未完成人工本地部署后的 HTTP API 验收就关闭需求
- 未读规范就开始实现
- 在未确认需求基线前写代码或拆任务

## 项目覆盖层

安装到具体项目后，在本文件下方补充项目自己的 `Repository Guidelines`：

- 技术栈和目录结构
- 构建、测试、运行命令
- 语言专项规范
- 安全与配置要求
- PR、提交和发布约定
- 业务知识库入口
