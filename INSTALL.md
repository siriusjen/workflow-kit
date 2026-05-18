# workflow-kit 安装说明

`workflow-kit` 是一套可迁移的大模型开发工作流基线，包含工作流引擎、项目入口模板和使用说明。安装时只复制通用流程资产，不复制任何来源项目的 feature、bug、knowledge 业务内容。

## 包内结构

```text
workflow-kit/
├── INSTALL.md
├── 使用指南.md
├── 开发AGENTS.md
├── 开发CLAUDE.md
└── docs/
    ├── README.md
    ├── 01-features/.gitkeep
    ├── 02-bug-fix/.gitkeep
    ├── 03-knowledge/.gitkeep
    └── .workflow/
        ├── 工作流规范.md
        ├── Java开发规范.md
        ├── Obsidian文档规范.md
        ├── 知识库规范.md
        ├── bug修复规范.md
        ├── agents/
        ├── scripts/
        └── templates/
```

## 安装到新项目

在目标项目根目录外执行：

```bash
cp -r workflow-kit/docs your-project/
cp workflow-kit/开发AGENTS.md your-project/AGENTS.md
cp workflow-kit/开发CLAUDE.md your-project/CLAUDE.md
cp workflow-kit/INSTALL.md your-project/
cp workflow-kit/使用指南.md your-project/
```

如果目标项目已有 `AGENTS.md` 或 `CLAUDE.md`，不要直接覆盖。把模板中的“开发工作流入口 / 启动协议 / 核心脚本 / 严格禁止”合并到现有入口文件中，并保留目标项目自己的 `Repository Guidelines`、构建命令、目录结构和业务知识入口。

## 安装后确认

1. 入口文件已合并：
   - Codex 项目：`AGENTS.md`
   - Claude Code 项目：`CLAUDE.md`

2. 语言规范已按项目调整：
   - Java 项目可保留并默认读取 `docs/.workflow/Java开发规范.md`。
   - 非 Java 项目可保留但不默认读取，或替换为对应语言规范。

3. 构建产物配置已按项目确认：
   - 默认配置偏向 Java/Maven：`target/*.jar`、`mvn -DskipTests package`。
   - 非 Java 项目必须创建或覆盖 `docs/.workflow/project_config.json` 的 `build.artifact_pattern`、`artifact_label`、`build_command`、`build_record_keyword`。

4. 文档 Git 策略已确认：
   - `docs/.workflow/` 建议纳入版本管理。
   - `docs/01-features/`、`docs/02-bug-fix/`、`docs/03-knowledge/` 是否纳入 Git，由目标项目决定。

5. OpenSpec 使用方式已确认：
   - 工作流默认使用 feature-local OpenSpec：`docs/01-features/Fxx-功能名/openspec/`。
   - 如果目标项目依赖根目录 `openspec/` CLI，可把根目录作为 CLI 镜像或全局能力规范；feature 文档仍以 feature-local openspec 为准。

## 验证安装

在新项目根目录执行：

```bash
python3 docs/.workflow/scripts/init_feature.py --list
```

空项目应能正常输出暂无 feature 或空列表。

再检查入口文件是否包含关键路径：

```bash
grep -n "docs/README.md" AGENTS.md CLAUDE.md
grep -n "工作流规范.md" AGENTS.md CLAUDE.md
grep -n "context_packets.py" AGENTS.md CLAUDE.md
grep -n "docs/01-features" AGENTS.md CLAUDE.md
```

Java 项目再确认：

```bash
grep -n "Java开发规范.md" AGENTS.md CLAUDE.md
```

如需覆盖默认构建配置，创建并确认：

```bash
cat docs/.workflow/project_config.json
```

Java/Maven/Jar 项目可以不创建该文件，脚本会使用默认值。非 Java 项目安装后先创建或覆盖该文件，再进入 S8 构建验收。

## 依赖

- Python 3.8+，无第三方依赖
- Git，可选；S6 实现阶段推荐用 worktree 隔离代码修改
- Claude Code 或 Codex
- Obsidian，可选；vault 可指向项目根目录或 `docs/`
- Java/Maven 不是 workflow-kit 的硬依赖，只是脚本默认值；非 Java 项目通过项目内 `project_config.json` 覆盖。

## 不迁移的内容

从业务项目抽取时不要带走：

- `docs/01-features/Fxx-*`
- `docs/02-bug-fix/` 下的具体 bug 记录
- `docs/03-knowledge/` 下的业务知识、环境信息、账号或运维记录
- 来源项目根目录的业务版 `CLAUDE.md`
- 来源项目根 `openspec/` 里的历史业务 change

## 推荐维护方式

把 `workflow-kit` 当成“通用包 + 项目覆盖层”：

- 通用包放工作流规范、脚本、通用子 Agent、通用模板和安装文档。
- 每个项目自己维护入口文件中的项目覆盖层，包括 `Repository Guidelines`、语言规范、构建命令、目录结构、业务知识库入口和专项规范启用策略。
