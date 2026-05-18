# Java 开发规范（AI 协作版）

> **版本**: v3.0
> **更新时间**: 2026-05-15
> **适用范围**: 配合"大模型自动化开发工作流 v2.0"使用，约束 AI 在 S6 实现阶段的编码行为
> **配套**: `docs/.workflow/工作流规范.md`（流程规范）+ 本文档（编码规范）

---

## 速查卡（S6 默认先读，20行以内）

```text
1. 不假设：T 有歧义先停，列问题，不凭猜测编码。
2. 简洁优先：只做当前 T，设计复杂度由 D 决定，不在 S6 自行扩展。
3. 精准修改：只改 scope；scope 外改动必须说明原因并接受 drift 校验。
4. 目标驱动：acceptance 是唯一成功标准，必须有真实验证证据。
5. 先 TDD：先验证 RED，再写最小 GREEN，最后重构且保持通过。
6. 先自检：编码前看 T/R/D/scope/acceptance；编码后做 diff review。
7. 实现记录必须写：改动范围、TDD 证据、D 对照、acceptance 证据、自检结果。
```

## 最小加载地图（默认按需，不整篇读）

| 当前任务 | 默认先读 | 只有需要时再读 |
|----------|----------|----------------|
| 收到 T 准备编码 | 速查卡 + `4.1 编码前自检` + `6.1 S6 强制顺序` | `0. 规范定位与优先级` |
| 设计包结构 / 命名 | `2. 包结构与建模` | `3. 代码规范` 中相关小节 |
| 写具体实现 | 速查卡 + `3. 代码规范` 中对应小节 | 其他 Part |
| 写测试 / 重构 | `5. 测试与重构` | `3. 代码规范` 中相关实现约束 |
| 做编码后检查 | `4.2` + `4.3` + `4.4` | `1. 四原则` |
| 写实现记录 | `6.2 实现记录模板` | 其他章节 |
| 需要全量审计本规范 | 全文 | 无 |

默认规则：
- 任务实现子Agent 默认不整篇读取本文，而是先读速查卡，再按当前动作读取必要小节。
- 只有在“规范审计 / 规范修订 / 多处规则冲突”这三类任务中，才允许整篇读取本文。

---

## 0. 规范定位与优先级

### 0.1 两份规范的边界

| 文档 | 负责 | 在哪个阶段生效 |
|------|------|---------------|
| 工作流规范 | 需求 → 方案 → 计划 → 任务 → 实现 → 测试 → 构建验收 → 全链路验证 → 发布关闭的流程纪律 | 全流程 S1–S10 |
| 本规范 | 代码怎么写、AI 编码时怎么思考、如何避免跑偏 | 重点在 S6 实现，部分约束在 S7/S8 |

**冲突仲裁**：流程规则与编码规则冲突时以流程规范为准；代码实现细节争议以"可读、可测、可维护、可审计"为最终标准。

### 0.2 本规范要解决的核心痛点

```
AI 编码时最常犯的 6 类错误：
①  默默做错误假设而不澄清
②  过度抽象、堆砌设计模式、200 行任务写成 1000 行
③  修改无关代码（顺手"改进"了不该动的地方）
④  跑偏 task 的 scope（超出 T 编号定义范围）
⑤  忘记现有规范、复制陈旧模式
⑥  生成的代码看似可运行但不能通过 acceptance
```

**本规范的所有规则都直接对应上述错误之一，没有"凑数"的条款。**

---

## Part 1：AI 编码四原则（强制，不可妥协）

> 这部分是 AI 在 S6 实现阶段的**思维模型**。先确立"怎么想"，再谈"怎么写"。
> 灵感来自 Andrej Karpathy 对 LLM 编码陷阱的观察。

### 原则 1：编码前不假设，有困惑就停下

**问题**：AI 倾向于在不确定时悄悄选一种解释然后执行，事后才暴露问题。

**强制规则**：

- 收到 T 任务后，AI **必须先读** `任务清单.json` 中该 T 的完整字段（r_mapping / d_mapping / scope / done_definition / acceptance），不允许凭印象编码
- 如果发现 T 字段中有歧义（如"支持半天"——上午下午的边界怎么定？），**必须停下来询问主Agent**，不允许猜测
- 如果发现现有代码与 T 任务前提冲突（如已有同名方法但语义不一致），**必须停下来报告**，不允许 silently 覆盖
- 同一段逻辑有多种实现路径且无明显优劣时，**必须列出 2-3 种方案的取舍**，由主Agent 决策

