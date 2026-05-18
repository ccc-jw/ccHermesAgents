# Hermes Agent 软件工程团队系统设计方案 v2.0

## 1. 结论摘要

Hermes Agent 软件工程团队应设计为一个 **状态机驱动、产物可追溯、执行可隔离、人工门禁可审计** 的长周期软件工程编排系统。

它不是多 Agent 自由聊天平台，也不是 Claude Code CLI 的简单包装器，而是：

```text
Hermes 管状态、流程、记忆、任务、产物、评审、异常升级；
Claude Code CLI / LLM / Script Runner 管代码、文档、测试、安全扫描等具体执行；
飞书只暴露 PM Agent 给用户；
WorkflowEngine 是唯一可以推进项目阶段的模块；
Agent 负责产出和建议，不能直接修改项目状态；
Runner 负责安全执行，不能参与业务决策。
```

核心判断：

```text
长周期项目的关键不是让多个 Agent 自由聊天，
而是让项目状态、任务输入、产物、评审和异常升级可恢复、可审计、可重试。
```

---

## 2. 总体架构

### 2.1 五层架构

```text
1. 交互层
   Feishu Bot / Feishu Card / Webhook / 用户确认

2. 编排层
   PM Interaction Service
   WorkflowEngine
   StateTransitionGuard
   PhaseCommunicationGuard
   EscalationManager
   PM Patrol Scheduler

3. 协作层
   AgentExecutor
   Agent Registry
   Role Prompt
   Review Service
   Issue Service
   Agent Message Service
   Confirmation Service

4. 执行层
   Task Queue
   Runner Worker
   Claude Code CLI Runner
   Direct LLM Runner
   Script Runner
   WorkspaceManager
   ArtifactCollector
   LogCollector

5. 状态与产物层
   SQLite / 后续 Postgres
   project_events
   tasks / task_runs
   artifacts
   issues
   reviews
   confirmations
   local file storage
   git workspaces
```

### 2.2 总体链路

```text
Feishu User
  -> Feishu Bot / Interactive Card
  -> PM Interaction Service
  -> WorkflowEngine / StateTransitionGuard
  -> TaskService / ReviewService / IssueService / ConfirmationService
  -> AgentExecutor
  -> Task Queue
  -> Runner Worker
  -> Claude Code CLI / Direct LLM / Script Runner
  -> Artifact Store / SQLite / Git Workspace
```

### 2.3 核心边界

```text
用户只和 PM 交互；
PM 负责沟通、汇总、巡检、升级，不直接切状态；
Agent 负责产出、建议、评审意见、问题单，不直接推进阶段；
Runner 负责执行，不理解业务阶段和角色决策；
WorkflowEngine 负责推进阶段；
StateTransitionGuard 负责防止非法跳转；
PhaseCommunicationGuard 负责按阶段控制 Agent 间通信；
Confirmation 负责人工确认；
Artifact 负责沉淀文档、代码 diff、报告、测试清单；
project_events 负责审计；
所有阶段推进必须有 evidence。
```

---

## 3. 角色体系

### 3.1 核心流程角色

| 角色 | 职责 | 主要产物 |
|---|---|---|
| PM | 用户交互、项目创建、进度汇总、评审组织、飞书通知、主动巡检、异常升级 | 进度报告、风险汇总、升级卡片 |
| PDM | 需求澄清、PRD 生成、PRD 修订、需求歧义裁决、验收报告 | PRD、验收报告 |
| DEV | 编码实现、自测、冒烟、Bug 修复、代码变更总结；MVP 阶段可兼任 ARCH 职责 | diff、源码、自测报告、详细设计 |
| TEST | 测试用例、测试清单、功能验证、缺陷记录、复测 | 测试用例、测试清单、测试报告、Issue |

### 3.2 质量增强角色

| 角色 | 职责 | 主要产物 |
|---|---|---|
| ARCH | 技术方案、接口定义、数据库设计、架构风险识别、设计评审；MVP 阶段可由 DEV 兼任 | 详细设计、接口设计、数据库设计 |
| SEC | 安全审查、SAST、依赖扫描、敏感信息检查、权限/鉴权审查 | 安全报告、安全 Issue |

### 3.3 按需派生角色

| 角色 | 职责 | 主要产物 |
|---|---|---|
| RES | 技术调研、竞品分析、API/SDK 可行性研究、多方案对比 | 调研报告 |
| Research Judge | 汇总调研结果、识别冲突、要求补证、给出推荐方案 | 调研裁决报告 |

落地优先级：

```text
第一优先级：PM / PDM / DEV / TEST
第二优先级：ARCH / SEC
第三优先级：RES / Research Judge
```

### 3.4 Agent 模型独立配置

每个 Agent 独立配置不同厂商模型，统一采用 OpenAI 兼容格式：

```yaml
agent:
  name: DEV
  role: developer
  executor_type: claude_code_cli
  model:
    provider: openai_compatible
    base_url: "https://api.xxx.com/v1"
    api_key_env: DEV_MODEL_API_KEY
    model: "claude-sonnet-4-6"
    max_tokens: 4096
    temperature: 0.0
```

`model_config_json` 存入数据库的结构（OpenAI 兼容格式）：

```json
{
  "provider": "openai_compatible",
  "base_url": "https://api.xxx.com/v1",
  "api_key_env": "DEV_MODEL_API_KEY",
  "model": "claude-sonnet-4-6",
  "max_tokens": 4096,
  "temperature": 0.0
}
```

