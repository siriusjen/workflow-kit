# 项目文档导航

> Obsidian vault 指向项目根目录后，此文件是整个 docs 的统一索引入口。
> 由大模型和人工共同维护，每次新增重要文档时更新。
>
> `workflow-kit` 语言无关。Java/Maven/Jar 只是默认构建验收 profile；前端、Go、Python 等项目安装后通过 `docs/.workflow/project_config.json` 覆盖构建产物和命令。

---

## 快速导航

| 我要做什么 | 去哪里 |
|-----------|--------|
| 开始一个新功能 | 运行 `python3 docs/.workflow/scripts/init_feature.py "功能名"` |
| 处理一个 Bug | 运行 `python3 docs/.workflow/scripts/init_bugfix.py "问题名"` |
| 查看项目架构 | [[03-knowledge/02-架构设计/00-架构总览]] |
| 查找环境连接信息 | [[03-knowledge/01-环境配置/00-环境总览]] |
| 查看业务规则 | [[03-knowledge/05-业务规则/00-业务规则总览]] |
| 恢复中断的会话 | `python3 docs/.workflow/scripts/init_feature.py --recover Fxx` |
| 查看所有功能状态 | `python3 docs/.workflow/scripts/init_feature.py --list` |
| 恢复中断的 bug 会话 | `python3 docs/.workflow/scripts/init_bugfix.py --recover BFxx` |
| 查看今天的 bug 列表 | `python3 docs/.workflow/scripts/init_bugfix.py --list` |
| 查看全部 bug 状态 | `python3 docs/.workflow/scripts/init_bugfix.py --list-all` |
| 生成阶段上下文包 | `python3 docs/.workflow/scripts/context_packets.py build Fxx S6 --task T01` |
| 记录 OpenSpec 决策 | 写入 `01-需求确认/OpenSpec决策记录-YYYYMMDD.md` 后执行 `stage_gates.py auto Fxx openspec-decision-recorded` |
| 覆盖构建 profile | 修改 `docs/.workflow/project_config.json` 的 `build` 段 |

---

## 文档结构

```
docs/
├── 01-features/       功能开发（由脚本自动创建）
├── 02-bug-fix/        Bug 处理（由脚本自动创建）
├── 03-knowledge/      项目知识库（人工维护）
├── 04-retrospective/  复盘与改进（可选）
└── .workflow/         工作流引擎（大模型用的规范）
```

---

## 01-功能开发（Features）

| 编号 | 功能名 | 状态 | 最后更新 |
| ---- | ------ | ---- | -------- |
| F03 | 入职离职当日自动补卡-复测 | 进行中 | 2026-05-18 |

*（由 init_feature.py 自动维护）*

---

## 02-Bug Fix 索引

| 日期 | 编号 | 问题名 | 状态 | 链接 |
| ---- | ---- | ------ | ---- | ---- |
| 2026-05-19 | BF01 | Bug流程状态门禁缺失 | done | [[02-bug-fix/2026-05-19/BF01-Bug流程状态门禁缺失/00-总览]] |

## 03-知识库

- [[03-knowledge/00-索引]] — 知识库总索引（快速查找环境信息、架构文档、业务规则）

---

## .workflow — 工作流引擎规范

> 以下文档是大模型读的规范，人工可以阅读但不要随意修改

| 文档 | 说明 |
|------|------|
| [[.workflow/工作流规范]] | 完整开发流程规范 v2.0 |
| [[.workflow/Java开发规范]] | Java 项目覆盖层规范；非 Java 项目可替换为对应语言规范 |
| [[.workflow/Obsidian文档规范]] | 文档命名、结构、标签规范 |
| [[.workflow/bug修复规范]] | Bug 处理 10 步全流程规范 |
| [[.workflow/知识库规范]] | 知识库目录结构和维护规范 |

## 构建 profile 示例

默认 Java profile:

```json
{
  "build": {
    "artifact_pattern": "target/*.jar",
    "artifact_label": "Jar",
    "build_command": "mvn -DskipTests package",
    "build_record_keyword": "Jar"
  }
}
```

前端示例:

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

Go 示例:

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

## 上下文加载原则

本项目使用“索引 + 摘要 + 按需加载”：

- 先读本索引，再读 feature 的 `导航.md` 和 `state.json`。
- 每阶段开始、派遣子Agent前，先生成 `06-上下文包/上下文包-Sx-*.md`。
- 大模型默认只读取上下文包和其中列出的精确路径。
- 需要额外文件时，先用 `rg` 定位，再读取最小片段。

---

*最后更新: 2026-05-29*