**自检问题**：在写第一行代码之前问自己：
```
□ T 的 scope 我看清楚了吗？
□ T 的 acceptance 我能复述吗？
□ 我有没有"我以为是这样"但实际没确认的假设？
□ 如果有歧义，我把它当作显式问题列出来了，还是默默选了一个？
```

### 原则 2：简洁优先，能 50 行不写 200 行

**问题**：AI 容易堆砌抽象层、加预防性的灵活性、引入未来用不到的设计模式。

**强制规则**：

- **不为一次性代码创建抽象**。如果某个接口只有一个实现且未来不会有第二个，就不要建接口。
- **不引入"可配置性"，除非 T 任务明确要求**。任何 `if (config.xxx)` 分支都要回溯到 T 的某个具体字段。
- **不写防御未来的代码**。"以后可能要支持多租户" → 现在不支持，就不留多租户的 hook。
- **不为不可能发生的情况做错误处理**。如方法参数是私有调用且来源可控，不需要 null 检查。
- **删除前的对比**：写完后强制自问"如果让一个资深工程师看，他会觉得我哪里多余？" — 如果有，砍掉。

**判断阈值**：

| 信号 | 处理 |
|------|------|
| 接口 + 1 个实现 | 删接口，直接用实现类 |
| 抽象类 + 1 个子类 | 改为普通类 |
| 工厂方法 + 1 个产品 | 改为直接 `new` |
| 策略模式 + 1 个策略 | 改为直接调用 |
| 配置项无具体使用场景 | 删配置项 |

**例外**：T 任务的 `d_mapping` 明确要求了某个模式（如 D02 写"使用策略模式以支持后续扩展"），则按设计执行。**设计的复杂度由 S3 方案阶段决定，不在 S6 编码阶段引入。**

### 原则 3：精准修改，scope 之外的代码不要碰

**问题**：AI 顺手"改进"了无关代码、清理了不属于本任务的死代码、改了命名风格。

**强制规则**：

- **只修改 `scope` 字段中列出的文件**。修改任何 scope 之外的文件需要在实现记录中**显式说明原因**，并触发 `impl_drift` 校验。
- **不"顺手"做的事**（即使你认为是改进）：
  - 不重命名相邻变量/方法
  - 不重排 import
  - 不改格式化风格
  - 不删除你认为没用的代码（哪怕它真的没用）
  - 不"修复"你注意到的其他 bug（应报告给主Agent）
- **匹配现有风格**：当前项目用 4 空格缩进就用 4 空格，用 Lombok 就用 Lombok，即使你个人偏好不同。
- **孤儿代码处理**：你的改动如果让某个 import / 变量 / 方法变得不再被引用，**必须删除**（这是你制造的清理责任）。但你**不能**删除本来就没用的代码。

**自检问题**：写完后做 diff review：
```
□ 每一行修改是否都能直接追溯到 T 任务的某个字段要求？
□ 我有没有"顺便"动了某个文件？为什么动的？
□ 如果让别人审查这个 diff，会不会有"这行为什么改？"的疑问？
```

### 原则 4：目标驱动执行，循环验证直到达成

**问题**：AI 写完代码后"感觉差不多就提交"，实际没真正达成验收标准。

**强制规则**：

- T 任务的 `acceptance` 字段就是**唯一成功标准**，不是"看起来对就行"
- 编码完成后**必须执行验证循环**：
  ```
  while (acceptance 未达成):
    1. 跑测试 / 调接口 / 查输出
    2. 如果失败，定位原因，修复
    3. 重新跑
  ```
- 失败超过 3 轮**必须报告主Agent**，不允许继续盲改
- 不允许"测试通过但 acceptance 没核对" — 测试是手段，acceptance 是目的
- **写在实现记录里的"已完成"必须基于实际验证**，不是基于"代码看起来正确"

**主Agent 检查时会问什么**：

```
"你说 T03 完成。
 acceptance 写的是 'POST /api/example/items 返回 201，库表新增记录'。
 你跑过这个验证了吗？返回值是 201 吗？库表有新记录吗？
 给我看实现记录里的验证证据。"
```

如果 AI 答不出来，状态回到"未完成"。

---

## Part 2：包结构与建模

### 2.1 顶层结构（Package by Feature）