字段说明：
- `provider`：模型提供商标识（openai_compatible / anthropic / custom）
- `base_url`：OpenAI 兼容格式的 API 基础 URL
- `api_key_env`：环境变量名，**不存储真实 API Key**
- `model`：模型名称（如 claude-sonnet-4-6、gpt-4o、qwen-plus 等）
- `max_tokens`：可选，单次请求最大 token 数
- `temperature`：可选，采样温度，默认 0.0 表示确定性输出

配置原则：

```text
PDM / DEV / ARCH 可优先使用代码和文档能力强的模型；
TEST / RES 可按成本和多样性选择模型；
SEC 可结合 LLM 与确定性扫描工具；
PM 可使用轻量模型负责汇总、通知和状态解释；
Hermes 自身模型配置与 Agent 执行模型分开管理。
运行时从环境变量读取 api_key_env 对应的真实 Key，不写入数据库或日志。
```

---

## 4. Agent 权限边界与协作规则

### 4.1 Agent 允许做

```text
生成 artifact；
提交 review comment；
创建 issue；
提出 question；
请求 clarification；
输出 task result；
建议下一步动作；
建议升级给用户；
建议暂停项目。
```

### 4.2 Agent 禁止做

```text
直接切换 project phase；
直接关闭 review；
直接标记 issue verified；
直接标记 project done；
直接绕过测试；
直接绕过用户确认；
直接 push / merge / deploy；
直接执行数据库迁移；
直接修改 project_events；
直接写数据库状态。
```

### 4.3 受控间接协作

```text
Agent 之间不直接自由聊天；
所有跨角色沟通通过 AgentMessage / Issue / ReviewComment / Artifact；
PM 可以汇总和路由；
PDM 负责需求歧义裁决；
ARCH 负责技术方案裁决；
WorkflowEngine 负责状态推进。
```

### 4.4 PhaseCommunicationGuard

PhaseCommunicationGuard 按阶段控制 Agent 间通信权限，满足 DEV/TEST 硬隔离等规则。

```text
规则：
  - 每个项目阶段可配置禁止通信的 Agent 对；
  - DESIGN_AND_TESTCASE_PREPARATION 阶段 DEV ↔ TEST 消息直接拒绝；
  - DESIGN_REVIEW 阶段开始后解禁；
  - 被拒绝的消息记录到 agent_messages，status = rejected_by_guard；
  - PM 巡检可查看被拦截的消息。

实现方式：
  - agent_messages 发送前经过 PhaseCommunicationGuard.check(from_agent, to_agent, project_phase)；
  - 返回 allowed / rejected + reason；
  - Guard 规则配置于 workflows/phase_communication_rules.yaml。
```

DEV 和 TEST 隔离规则：

```text
在 DESIGN_AND_TESTCASE_PREPARATION 阶段：
DEV / ARCH 负责详细设计；
TEST 独立生成测试用例和测试清单；
DEV 和 TEST 不直接点对点沟通；
需求疑问提交给 PDM；
技术可测性疑问通过 ReviewComment 在设计评审阶段处理；
所有沟通必须留下结构化记录。
```

---

## 5. Workflow 设计

### 5.1 统一阶段枚举

项目阶段（current_phase）与项目状态（status）分离管理：
- `current_phase`：表达项目当前处于哪个工作阶段（见下方枚举）
- `status`：active / paused / failed / cancelled / done

项目暂停时，`status='paused'` 但 `current_phase` 保留暂停前的真实阶段，
恢复时可准确恢复到暂停时的阶段继续执行。

```text
INIT
REQUIREMENT_DISCOVERY
REQUIREMENT_DRAFTING
REQUIREMENT_REVIEW
REQUIREMENT_REVISION
REQUIREMENT_APPROVED
DESIGN_AND_TESTCASE_PREPARATION
DESIGN_REVIEW
DESIGN_REVISION
DESIGN_APPROVED
DEVELOPMENT
DEV_SELF_TEST
TEST_AND_SECURITY_VALIDATION
FIXING
USER_ACCEPTANCE
ACCEPTANCE_FIXING
```

SCOPE_CHANGE 不作为 current_phase，也不作为 project.status。
它是用户或系统触发的变更命令，由 Confirmation / Escalation 承载。
变更被确认后，WorkflowEngine 根据影响范围创建新的 PRD 修订任务，通常回到 REQUIREMENT_DISCOVERY 或 REQUIREMENT_DRAFTING。

所有 API、DDL、飞书卡片、测试用例、WorkflowEngine 都必须引用这一份阶段枚举。

### 5.2 完整生命周期

```text
INIT
  -> REQUIREMENT_DISCOVERY
  -> REQUIREMENT_DRAFTING
  -> REQUIREMENT_REVIEW
  -> REQUIREMENT_REVISION
  -> REQUIREMENT_APPROVED
  -> DESIGN_AND_TESTCASE_PREPARATION
  -> DESIGN_REVIEW
  -> DESIGN_REVISION
  -> DESIGN_APPROVED
  -> DEVELOPMENT
  -> DEV_SELF_TEST
  -> TEST_AND_SECURITY_VALIDATION
  -> FIXING
  -> USER_ACCEPTANCE
  -> ACCEPTANCE_FIXING
  -> DONE
```

典型直线路径：

```text
INIT
  -> REQUIREMENT_DISCOVERY
  -> REQUIREMENT_DRAFTING
  -> REQUIREMENT_REVIEW
  -> REQUIREMENT_APPROVED
  -> DESIGN_AND_TESTCASE_PREPARATION
  -> DESIGN_REVIEW
  -> DESIGN_APPROVED
  -> DEVELOPMENT
  -> DEV_SELF_TEST
  -> TEST_AND_SECURITY_VALIDATION
  -> USER_ACCEPTANCE
  -> DONE
```

问题回流：

