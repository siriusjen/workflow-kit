# workflow-kit 安装说明

`workflow-kit` 是一套可迁移的大模型开发工作流基线，包含工作流引擎、入口受管块模板和使用说明。安装时只复制通用流程资产，不复制任何来源项目的 feature、bug、knowledge 业务内容。

workflow-kit 语言无关。Java/Maven/Jar 只是默认构建验收 profile；前端、Go、Python 等项目安装后通过 `docs/.workflow/project_config.json` 覆盖构建产物和命令。

## 包内结构

```text
workflow-kit/
├── AGENTS.md
├── CLAUDE.md
├── INSTALL.md
├── 使用指南.md
└── docs/
    ├── README.md
    ├── 01-features/.gitkeep
    ├── 02-bug-fix/.gitkeep
    ├── 03-knowledge/.gitkeep
    └── .workflow/
        ├── 工作流规范.md
        ├── project_config.json
        ├── agents/
        ├── scripts/
        │   └── install_entry.py
        └── templates/
            └── entry/
                ├── AGENTS.md.tpl
                └── CLAUDE.md.tpl
```

## 安装到新项目

在目标项目根目录外执行：

```bash
mkdir -p your-project/docs/{01-features,02-bug-fix,03-knowledge}
cp -r workflow-kit/docs/.workflow your-project/docs/.workflow
cp -n workflow-kit/docs/README.md your-project/docs/README.md
cp workflow-kit/INSTALL.md your-project/
cp workflow-kit/使用指南.md your-project/
python3 your-project/docs/.workflow/scripts/install_entry.py --target your-project
```

`install_entry.py` 会把 `WORKFLOW-KIT` 受管块注入到目标项目的 `AGENTS.md` 和 `CLAUDE.md`：

- 目标文件不存在：创建文件并写入受管块。
- 目标文件存在且已有受管块：只替换受管块。
- 目标文件存在但没有受管块：在末尾追加，保留原内容。
- `--dry-run`：只打印 unified diff，不写文件。
- `--only AGENTS.md` 或 `--only CLAUDE.md`：只更新一个入口文件。

降级方式：如果目标环境不能运行 Python，可手工复制 `docs/.workflow/templates/entry/*.tpl` 中的 `WORKFLOW-KIT` 受管块到目标入口文件，保留项目自己的 `Repository Guidelines`、构建命令、目录结构和业务知识入口。

## 安装后确认

1. 入口文件已合并：
   - Codex 项目：`AGENTS.md`
   - Claude Code 项目：`CLAUDE.md`

2. 构建产物配置已按项目确认：
   - 默认 Java profile：`target/*.jar`、`mvn -DskipTests package`、`Jar`。
   - 前端示例：

```json
{
  "build": {
    "artifact_pattern": "dist/**/*",
    "artifact_label": "frontend dist",
    "build_command": "npm run build",
    "build_record_keyword": "dist"
  }
}
```

   - Go 示例：

```json
{
  "build": {
    "artifact_pattern": "bin/*",
    "artifact_label": "Go binary",
    "build_command": "go build -o bin/app ./...",
    "build_record_keyword": "bin/"
  }
}
```

3. 文档 Git 策略已确认：
   - `docs/.workflow/` 建议纳入版本管理。
   - `docs/01-features/`、`docs/02-bug-fix/`、`docs/03-knowledge/` 是否纳入 Git，由目标项目决定。

## 验证安装

在新项目根目录执行：

```bash
python3 docs/.workflow/scripts/init_feature.py --list
```

空项目应能正常输出暂无 feature 或空列表。

再检查入口文件是否包含受管块和关键路径：

```bash
grep -n "WORKFLOW-KIT:START" AGENTS.md CLAUDE.md
grep -n "docs/README.md" AGENTS.md CLAUDE.md
grep -n "工作流规范.md" AGENTS.md CLAUDE.md
grep -n "context_packets.py" AGENTS.md CLAUDE.md
```

确认构建配置：

```bash
cat docs/.workflow/project_config.json
```

## 依赖

- Python 3.8+，无第三方依赖
- Git，可选；S6 实现阶段推荐用 worktree 隔离代码修改
- Claude Code 或 Codex
- Obsidian，可选；vault 可指向项目根目录或 `docs/`

## 不迁移的内容

从业务项目抽取时不要带走：

- `docs/01-features/Fxx-*`
- `docs/02-bug-fix/` 下的具体 bug 记录
- `docs/03-knowledge/` 下的业务知识、环境信息、账号或运维记录
- 来源项目根目录的业务版 `CLAUDE.md` / `AGENTS.md` 标记外内容
- 来源项目根 `openspec/` 里的历史业务 change