```
com.{company}.{project}/
├── {feature1}/              ← 一个独立业务功能一个包
│   ├── domain/
│   ├── application/
│   ├── adapter/
│   └── infrastructure/
├── {feature2}/
│   └── ...
└── shared/                  ← 跨功能共享（极简，慎用）
    ├── exception/
    └── util/
```

**核心原则**：
- 一个功能 = 一个顶层包，删除该功能 = 删除该目录
- **具体包名由 AI 在 S2 技术方案阶段命名**，必须满足：业务语义直接、不用 `module1` `common` 这类无意义名、不用泛化的 `manager` `handler`
- **不允许出现 `controller/` `service/` `dao/` 作为顶层包**（这是 Package by Layer 的反模式，禁止）

### 2.2 子包结构（每个 feature 内部）

```
{feature}/
├── domain/                    ← 业务核心
│   ├── model/                 ← 领域对象、值对象、聚合根
│   ├── enums/                 ← 业务枚举（状态、来源、类型、动作、结果）
│   ├── exception/             ← 业务异常
│   └── service/               ← 领域服务（无状态业务规则）
│
├── application/               ← 用例编排
│   ├── usecase/               ← 单个业务动作（命令式：CreateXxxUseCase）
│   ├── query/                 ← 单个业务查询（QueryXxxService）
│   └── dto/                   ← 用例输入输出（与 domain.model 解耦）
│
├── adapter/                   ← 适配器层
│   ├── web/                   ← Controller、REST 接口、Request/Response
│   ├── persistence/           ← Mapper、Repository 实现、Entity
│   ├── messaging/             ← MQ 发送/消费（如有）
│   └── external/              ← 调用外部服务的客户端（如有）
│
└── infrastructure/            ← 技术基础设施
    ├── config/                ← Bean 配置
    └── support/               ← 该 feature 专用的工具类（不放 shared）
```

**约束**：

- **domain 包不依赖任何其他子包**（不依赖 Spring、不依赖 MyBatis、不依赖 web 框架）
- **application 依赖 domain**，通过 port 接口反向依赖 adapter
- **adapter 依赖 application 和 domain**
- **infrastructure 是所有人的支撑**

依赖方向图：
```
adapter ──→ application ──→ domain
              ↓
       infrastructure ←────────┘
```

**禁止**：
- ❌ Controller 直接调用 Mapper（绕过 application）
- ❌ domain.model 引入 `@Entity` `@Table` 等持久化注解（持久化用单独的 PO，放在 adapter/persistence）
- ❌ Service 直接返回数据库实体到 Controller
- ❌ adapter.persistence 中写业务规则判断

### 2.3 命名要求

AI 在 S2 技术方案阶段为每个 feature 命名时遵循：

- **业务语义直接**：`example` 而不是 `exMod`，`examplefeature` 而不是 `lvApp`
- **避免泛化词**：禁止 `common`、`manager`、`handler`、`util`（作为顶层包名）、`base`
- **多词分隔**：Java 包名小写无分隔（`examplefeature`），不用驼峰或下划线
- **同一业务概念跨层保持一致**：domain 叫 `ExampleRecord`，DTO 叫 `ExampleRecordDto`，Entity 叫 `ExampleRecordPO`，**不允许** domain 叫 `ExampleRecord`、DTO 叫 `ExampleRecordForm`、Entity 叫 `TExampleRecordRec`

### 2.4 类的命名约定（Java 通用）

| 角色 | 后缀 | 例子 |
|------|------|------|
| 领域对象 | 无 | `ExampleRecord` |
| 值对象 | 无 | `DateRange` |
| 枚举 | `Enum` | `ExampleStatusEnum` |
| 用例 | `UseCase` | `ApproveRequestUseCase` |
| 查询服务 | `Query` | `ExampleHistoryQuery` |
| 领域服务 | `DomainService` | `ExampleRuleDomainService` |
| Controller | `Controller` | `ExampleRecordController` |
| REST DTO | `Request` / `Response` | `ExampleRecordRequest` / `ExampleRecordResponse` |
| 应用层 DTO | `Dto` | `ExampleRecordDetailDto` |
| 持久化对象 | `PO` | `ExampleRecordPO` |
| Mapper | `Mapper` | `ExampleRecordMapper` |
| Repository 接口（在 application/port） | `Repository` | `ExampleRecordRepository` |
| Repository 实现（在 adapter/persistence） | `RepositoryImpl` | `ExampleRecordRepositoryImpl` |
| 异常 | `Exception` | `ExampleRejectedException` |
| 配置类 | `Configuration` | `ExampleConfiguration` |