```text
需求评审失败：
REQUIREMENT_REVIEW -> REQUIREMENT_REVISION -> REQUIREMENT_REVIEW

设计评审失败：
DESIGN_REVIEW -> DESIGN_REVISION -> DESIGN_REVIEW

测试 / 安全失败：
TEST_AND_SECURITY_VALIDATION -> FIXING -> DEV_SELF_TEST -> TEST_AND_SECURITY_VALIDATION

用户验收失败（标准路径 - 代码逻辑变更）：
USER_ACCEPTANCE -> ACCEPTANCE_FIXING -> DEV_SELF_TEST -> TEST_AND_SECURITY_VALIDATION -> USER_ACCEPTANCE

用户验收失败（轻量路径 - 文案/样式/文档类变更）：
USER_ACCEPTANCE -> ACCEPTANCE_FIXING -> USER_ACCEPTANCE
```

异常状态：

```text
任意阶段 -> status=PAUSED（current_phase 保持不变）
任意阶段 -> status=FAILED（current_phase 保持不变）
任意阶段 -> status=CANCELLED（current_phase 保持不变）
任意阶段 -> scope_change command / escalation decision
  -> 用户确认变更范围
  -> REQUIREMENT_DISCOVERY 或 REQUIREMENT_DRAFTING
  -> 生成新版 PRD artifact
```

需求变更处理规则：

```text
  - scope change 不直接修改 current_phase 或 status；
  - Feishu / PM 只提交 change_requirement 命令或 escalation decision；
  - WorkflowEngine 创建 scope_change_approval confirmation；
  - 用户确认后，按影响范围回到 REQUIREMENT_DISCOVERY 或 REQUIREMENT_DRAFTING；
  - 原 PRD / 设计 / 测试用例保留为历史 artifact，新版本通过 parent_artifact_id 关联；
  - 未确认前，项目可保持原阶段 paused，避免半变更状态。
```

### 5.3 DESIGN_REVIEW 双评审机制

`DESIGN_REVIEW` 阶段内，WorkflowEngine 同时创建两个独立 Review：

```text
Review A：详细设计评审
  - 评审对象：DEV / ARCH 产出的详细设计文档
  - 参与 Agent：PM、PDM、TEST、SEC、ARCH（如已独立）
  - 独立投票通过/打回

Review B：测试用例与测试清单评审
  - 评审对象：TEST 产出的测试用例文档 + 测试清单
  - 参与 Agent：PM、PDM、DEV、SEC、ARCH（如已独立）
  - 独立投票通过/打回
```

两个 Review 各自独立：

```text
Review A 不通过 -> DEV / ARCH 修订详细设计 -> 重新提交 Review A；
Review B 不通过 -> TEST 修订测试用例 -> 重新提交 Review B；
两个 Review 都通过 -> WorkflowEngine 推进到 DESIGN_APPROVED。
```

### 5.4 回流和超时上限

```text
需求评审最多 2 轮回流；
设计评审最多 3 轮回流；
测试修复最多 3 轮回流；
验收修复最多 3 轮回流；
每个 Review 超时按项目规模分级（可配置）：
  - S 级：15 分钟
  - M 级：30 分钟
  - L/XL 级：60 分钟
超过回流次数限制或 Review 超时后进入 PAUSED，并创建 escalation。
```

Review 超时后：

```text
PM 查询尚未提交评审意见的 Agent；
PM 推送飞书通知用户，列出已提交意见和超时未响应 Agent；
用户可选择继续等待、跳过未响应 Agent、回退阶段或暂停项目。
```

PM 巡检消息聚合策略：

```text
PM 每 15 分钟巡检一次（可配置），但不每次推送消息给用户。
消息聚合规则：
  - 30 分钟内相同项目的相同状态问题，不重复推送；
  - 只有以下情况才主动推送飞书消息：
    a. 项目状态发生变化（新任务开始、任务完成、任务失败）
    b. Review 首次超时
    c. 连续 2 次巡检发现同一任务超时（升级预警）
    d. 创建 Escalation 需要用户决策
    e. 等待用户确认且确认即将超时
  - 用户可通过飞书 /status 命令随时查询项目状态，不受聚合规则限制
```

### 5.5 阶段推进原则

```text
只有 WorkflowEngine 可以推进阶段；
每次推进必须有 evidence；
evidence 可以是 artifact、review、issue、task_run、confirmation 或 escalation decision；
每次推进必须写 project_events；
Agent 输出只能作为 evidence，不能直接作为状态变更；
MVP 采用“状态快照 + 审计事件”；
projects.current_phase / projects.status 是当前状态快照；
project_events 是审计日志，后续可演进为完整 Event Sourcing。
```

幂等规则：

```text
  - 所有会导致状态变化的命令必须带 idempotency key；
  - project_events.event_key 作为状态变更幂等键；
  - Feishu event_id / open_message_id、confirmation decision、runner complete/fail、review complete 都必须映射到稳定 event_key；
  - 如果 event_key 已存在，服务返回已有处理结果，不重复推进状态。
```

---

## 6. 评审机制

评审不采用自由聊天会议，而采用结构化评审。

### 6.1 Review

```text
review_type
phase
input_artifacts
participants
required_participants
round
status
deadline
conclusion
```

### 6.2 ReviewComment

```text
reviewer_agent
comment_type: pass / question / issue / suggestion
status: open / resolved / accepted / rejected
severity: minor / major / blocker
comment
required_change
related_artifact
resolved_by
resolved_at
resolution_note
```

### 6.3 评审通过条件

```text
所有 required participant 已提交意见；
没有 blocker / major 级 fail；
所有 question 已关闭或转成 issue；
评审 owner 提交 conclusion；
WorkflowEngine 校验 evidence 后推进阶段。
```

### 6.4 评审失败条件

```text
存在 blocker；
存在 major 且 required_change 未解决；
核心 artifact 缺失；
参与角色未完成评审且超过 deadline；
意见冲突无法收敛。
```

### 6.5 阶段评审与结果复核边界

`Review` 和 `Result Review` 是两类不同门禁：

```text
Review：阶段级评审，用于 PRD、详细设计、测试用例、安全方案等阶段产物；
Result Review：任务级复核，用于判断一次 TaskRun 输出是否满足 Task Contract 和业务语义。
```

边界原则：

```text
Review 关注”阶段产物是否可进入下一阶段”；
Result Review 关注”Runner 的一次执行结果是否可以被任务采纳”；
TaskRun completed 只能触发 Result Review，不能直接完成 Task；
Review passed 才能作为 WorkflowEngine 推进阶段的 evidence；
Result Review passed 只能证明单个任务结果有效，是否推进阶段仍由 WorkflowEngine 综合判断。
```

### 6.6 验收问题处理规则

PDM 验收时发现的问题统一走 `issues` 表，`source=acceptance`：

```text
验收问题与测试/安全发现的问题共享 issues 表，但通过 source 字段区分：
  - source=test：测试工程师发现的功能缺陷
  - source=security：安全工程师发现的安全漏洞
  - source=acceptance：PDM 验收时发现的需求符合度问题

验收问题在飞书卡片上标注为”验收问题”，与”测试缺陷”分开展示，
确保用户能直观区分两类问题的性质和优先级。
```

验收回流路径选择规则：

```text
WorkflowEngine 根据验收问题的影响范围判断走哪条回流路径：

标准路径（代码逻辑变更）：
  - 存在 severity=blocker/major 的验收问题
  - 或涉及接口变更、数据库变更、鉴权/权限变更
  - 路径：ACCEPTANCE_FIXING -> DEV_SELF_TEST -> TEST_AND_SECURITY_VALIDATION -> USER_ACCEPTANCE

轻量路径（文案/样式/文档类变更）：
  - 所有验收问题均为 severity=minor
  - 且不涉及代码逻辑变更
  - 路径：ACCEPTANCE_FIXING -> USER_ACCEPTANCE
```

验收报告结构：

```text
acceptance_report artifact 包含：
  - 验收概述：验收时间、验收人、验收范围
  - 验收结果：passed / failed
  - 验收问题统计：总数 / blocker / major / minor
  - 验收问题清单列表（引用 issues 表，source=acceptance）
  - 验收结论：是否满足 PRD 要求
  - 后续建议（如有）
```

验收通过判定标准：

```text
  - source=acceptance 的 open issue 数量为 0；
  - 或仅存在 minor 级 issue 且用户通过飞书确认接受；
  - PDM 提交 acceptance_report 并标记 is_final=true。
```

---

## 7. Agent 与 Runner 协作模型

### 7.1 基本原则

```text
Agent 不直接调用 Claude Code CLI；
Runner 不理解 Agent 角色和业务决策；
二者通过 TaskService / AgentExecutor / TaskRun / Artifact 间接协作。
```

推荐链路：

```text
Agent 提出任务意图
  -> AgentExecutor 生成 Task Contract
  -> AgentExecutor 生成 task_prompt.md / task_context.json
  -> 创建 TaskRun
  -> Runner 执行
  -> Runner 做机械约束校验
  -> Runner 输出 Artifact / Result
  -> Result Reviewer 做语义复核
  -> WorkflowEngine 根据 evidence 推进
```

### 7.2 Task Contract

Agent 意图必须被编译成可执行契约，而不是只传一句自然语言指令。

Task Contract 包含：

```text
task_goal
role
phase
input_artifacts
must_read_artifacts
allowed_paths
forbidden_paths
expected_artifacts
acceptance_criteria
quality_gates
risk_controls
review_required
max_changed_files
timeout_seconds
```

示例：

```json
{
  "task_goal": "实现账号密码登录接口",
  "must_read_artifacts": ["prd_final", "design_final", "api_design"],
  "allowed_paths": ["src/auth/**", "tests/auth/**"],
  "forbidden_paths": [".env", "deploy/**", "ci/**"],
  "expected_artifacts": ["diff_patch", "self_test_report"],
  "acceptance_criteria": [
    "支持账号密码登录",
    "密码错误返回统一错误提示",
    "登录成功返回 token",
    "新增或更新测试用例",
    "相关测试通过"
  ],
  "risk_controls": [
    "不要 push",
    "不要执行数据库迁移",
    "不要修改 CI/CD"
  ]
}
```

### 7.3 Runner 机械校验

Runner 执行结束后必须检查：

```text
是否修改了 forbidden_paths；
是否超出 allowed_paths；
是否产出了 expected_artifacts；
是否 exit_code 正常；
是否输出过大；
是否触发安全策略；
是否缺少 output_manifest；
是否缺少 diff 或报告。
```

违反契约时，Runner 标记：

```text
CONTRACT_VIOLATION
SECURITY_POLICY_BLOCKED
OUTPUT_MISSING
```

### 7.4 Result Review

Runner 完成不等于任务通过。

```text
task_run.status = completed
不代表 task.status = completed
```

需要 Result Reviewer 对照 Task Contract、原始需求、diff、报告做语义复核：

```text
是否满足 acceptance_criteria；
是否偏离 PRD / design；
是否漏测；
是否需要返工；
是否需要创建 issue。
```

WorkflowEngine 只认通过验证的 evidence：

```text
TaskRun completed；
没有 contract violation；
required artifacts 存在；
Result Review passed；
必要测试 passed；
必要 issue 已关闭；
必要人工确认已完成。
```