---

## Part 3：代码规范

### 3.1 基础风格

- Java 17
- UTF-8 + 4 空格缩进
- 单行 ≤ 120 字符
- 禁止：`@SuppressWarnings` 掩盖告警 / 空 `catch` / 注释掉的旧代码 / `System.out.println` 调试残留

### 3.2 方法设计

| 维度 | 限制 |
|------|------|
| 长度 | 常规 ≤ 40 行，超 60 行强制评估拆分 |
| 参数个数 | ≤ 4 个，超过封装为 Command / Context / Request 对象 |
| 嵌套深度 | ≤ 3 层，超过用卫语句或提炼方法 |
| 布尔参数 | 不连续超过 1 个，多个布尔改为枚举或显式策略 |
| 单一职责 | 一个方法不同时做"查询 + 计算 + 持久化 + 组装返回" |
| 命名 | public 方法体现业务动作（`approveRequest`），private 方法体现局部意图（`validateInput`），禁止 `doHandle` `processAll` 这类空泛命名 |

### 3.3 注释规范

**注释回答"为什么"，不回答"做什么"。**

#### JavaDoc 强制要求（public / protected 方法）

```java
/**
 * 提交示例数据变更并触发审批流程。
 *
 * @param request 示例接口保存信息，emplid 不可为空
 * @param applicantId 申请人 ID，用于权限校验
 * @return 申请ID + 审批流程实例ID
 * @throws ExampleRejectedException 申请年假但剩余额度不足时抛出
 * @throws DuplicateRequestException 同一时间段已有审批中或已通过的申请时抛出
 *
 *   边界约束：
 *   - 年假申请会立即扣减额度（事务内）
 *   - 半天精度按上下午区分
 *   - 跨节假日的天数自动剔除节假日
 */
```

**JavaDoc 必须包含**：业务意图、关键参数语义、边界约束、返回/副作用、异常说明。

#### 必须写块注释的场景

- 历史兼容分支
- 与外部系统对齐的特殊处理
- 规则优先级、冲突覆盖、兜底分支
- 性能优化、并发、缓存策略

#### 禁止的注释

- 复述代码（"// 循环处理列表"）
- 翻译命名（`// 验证参数` 跟在 `validateParams()` 后面）
- 已失效的历史说明

### 3.4 枚举（重点）

**禁止散落字符串常量表达业务状态。** 以下场景**必须**用枚举：

- 业务状态（审批状态、执行状态）
- 业务来源（数据来源、规则来源）
- 类型分类（假期类型、班次类型）
- 动作模式（重算模式、覆盖模式）
- 结果口径（成功/失败/部分成功/跳过）

**枚举设计要求**：

```java
public enum ExampleStatusEnum {

    DRAFT("DRAFT", "草稿"),
    SUBMITTED("SUBMITTED", "审批中"),
    APPROVED("APPROVED", "已通过"),
    REJECTED("REJECTED", "已拒绝"),
    CANCELLED("CANCELLED", "已撤销");

    private final String code;
    private final String desc;

    ExampleStatusEnum(String code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public static ExampleStatusEnum fromCode(String code) {
        for (ExampleStatusEnum value : values()) {
            if (value.code.equals(code)) {
                return value;
            }
        }
        throw new IllegalArgumentException("未知资料状态: " + code);
    }

    /** 状态迁移规则集中在枚举内，禁止散落在 if-else */
    public boolean canTransitTo(ExampleStatusEnum target) {
        return switch (this) {
            case DRAFT -> target == SUBMITTED;
            case SUBMITTED -> target == APPROVED || target == REJECTED || target == CANCELLED;
            case APPROVED, REJECTED, CANCELLED -> false;
        };
    }

    public String getCode() { return code; }
    public String getDesc() { return desc; }
}
```

**禁止**：
- ❌ 依赖 `ordinal()` 表达业务含义
- ❌ 直接把 `name()` 作为对外协议值
- ❌ 在业务流程中 `if (status.equals("APPROVED"))` 这种裸字符串比较

### 3.5 异常与日志

- 业务异常用统一异常体系，禁止 `printStackTrace()` 或吞异常
- 日志必须含关键业务键：`emplid` / `emplRcd` / 业务日期 / 批次号 / 请求 ID
- `INFO` 关键业务流转，`WARN` 可恢复异常或降级路径，`ERROR` 失败与中断
- 捕获异常后做降级/兜底/跳过的，**必须**注释说明"为什么可跳过"