### 7.5 Task 状态机

Task 表达业务任务，TaskRun 表达一次执行。Task 状态只能由 TaskService、Runner Worker 回调、Result Review 和 WorkflowEngine 按规则推进。

Task 状态转移：

```text
pending -> assigned：TaskService 分派 owner_agent / assigned_to。
assigned -> queued：TaskService 创建 task_contract 和 task_run，并向队列写入 task_run_id。
queued -> running：Runner Worker 成功领取 task_run 并开始准备 workspace。
running -> result_pending_review：task_run completed，且 Runner 机械校验未发现 contract violation。
running -> failed：task_run failed / timeout / cancelled，且达到重试上限或错误不可自动重试。
result_pending_review -> completed：Result Review passed。
result_pending_review -> needs_revision：Result Review failed 或 needs_revision。
needs_revision -> assigned：AgentExecutor 根据 required_changes 生成修订任务或重试任务。
任意非终态 -> blocked：等待依赖、人工确认或外部条件。
任意非终态 -> cancelled：项目取消或任务取消。
```

约束：

```text
  - task_run.status 不能直接决定 task.status=completed；
  - task.completed 必须依赖 Result Review passed；
  - WorkflowEngine 只使用 completed task / passed review / closed issue / approved confirmation 作为推进 evidence。
```

---

## 8. Runner 设计

### 8.1 Runner 定位

```text
AgentExecutor 负责决定“谁来做任务”；
Runner 负责决定“如何安全执行任务”；
Claude Code CLI 只是 Runner 的一种执行后端。
```

Runner 标准输入：

```text
task_prompt.md
task_context.json
input_artifacts_manifest.json
runner_config_snapshot.json
model_config_snapshot.json
workspace_config.json
task_contract.json
```

Runner 标准输出：

```text
stdout / stderr
execution log
summary
diff.patch
artifact manifest
result.json
error report
contract_check_result.json
```

### 8.2 Runner 生命周期

```text
CREATED
  -> PREPARING_WORKSPACE
  -> BUILDING_CONTEXT
  -> RUNNING
  -> COLLECTING_RESULTS
  -> PARSING_OUTPUT
  -> COMPLETED / FAILED / TIMEOUT / CANCELLED
```

执行后端由 `runner_type` 区分：

```text
claude_code_cli      # MVP 主要使用，代码生成和文档生成
script_runner        # MVP 使用，Excel 生成/简单脚本测试/SAST 扫描
direct_llm           # MVP 后使用
sast_runner          # MVP 后使用
test_runner          # MVP 后使用
multi_agent_runner   # MVP 后使用
```

MVP 阶段只实现 `claude_code_cli` 和 `script_runner` 两种 Runner，
覆盖编码、文档生成、测试清单 Excel 生成和基本脚本验证场景。
其他 Runner 类型在后续阶段按需添加，减少初期复杂度。

### 8.2.1 Task Queue / Runner Worker 模型

MVP 推荐使用 Dramatiq + Redis 作为任务队列，SQLite 仍然是业务状态源。

入队时机：

```text
  - TaskService 创建 task_run 后，将 task.status 置为 queued；
  - 队列消息只包含 task_run_id，不携带完整上下文；
  - Runner Worker 领取后从数据库读取 task_run、task_contract、runner_policy 和输入快照路径。
```

队列消息：

```json
{
  "task_run_id": "run_001",
  "idempotency_key": "task_run:run_001:start"
}
```

Worker 并发：

```text
  - 同一项目同一时间最多一个 DEV 写工作区任务运行；
  - TEST / SEC 只读任务可以并行；
  - PDM / PM 文档任务可并行，但同一 artifact 只能有一个最终版标记任务；
  - Worker 池按 runner_type 设置并发上限。
```

状态更新责任：

```text
  - Runner Worker 只更新 task_run.status 和运行输出；
  - TaskService 根据 Worker 开始执行事件把 task.status 从 queued 推到 running；
  - Result Review 决定 task.status 是 completed 还是 needs_revision；
  - WorkflowEngine 根据 evidence 推进 project.current_phase。
```

重试策略：

```text
  - 队列框架只负责投递失败重试；
  - 业务重试次数以 tasks.retry_count / max_retries 为准；
  - Runner 超时、CLI 非零退出、输出缺失等错误写入 task_runs.error_code；
  - 达到 max_retries 后创建 escalation，不继续自动重试。
```

### 8.3 Workspace 策略

| 任务类型 | 策略 | 写权限 |
|---|---|---|
| PDM / PM 文档任务 | copy_workspace 或 artifact_workspace | docs / artifacts / reports |
| DEV 代码任务 | git_worktree | repo workspace，禁止自动 push / merge |
| TEST 测试任务 | clean_git_worktree | 代码默认只读，reports / artifacts 可写 |
| SEC 安全任务 | readonly_worktree 或 container readonly mount | security-reports / artifacts |
| RES 调研任务 | no_repo_workspace 或 readonly_workspace | research reports |

原则：

```text
每个 task_run 一个独立 workspace；
同一项目同一时间最多一个 DEV 写工作区；
TEST / SEC 可以并行读；
产物目录必须白名单；
任务结束后收集产物，再决定是否清理 workspace。
```

### 8.3.1 测试清单 Excel 生成机制

TEST Agent 产出的测试清单需要同时生成两种格式：

```text
1. Markdown 格式（artifact_type=testcase_doc）：
   用于评审阶段阅读和结构化解析，存储在 artifacts/ 目录
   TEST Agent 通过 claude_code_cli 生成 Markdown 文档

2. Excel 格式（artifact_type=test_checklist）：
   用于逐条执行验证和进度跟踪，存储在 artifacts/ 目录
   通过 script_runner 调用 Python 脚本，从 testcase_doc 解析并转换为 Excel

转换流程：
  TEST Agent 生成 testcase_doc Markdown
    -> WorkflowEngine 解析 Markdown 中的测试用例结构（标题、步骤、预期结果）
    -> 将解析结果写入 test_checklist_items 表
    -> script_runner 调用 openpyxl 库生成 Excel 文件
    -> 登记 artifact (type=test_checklist)
    -> PM 巡检时从 test_checklist_items 表查询进度（共 N 条，通过 M 条，失败 K 条）
    -> PDM 验收时可直接查看 Excel 或从系统读取

Excel 文件列结构：
  序号 | 测试用例标题 | 测试步骤 | 预期结果 | 执行状态 | 实际结果 | 失败描述 | 关联 Issue
```

MVP 实现策略：
- `script_runner` 使用预置的 Python 脚本 `generate_test_checklist.py`，读取 testcase_doc Markdown 解析后生成 Excel
- 依赖 `openpyxl` 库，在 Docker 镜像中预装
- Markdown 格式采用固定模板，确保解析可靠性

### 8.4 输入快照

每次 TaskRun 启动前必须固化：

```text
task_id
project_id
phase
owner_agent
task_contract.json
task_prompt.md
task_context.json
input_artifacts_manifest.json
repo_url
repo_commit_sha
base_branch
workspace_strategy
agent_config_snapshot
model_config_snapshot
runner_config_snapshot
created_at
```

---

## 9. Runner 安全、可靠性与交付门禁

### 9.1 默认禁止动作

```text
禁止自动 push；
禁止自动 merge；
禁止自动创建 PR；
禁止自动发布；
禁止自动部署；
禁止自动执行数据库迁移；
禁止自动删除远端分支；
禁止自动修改生产配置；
禁止自动发送外部消息；
禁止读取宿主敏感目录；
禁止把 API Key 写入 prompt、artifact、log。
```

### 9.2 需要人工确认的动作

```text
创建 PR；
推送分支；
执行 migration；
新增外部依赖；
修改 CI/CD；
修改鉴权 / 权限 / 支付 / 安全策略；
发布部署；
删除文件或大规模重构。
```

确认必须通过飞书卡片或明确用户消息完成，并写入 `confirmations` 与 `project_events`。

### 9.3 Runner Policy 强制机制

Runner 启动前必须加载 `runner_policies` 中启用的策略，并把策略快照写入 `task_runs.runner_policy_id` 与 `runner_config_snapshot_json`。

强制检查点：

```text
启动前：校验 runner_type、workspace_strategy、allowed_paths、forbidden_paths、env allowlist；
执行中：限制超时、输出大小、网络访问、子进程数量和危险命令；
收集前：校验 artifact 路径白名单、大小上限、敏感字符串；
完成前：校验 diff 是否越权、expected_artifacts 是否齐全、contract_check_result 是否通过。
```

策略维度：

```text
command_policy：禁止 push / merge / deploy / migration 等命令；
network_policy：默认禁止外连，按 runner_type 白名单放行；
env_policy：只注入任务需要的环境变量，禁止透传宿主完整环境；
file_policy：只允许访问 workspace 与 artifact 目录；
artifact_policy：限制 artifact 类型、路径、大小和敏感内容。
```

违反策略时，Runner 必须停止执行或拒绝收集产物，并写入 `SECURITY_POLICY_BLOCKED` 或 `CONTRACT_VIOLATION`。

### 9.4 可靠性机制

Runner 必须支持：

```text
timeout；
取消任务时杀掉子进程；
最大 stdout / stderr 大小；
最大 artifact 大小；
重试上限；
失败 error_type 分类；
失败 error_message；
exit_code；
workspace_path；
logs_path；
diff_path；
input_snapshot_path；
output_manifest_path。
```

错误类型：

```text
PREPARE_WORKSPACE_FAILED
BUILD_CONTEXT_FAILED
RUNNER_TIMEOUT
RUNNER_CANCELLED
CLI_EXIT_NONZERO
OUTPUT_TOO_LARGE
ARTIFACT_COLLECTION_FAILED
RESULT_PARSE_FAILED
SECURITY_POLICY_BLOCKED
CONTRACT_VIOLATION
OUTPUT_MISSING
UNKNOWN_ERROR
```

### 9.5 日志和密钥保护

```text
API Key 只从环境变量读取；
prompt 和 task_context 里只记录 api_key_env，不记录真实 key；
stdout / stderr 入库或落盘前做脱敏；
artifact 收集前扫描敏感字符串；
日志中隐藏 workspace 外部路径；
错误消息避免带完整环境变量；
脱敏对象至少包括 API Key、Token、Cookie、Authorization Header、SSH Key、私钥、数据库连接串、Webhook Secret、Feishu App Secret。
```

### 9.6 取消策略

```text
用户暂停 / 取消项目时，WorkflowEngine 标记相关 TaskRun cancel_requested_at；
Runner Worker 收到取消请求后停止接受新输出，向子进程发送终止信号；
超时未退出时强制杀掉子进程组；
取消后只收集安全允许的日志和已有产物摘要；
最终写入 cancelled_at、exit_code、error_code = RUNNER_CANCELLED。
```

### 9.7 内部 API 与飞书安全

```text
/internal/runner/* 只允许 Runner Worker 调用；
内部 Runner API 必须使用服务端 token、mTLS 或内网网关鉴权；
Runner heartbeat / complete / fail 必须校验 task_run 当前状态，防止重复完成或越权更新；
Feishu event / interactive 必须校验签名、timestamp 和 app_id；
Feishu event_id / open_message_id 必须做幂等去重；
超过时间窗口的飞书回调必须拒绝，防止重放。
```