```java
// 反例
try {
    exampleService.apply(req);
} catch (Exception e) {
    // 忽略
}

// 正例
try {
    exampleService.apply(req);
} catch (ExampleRejectedException e) {
    // 额度不足是业务正常路径，记录后返回友好提示，不向上抛
    log.warn("申请失败 - 额度不足, emplid={}, requestedDays={}, remaining={}",
             req.getEmplid(), req.getDays(), e.getRemaining());
    return ApplyResult.quotaExceeded(e.getRemaining());
}
```

### 3.6 分层红线（绝对禁止）

以下情况**任何理由都不允许**：

| 红线 | 原因 |
|------|------|
| Controller 直接调用 Mapper | 跳过 application 层 |
| Mapper 中写业务规则判断 | 持久化层污染业务 |
| Service 返回数据库 PO 给前端 | 内外模型未隔离 |
| domain.model 引入 `@Entity` / Spring 注解 | 领域层被技术细节污染 |
| Util 类承载业务规则 | 业务逻辑被伪装成工具 |
| 单个类同时做"查询 + 规则 + 持久化 + 组装" | 职责混乱 |
| 用 `Map<String, Object>` 作为对外接口的参数/返回 | 类型不安全，无法静态检查 |

---

## Part 4：AI 编码自检清单（强制执行）

### 4.1 编码前自检（写第一行代码前）

```
□ 我读过 T 任务的全部字段了吗？（r_mapping / d_mapping / scope / done_definition / acceptance）
□ 我读过对应的需求说明书（R 字段）和技术方案（D 字段）了吗？
□ T 中有歧义的地方我列出来了吗？是问主Agent，还是确认过可以自决？
□ scope 中要修改的文件我都打开看过现状了吗？
□ 我是否倾向于"先写起来再说"？如果是，停下来想清楚。
```

### 4.2 编码中自检（写每个方法时）

```
□ 这个方法做的事在 T 的范围内吗？
□ 我引入的接口/抽象类/工厂，是 D 字段要求的，还是我自己加的？
□ 我能用更少的代码达成同样效果吗？
□ 我有没有用到 Map<String,Object>、魔法字符串、ordinal()？
□ 我有没有捕获异常后默默吞掉？
```

### 4.3 编码后自检（提交前）

```
□ acceptance 字段我实际验证过了吗？（不是"代码看起来对"）
□ diff 中每一行修改都能追溯到 T 的某个字段要求吗？
□ scope 之外的文件我有没有"顺手"动过？如果动了，原因写进实现记录了吗？
□ 我引入的孤儿代码（不再被引用的 import / 变量 / 方法）都清理了吗？
□ public 方法都有 JavaDoc 吗？JavaDoc 包含业务意图、参数语义、边界、异常吗？
□ 业务状态/类型/来源/动作/结果是否都用了枚举？
□ 测试是否覆盖：主流程 / 边界 / 异常路径 / 历史兼容？
```

### 4.4 主Agent 检查时会做的事

主Agent 收到子Agent 完成报告后会运行：

```bash
python3 docs/.workflow/scripts/validators.py impl_drift <FID> <T_NUMBER>
```

如果有偏离，主Agent 会问以下问题（子Agent 答不出来则状态回退）：

1. **acceptance 实证**：你的实现记录里 acceptance 验证证据在哪？
2. **scope 一致性**：实际改的文件和 tasks.json 里的 scope 一致吗？不一致的原因？
3. **抽象正当性**：你引入的每个接口/抽象类，对应 D 字段的哪个设计要求？
4. **修改必要性**：你改的每一行都对应 T 的什么字段？
5. **简洁审查**：如果让资深工程师看，会不会觉得过度复杂？

---

## Part 5：测试与重构

### 5.1 测试要求

| 类型 | 必须覆盖 |
|------|----------|
| 单元测试 | 主流程 + 边界条件 + 异常路径 |
| 集成测试 | 关键业务链路（如完整审批流） |
| 历史兼容 | 涉及历史规则分支的必须有专项测试 |

**最少测试 = T 的 acceptance 字段中的每一条都至少 1 个测试。**

### 5.2 重构红线

- 重构必须"行为不变"，先补测试再改
- **不允许在 S6 实现阶段做"顺手重构"**——重构属于独立任务，要走完整流程
- 大类（>500 行）、大方法（>60 行）、重复逻辑（>2 次）、散落常量是治理信号，但治理本身必须是一个独立 T 任务