---

## 10. 需求规模分级与流程裁剪

### 10.1 S 级

适用：文案修改、配置调整、简单 Bug、局部低风险代码改动。

```text
需求确认
  -> DEVELOPMENT
  -> DEV_SELF_TEST
  -> TEST_AND_SECURITY_VALIDATION（轻量模式）
  -> USER_ACCEPTANCE
  -> DONE
```

### 10.2 M 级

适用：常规功能、业务规则明确、单仓库或少量模块改动。

```text
REQUIREMENT_DRAFTING
  -> REQUIREMENT_REVIEW
  -> REQUIREMENT_APPROVED
  -> DEVELOPMENT
  -> DEV_SELF_TEST
  -> TEST_AND_SECURITY_VALIDATION
  -> USER_ACCEPTANCE
  -> DONE
```

### 10.3 L 级

适用：涉及数据库 schema、鉴权、权限、支付、安全、跨模块、外部依赖、部署、技术不确定性。

```text
REQUIREMENT_DISCOVERY
  -> REQUIREMENT_DRAFTING
  -> REQUIREMENT_REVIEW
  -> REQUIREMENT_APPROVED
  -> DESIGN_AND_TESTCASE_PREPARATION
  -> DESIGN_REVIEW
  -> DESIGN_APPROVED
  -> DEVELOPMENT
  -> DEV_SELF_TEST
  -> TEST_AND_SECURITY_VALIDATION
  -> USER_ACCEPTANCE
  -> DONE
```

### 10.4 XL 级

```text
不允许直接进入开发；
必须先拆成多个子项目；
每个子项目独立 PRD / 设计 / 开发 / 测试 / 验收；
PM 维护父项目进度。
```

### 10.5 升级到 L 的触发条件

```text
修改数据库 schema；
修改鉴权 / 权限 / 支付 / 风控 / 安全逻辑；
新增外部服务或关键依赖；
影响 CI/CD、部署、发布；
跨多个仓库；
需要迁移历史数据；
需要线上数据修复；
需求目标不明确；
存在多个产品方案；
测试无法自动验证；
失败影响范围不可控。
```

---

## 11. 按需并行调研机制

RES 不作为固定流程必经角色，而是按需并行派生的调研池。

触发场景：

```text
技术选型不明确；
需求存在多种产品方案；
外部 API / SDK 不熟；
需要竞品分析；
需要安全或合规判断；
开发评估发现实现风险。
```

推荐流程：

```text
PM / PDM / ARCH 判断需要调研
  -> 创建 research_task
  -> 并行派出 2~4 个 Research Agent
  -> 每个 Research Agent 独立调研一个方向
  -> Research Judge 汇总、交叉验证、battle
  -> 输出 research_report + recommendation
  -> 作为 PRD 或详细设计输入
```

关键原则：

```text
多个 Research Agent 可以并行 battle；
最终决策不能由调研员投票决定；
必须由 ARCH / PDM / PM 这类责任角色裁决；
WorkflowEngine 把 research_report 作为 evidence 进入后续阶段。
```

预算和停止条件：

```text
默认派生 2~3 个 Research Agent；
单次最多 4 个 Research Agent；
每个 Research Agent 必须有时间上限和 token / 成本预算；
每个调研结论必须给出证据来源或验证依据；
Research Judge 默认只汇总一轮 battle；
如果关键分歧无法收敛，升级给 ARCH 或用户决策。
```

---

## 12. 飞书交互设计

### 12.1 用户入口

用户只和 PM 交互：

```text
创建项目；
补充需求；
确认 PRD；
查看进度；
处理异常升级；
确认高风险动作；
验收结果；
暂停 / 恢复 / 取消项目。
```

### 12.2 飞书按钮

MVP 建议支持：

```text
确认 PRD；
驳回 PRD；
继续自动修复；
转人工处理；
修改需求；
确认高风险操作；
确认创建 PR / 推送分支；
确认执行迁移；
暂停项目；
恢复项目；
确认验收通过；
验收不通过；
取消项目。
```

飞书卡片按钮统一转成：

```text
confirmation decision
project command
status query
```

不允许 Feishu handler 直接写业务状态。

### 12.3 PM 主动巡检

```text
巡检周期：每 15 分钟扫描一次（可配置）
巡检内容：
  - running task 是否超时；
  - failed task 是否未处理；
  - open issue 是否卡住；
  - review 是否超过 deadline；
  - 项目是否等待用户确认；
  - 回流次数是否超阈值。

消息聚合规则（防止飞书轰炸）：
  - 30 分钟内相同项目的相同状态问题，不重复推送；
  - 只有以下情况才主动推送飞书消息：
    a. 项目状态发生变化
    b. Review 首次超时
    c. 连续 2 次巡检发现同一任务超时（升级预警）
    d. 创建 Escalation 需要用户决策
    e. 等待用户确认且确认即将超时
  - 用户可通过飞书 /status 命令随时查询，不受聚合规则限制
```

告警策略：

```text
首次超时 -> 飞书提醒（受消息聚合规则约束）；
连续 2 次超时 -> 飞书预警；
超过回流次数限制 -> 创建 Escalation 并推送用户决策卡片。
```

---

## 13. 数据模型建议

MVP 保留并增强：

```text
projects
project_events
agents
project_agents
tasks
task_contracts
task_runs
task_result_reviews
artifacts
reviews
review_comments
issues
test_checklists
test_checklist_items
escalations
agent_messages
confirmations
runner_policies
```

关键增强方向：

```text
projects 增加 workflow_template / size_level / current_round_json；
project_events 增加 event_key / correlation_id / causation_id / evidence_json；
project_agents 记录项目启用的 Agent、角色、配置快照和 prompt 版本；
tasks 增加 task_type / runner_type / workspace_strategy / depends_on_json / risk_level；
task_contracts 以 contract_json 为权威存储，常用字段只做查询索引，避免双写冲突；
task_runs 增加 input_snapshot_path / task_contract_path / repo_commit_sha / model_config_snapshot_json / exit_code；
artifacts 增加 source_task_run_id / checksum / content_type / size_bytes / is_final / parent_artifact_id；
reviews 增加 required_participants_json / submitted_participants_json / deadline；
issues 增加 source_task_run_id / fixed_by_task_id / verification_task_id / source_checklist_item_id；
test_checklists 作为测试清单父表，test_checklist_items 记录逐条执行结果；
confirmations 增加 timeout_minutes，便于与 API 请求保持一致；
新增 confirmations 表承载人工确认；
新增 runner_policies 表承载安全策略配置。
```

详细 DDL 以 `database-ddl-v0.1.md` 为准。

---

## 14. API 设计原则

```text
外部 API 表达用户意图；
内部服务决定能不能执行；
WorkflowEngine 决定状态是否推进；
Runner API 只服务受控执行，不暴露给普通用户。
```

公开 API 不应允许外部任意调用：

```text
POST /workflow/advance
POST /workflow/reject
```

推荐改为语义接口：

```text
提交确认；
提交评审；
完成任务；
验证 issue；
登记产物；
提交 Runner 结果。
```

详细 API 以 `api-design-v0.1.md` 为准。

---

## 15. 第一阶段目录结构建议

```text
ccHermesAgents/
  app/
    main.py
    core/
    config/
    agents/
      registry.py
      prompt_builder.py
      executor.py
      roles/
        pm.yaml
        pdm.yaml
        dev.yaml
        test.yaml
        arch.yaml
        sec.yaml
        research.yaml
        research_judge.yaml
    projects/
    workflows/
      phases.py
      state_machine.py
      guards.py
      phase_communication_rules.yaml
      engine.py
    tasks/
    runners/
      worker.py
      claude_code_runner.py
      direct_llm_runner.py
      script_runner.py
      workspace_manager.py
      result_parser.py
      artifact_collector.py
      log_collector.py
    artifacts/
    issues/
    reviews/
    confirmations/
    escalations/
    feishu/
    messaging/
    observability/
  configs/
    app.yaml
    agents.yaml
    models.yaml
    runner_policies.yaml
  docs/
    designs/
    prd/
    test-reports/
    security-reports/
  scripts/
  tests/
```

---

## 16. 推荐技术栈

```text
语言：Python
Web 框架：FastAPI
数据库：SQLite
ORM：SQLAlchemy
迁移：Alembic
任务队列：Dramatiq 或 RQ
配置：YAML + 环境变量
Runner：subprocess 调 Claude Code CLI
飞书：官方 SDK 或直接 HTTP
部署：Linux + Docker Compose
日志：structlog 或标准 logging
测试：pytest
```

推荐组合：

```text
FastAPI + SQLite + SQLAlchemy + Dramatiq + Docker Compose
```

---

## 17. 路线图

### Phase 0：Runner 安全执行验证

目标：只证明 Claude Code CLI 可以被安全、可控、可恢复地作为 Runner 后端。

范围：

```text
task_prompt.md；
task_context.json；
task_contract.json；
workspace 创建；
subprocess 调用；
timeout；
cancel；
日志收集；
diff 收集；
artifact 收集；
失败记录；
contract check。
```

### Phase 1：最小控制面

目标：项目、任务、契约、执行和产物可以被结构化管理。

范围：

```text
Project；
Task；
TaskContract；
TaskRun；
Artifact；
Runner Worker；
基础 Runner Policy；
不做完整 Review；
不接飞书；
不做多角色完整闭环。
```

### Phase 2：本地最小闭环

目标：不依赖飞书，先跑通 PDM -> DEV -> TEST -> Issue -> Fix -> Result Review。

范围：

```text
PDM Agent；
DEV Agent；
TEST Agent；
PRD artifact；
diff artifact；
test report；
issue 回流；
result review；
使用本地命令或内部 API 驱动。
```

### Phase 3：飞书 PM 入口

目标：用户只通过飞书和 PM Agent 交互。

范围：

```text
Feishu event；
Feishu interactive card；
Confirmation；
项目创建；
状态查询；
PRD 确认；
验收确认；
异常升级。
```

### Phase 4：评审、巡检与升级

目标：支持需求评审、设计评审、测试用例评审、PM 主动巡检和超时预警。

范围：

```text
Requirement Review；
Design Review；
Test Review；
ReviewComment；
Escalation；
PM Patrol Scheduler；
设计/测试用例评审。
```

### Phase 5：质量增强与研究能力

目标：扩展 ARCH、SEC、RES，提高复杂项目质量。

范围：

```text
ARCH Agent；
SEC Agent；
SAST；
dependency scan；
Research Agent pool；
Research Judge；
多方案比较；
安全报告。
```

---

## 18. 最终建议

优先建设：

```text
状态机驱动的多角色软件工程团队平台，
而不是自由对话式 multi-agent 实验平台。
```

最关键设计原则：

```text
Agent 负责产出，WorkflowEngine 负责决策；
Runner 负责执行，Hermes 负责状态；
飞书负责交互，Artifact 负责沉淀；
Task Contract 约束 Runner，Result Review 验证 Agent 意图是否被正确实现。
```