---

## Part 6：与工作流集成

### 6.1 S6 实现阶段的强制顺序

```
1. 主Agent 确认代码 worktree 已创建，文档根仍为主项目 docs/
2. 主Agent 派遣"任务实现"子Agent，传入 T 编号、doc_root、code_root
3. 子Agent 执行 Part 4.1 编码前自检
4. 子Agent 先写当前 T 的失败测试，并实际运行确认 RED
5. 子Agent 编码最小实现（遵循 Part 1 四原则 + Part 2 包结构 + Part 3 代码规范）
6. 子Agent 执行 Part 4.2 编码中自检
7. 子Agent 运行聚焦测试确认 GREEN，再验证 acceptance 直到通过
8. 子Agent 执行 Part 4.3 编码后自检
9. 子Agent 写实现记录到 doc_root 的 04-实现记录/，含 RED/GREEN 和 acceptance 验证证据
10. 子Agent 上报结构化摘要给主Agent
11. 主Agent 运行 impl_drift 校验
12. 主Agent 按 Part 4.4 核查
13. 通过 → step-done；不通过 → 指令修正；3次失败 → approve-correction
```

### 6.2 实现记录模板（写入 `04-实现记录/`）

```markdown
# T{编号} 实现记录 — YYYY-MM-DD

## 任务信息
- T 编号: T03
- 对应需求: R02
- 对应方案: D02
- scope: [src/.../ExampleService.java, src/.../ExampleRecordController.java]
- done_definition: ...
- acceptance: POST /api/example/items 返回 201，库表新增记录

## 实际改动范围
- 修改: ...（与 scope 一致 / 不一致请说明）
- 新增: ...
- 删除: ...（孤儿代码清理）

## 关键设计决策
- 为什么没用接口抽象：只有一个实现，按"简洁优先"不加抽象
- 为什么用了枚举 ExampleStatusEnum：状态分类业务概念，符合 3.4 节要求

## TDD 证据
- RED: `mvn -Dtest=ExampleRecordTest#shouldCreateExampleRecord -DskipTests=false test` → 失败，原因：目标行为尚未实现
- GREEN: `mvn -Dtest=ExampleRecordTest#shouldCreateExampleRecord -DskipTests=false test` → 通过

## 与 D 字段对照
- D02 要求：状态机模式，使用枚举集中迁移规则 ✓
- D04 要求：事务保证额度扣减原子性 ✓

## acceptance 验证证据
- 测试运行: `mvn test -Dtest=ExampleRecordTest` → 12/12 通过
- 接口验证: curl POST /api/example/items 返回 201
- 库表验证: SELECT * FROM example_record WHERE id=xxx → 有记录

## 自检清单
- [x] 编码前自检通过
- [x] TDD RED 已验证且失败原因正确
- [x] TDD GREEN 已验证通过
- [x] 编码中自检通过
- [x] 编码后自检通过
- [x] scope 内所有文件都修改了
- [x] scope 外文件未修改（或说明原因）
- [x] acceptance 全部验证通过

## 修正记录（如有）
- 第1次主Agent反馈: ...
- 修正内容: ...

## 关键结论（写入 step-done）
- T03 完成
- 新增枚举 ExampleStatusEnum
- 引入 ExampleRejectedException
- acceptance 全部验证通过
```

---

## Part 7：演进历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 - v2.3 | 2025-12 ~ 2026-03 | 早期从 通用 Java 项目实践提炼 |
| v3.0 | 2026-05-15 | 重构：融合 AI 编码四原则（反 LLM 陷阱）+ DDD Package by Feature 包结构 + 配合工作流 v2.0 的强制自检流程 |

---

## 附录 A：四原则速记卡（贴在屏幕上）

```
1. 不假设 — 有困惑就停，列权衡让主Agent决策
2. 简洁优先 — 50 行能搞定就别写 200 行
3. 精准修改 — scope 之外不要碰
4. 目标驱动 — acceptance 是唯一成功标准
```

## 附录 B：编码时禁止的口头禅

AI 在编码时如果出现以下"内心台词"，立即停下：

- "为了未来扩展，我先抽象一下" → 简洁原则违反
- "顺便把这个地方也改了" → 精准修改原则违反
- "应该差不多了，提交吧" → 目标驱动原则违反
- "这里应该是这个意思吧" → 不假设原则违反

---

*Java 开发规范 v3.0 · AI 协作版 · 2026-05-15*
