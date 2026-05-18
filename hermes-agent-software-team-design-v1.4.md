# Hermes Agent 软件工程团队系统设计方案 v1.4

## 1. 结论摘要

本方案建议采用 **Hermes Orchestrated Agent Team** 架构：

```text
Hermes 状态机 + 任务队列 + 产物管理 + 评审门禁
  + Claude Code CLI Runner
  + 飞书 PM 入口
  + 角色 Prompt Agent
  + 可选 Claude Code Sub-agent 辅助执行
```

不建议第一版采用纯 Sub-agent，也不建议采用 OpenClaw / AutoGen / CrewAI 风格的自由 multi-agent 协商模式作为核心。

核心判断：

```text
长周期项目的关键不是让多个 Agent 自由聊天，
而是让项目状态、任务输入、产物、评审和异常升级可恢复、可审计、可重试。
```

因此：

- Hermes 负责记忆、状态、流程、任务、产物、评审、异常升级。
- Claude Code CLI 负责代码、文档、测试、安全扫描等具体执行。
- 飞书只暴露 PM Agent 给用户。
- PDM / DEV / TEST / SEC 等角色先以角色 Prompt + Runner 任务实现。
- WorkflowEngine 是唯一可以推进项目阶段的模块。
- Agent 不能直接修改项目状态。

---

## 2. 方案可行性判断

### 2.1 可行

从当前设计看，整体方向可行，原因是：

```text
1. 以状态机承载长周期项目流程，而不是依赖对话上下文。
2. 以 Task / TaskRun 承载异步任务执行，适合后台运行。
3. 以 Artifact 承载 PRD、设计文档、测试清单、代码 diff、报告等产物。
4. 以 Review / Issue / Escalation 承载评审、问题回流和人工决策。
5. 以 Runner Worker 封装 Claude Code CLI，避免把 CLI 直接暴露给业务层。
6. 飞书只作为用户交互入口，降低用户操作复杂度。
```

### 2.2 最大风险

最大风险不是 Agent 能力，而是工程控制面：

```text
1. MVP 范围过大导致迟迟无法跑通闭环。
2. Runner 权限边界不清导致误改文件、泄露密钥或资源失控。
3. Agent 自行判断阶段完成导致状态漂移。
4. 长周期任务缺少输入快照，失败后无法复现。
5. 多 Agent 自由通信导致责任边界混乱。
```

---

## 3. Sub-agent 与 Multi-agent 模式对比

### 3.1 Claude Code Sub-agent 模式

适合：

```text
代码搜索
局部实现
代码评审
并行短任务
测试补充
文档整理
```

优点：

```text
上下文隔离好；
适合单次任务内并行；
对代码仓库理解能力强；
能保护主会话上下文。
```

缺点：

```text
不适合作为长周期项目调度核心；
生命周期依赖主任务；
自身不负责项目状态持久化；
不能替代 WorkflowEngine、TaskQueue、ArtifactStore。
```

结论：

```text
Sub-agent 适合作为 Runner 内部能力，不适合作为系统总架构。
```

### 3.2 OpenClaw / AutoGen / CrewAI 风格 Multi-agent

适合：

```text
快速原型；
多角色讨论；
头脑风暴；
研究性任务；
一次性复杂问题求解。
```

优点：

```text
角色建模自然；
多 Agent 协作表达力强；
容易模拟会议和讨论；
适合验证协作流程。
```

缺点：

```text
状态一致性弱；
失败恢复复杂；
长期项目容易上下文漂移；
难以审计每一步为什么发生；
容易出现 Agent 之间互相确认但实际产物不合格的情况。
```

结论：

```text
Multi-agent 框架可以作为 AgentExecutor 的可选实现，但不建议作为 MVP 核心。
```

### 3.3 推荐：Hermes 混合编排模式

推荐模式：

```text
Hermes 管流程；
Runner 管执行；
Agent 管产出和评审意见；
WorkflowEngine 管阶段推进；
飞书 PM 管用户交互。
```

该模式的优势：

```text
1. 长周期项目可恢复。
2. 每个阶段有明确输入和输出。
3. 每次执行有 TaskRun 记录。
4. 每个产物有 Artifact 记录。
5. 每次失败有 Issue / Escalation 记录。
6. 用户只需要和 PM 交互。
7. 后续可以替换或扩展 Agent 执行引擎。
```

---

## 4. 角色实现分层

### 4.1 必须是真服务 / 真代码模块

这些模块不能只靠 LLM Prompt 实现：

| 模块 | 原因 |
|---|---|
| PM 交互服务 | 负责飞书消息、用户确认、状态查询和异常升级 |
| WorkflowEngine | 负责项目阶段推进，必须确定、可审计 |
| StateTransitionGuard | 防止非法状态跳转 |
| TaskService | 负责任务创建、分派、重试、取消 |
| Runner Worker | 负责调用 Claude Code CLI、收集日志和产物 |
| WorkspaceManager | 负责隔离 workspace |
| ArtifactService | 负责产物登记、版本化和查询 |
| EscalationManager | 负责超过重试阈值后的人工决策 |
| Feishu Module | 负责飞书事件、卡片、审批交互 |

### 4.2 第一版可以是角色 Prompt + Runner 任务

这些角色第一版不需要独立服务进程：

| Agent | 第一版实现方式 | 说明 |
|---|---|---|
| PDM | Prompt + Runner | 生成和修订 PRD |
| DEV | Prompt + Claude Code CLI Runner | 编码、自测、修复缺陷 |
| TEST | Prompt + Claude Code CLI Runner | 生成测试清单、执行测试、记录问题 |
| ARCH | Prompt + Runner，可先合并到 DEV | MVP 可延后独立化 |
| SEC | Prompt + 脚本扫描任务，可延后 | MVP 可先只保留安全边界，不做完整安全 Agent |
| RES | Prompt + Runner，按需并行派生 | 技术调研、竞品分析、方案搜索、资料整理，不是第一阶段闭环必需 |
| Research Judge | ARCH / PM / PDM 兼任 | 汇总多个调研结果，做交叉验证和方案裁决 |

### 4.3 Agent 权限边界

Agent 只能输出：

```text
建议
文档
评审意见
执行结果
问题单
下一步请求
```

Agent 不能直接执行：

```text
切换项目阶段
关闭评审
创建任意下一阶段任务
绕过测试结果
绕过用户确认
直接修改数据库状态
直接通知最终完成
```

只有 WorkflowEngine 可以：

```text
切阶段
创建下一任务
关闭评审
触发回流
触发异常升级
标记项目完成
```

### 4.4 按需并行调研机制

RES 不建议设计成固定流程必经角色，而应设计成按需并行派生的调研池。

触发场景：

```text
技术选型不明确
需求存在多种产品方案
外部 API / SDK 不熟
需要竞品分析
需要安全或合规判断
开发评估发现实现风险
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

Research Agent 负责独立产出：

```text
候选方案
依据来源
优点
缺点
风险
实现成本
长期维护成本
推荐程度
```

Research Judge 可以由 ARCH、PDM 或 PM 兼任，负责：

```text
去重和合并多个调研结论
识别互相矛盾的结论
要求补充证据
按评估维度打分
给出最终推荐方案
登记 research_report artifact
```

默认评估维度：

```text
可行性
实现成本
接入复杂度
安全风险
长期维护成本
生态成熟度
与现有技术栈匹配度
```

关键原则：

```text
多个 Research Agent 可以并行 battle，
但最终决策不能由调研员投票决定，
必须由 ARCH / PDM / PM 这类责任角色裁决，
并由 WorkflowEngine 把 research_report 作为 evidence 进入后续阶段。
```

---

## 5. MVP 范围收敛

### 5.1 第一版目标

第一版目标不是完整模拟一个软件公司，而是跑通一个稳定闭环：

```text
飞书用户
  -> PM 创建项目
  -> PDM 生成 PRD
  -> 用户确认 PRD
  -> DEV 编码实现
  -> DEV 自测
  -> TEST 执行验证清单
  -> TEST 发现问题并创建 Issue
  -> DEV 修复 Issue
  -> TEST 复测
  -> 全部通过
  -> PM 通知用户验收
  -> 用户确认完成
```

### 5.2 第一版必须包含

```text
FastAPI 后端
SQLite 数据库
Project / Task / TaskRun
Artifact
Issue
WorkflowEngine
Runner Worker
ClaudeCodeRunner
WorkspaceManager
Feishu webhook
Feishu interactive card
基础 Escalation
PDM / DEV / TEST 三类角色 Prompt
```

### 5.3 第一版可以暂缓

```text
独立 ARCH Agent
独立 SEC Agent
Researcher Agent 的完整 battle 系统
复杂全员评审会议
Excel 高级测试清单格式
多租户权限系统
成本统计
绩效统计
复杂模型路由
多项目大规模并发
Web 控制台
OpenClaw / AutoGen / CrewAI 集成
```

### 5.4 MVP 成功标准

MVP 成功的判断标准：

```text
1. 用户可以通过飞书创建一个项目。
2. 系统可以生成 PRD 并请求用户确认。
3. 用户确认后，DEV 可以通过 Claude Code CLI 修改代码。
4. 系统可以保存代码 diff、自测报告、日志和产物记录。
5. TEST 可以验证结果并生成问题。
6. 问题可以回流给 DEV 修复。
7. 重试超过阈值后可以升级给用户。
8. 项目状态可以随时查询。
9. 服务重启后项目可以继续推进。
```

---

## 6. 推荐系统架构

### 6.1 总体架构

```text
Feishu User
  |
  v
Feishu Bot / Webhook
  |
  v
PM Interaction Layer
  |
  v
Backend API / Modular Monolith
  |
  +--> ProjectService
  +--> WorkflowEngine
  +--> TaskService
  +--> ArtifactService
  +--> IssueService
  +--> ReviewService
  +--> EscalationManager
  +--> AgentExecutor
  |
  v
Task Queue
  |
  v
Runner Worker Pool
  |
  +--> WorkspaceManager
  +--> PromptBuilder
  +--> Claude Code CLI subprocess
  +--> LogCollector
  +--> ResultParser
  +--> ArtifactCollector
  |
  v
SQLite / File Storage / Git Workspace
```

### 6.2 模块化单体优先

MVP 阶段继续采用模块化单体：

```text
app/
  core/
  config/
  agents/
  projects/
  tasks/
  workflows/
  artifacts/
  issues/
  reviews/
  runners/
  feishu/
  escalations/
  messaging/
  security/
  observability/
```

原因：

```text
访问量初期不大；
业务状态复杂；
模块化单体更容易保证事务一致性；
后续可以按模块边界拆服务。
```

---

## 7. Workflow 设计

### 7.1 MVP 阶段状态

第一版建议先使用以下项目阶段：

```text
INIT
REQUIREMENT_DRAFTING
REQUIREMENT_USER_REVIEW
REQUIREMENT_APPROVED
DEVELOPMENT
DEV_SELF_TEST
TESTING
FIXING
USER_ACCEPTANCE
DONE
PAUSED
FAILED
CANCELLED
```

### 7.2 核心流转

```text
INIT
  -> REQUIREMENT_DRAFTING
  -> REQUIREMENT_USER_REVIEW
  -> REQUIREMENT_APPROVED
  -> DEVELOPMENT
  -> DEV_SELF_TEST
  -> TESTING
  -> USER_ACCEPTANCE
  -> DONE
```

问题回流：

```text
TESTING
  -> FIXING
  -> DEV_SELF_TEST
  -> TESTING
```

用户验收失败：

```text
USER_ACCEPTANCE
  -> FIXING
  -> DEV_SELF_TEST
  -> TESTING
  -> USER_ACCEPTANCE
```

异常升级：

```text
任意自动阶段
  -> PAUSED
  -> 用户决策
  -> 恢复 / 改需求 / 人工介入 / 取消
```

### 7.3 阶段推进原则

```text
1. 只有 WorkflowEngine 可以推进阶段。
2. 每次推进必须有 evidence。
3. evidence 可以是 artifact、issue、review、task_run 或用户确认。
4. 每次推进必须写 project_events。
5. Agent 输出只能作为 evidence，不能直接作为状态变更。
```

---

## 8. Runner 设计

### 8.1 Runner 职责

Runner 负责把系统任务转成 Claude Code CLI 可执行任务：

```text
创建 workspace
准备输入上下文
生成 task-prompt.md
生成 task-context.json
调用 claude CLI
限制执行时间和资源
收集 stdout / stderr
收集 diff / 文档 / 测试报告
解析执行结果
回写 task_run
登记 artifacts
```

### 8.2 Runner 生命周期

```text
CREATED
  -> PREPARING_WORKSPACE
  -> BUILDING_CONTEXT
  -> RUNNING_CLAUDE
  -> COLLECTING_RESULTS
  -> PARSING_OUTPUT
  -> COMPLETED / FAILED / TIMEOUT / CANCELLED
```

### 8.3 任务输入快照

每个 task_run 启动前必须生成输入快照：

```text
task_context.json
task_prompt.md
input_artifacts_manifest.json
repo_commit_sha
workspace_path
agent_config_snapshot
model_config_snapshot
runner_config_snapshot
```

目的：

```text
失败可复现；
结果可审计；
重试可对比；
长期项目不会因为上下文变化而无法解释历史行为。
```

### 8.4 Workspace 策略

| 任务类型 | 策略 | 写权限 |
|---|---|---|
| PDM 文档任务 | copy_workspace | docs / artifacts |
| DEV 代码任务 | git_worktree | repo workspace |
| TEST 测试任务 | clean_git_worktree | reports / artifacts，代码默认只读 |
| SEC 安全任务 | readonly_worktree 或 container_readonly_mount | reports / artifacts |
| PM 报告任务 | copy_workspace | reports / artifacts |

---

## 9. Runner 安全与可靠性要求

### 9.1 MVP 必须实现

```text
1. 每个 task_run 独立 workspace。
2. 代码任务使用 git worktree 或容器目录。
3. Runner 不能访问宿主敏感目录。
4. API Key 只通过环境变量注入，不写入 prompt 和日志。
5. 日志入库或落盘前做脱敏。
6. 每个 task_run 必须有 timeout。
7. 每个 task_run 必须有最大输出大小限制。
8. 每个项目必须有并发上限。
9. 每个任务必须有 retry 上限。
10. Runner 只能回写指定 artifact 目录。
11. 取消任务时必须能停止对应子进程。
12. 失败必须记录 error_type 和 error_message。
```

### 9.2 建议尽早实现

```text
容器级隔离
CPU / 内存限制
磁盘配额
网络访问开关
命令 allowlist / denylist
日志敏感信息扫描
artifact 完整性校验
workspace 自动清理策略
```

### 9.3 可延后实现

```text
复杂沙箱策略
多租户隔离
远程 Runner 集群
细粒度 RBAC
完整审计后台
成本计量系统
```

---

## 10. 数据模型调整建议

现有 DDL 方向基本合理，MVP 建议保留以下表：

```text
projects
project_events
agents
tasks
task_runs
artifacts
issues
escalations
agent_messages
```

Review 相关表可保留，但第一版可以只做轻量能力：

```text
reviews
review_comments
```

暂不需要复杂：

```text
review_rounds
artifact_relations
project_members
cost_records
permission tables
```

### 10.1 task_runs 建议补充字段

```text
input_snapshot_path
agent_config_snapshot_json
model_config_snapshot_json
runner_config_snapshot_json
repo_commit_sha
output_size_bytes
timeout_seconds
exit_code
```

### 10.2 artifacts 建议补充字段

```text
checksum
source_task_run_id
content_type
size_bytes
```

### 10.3 issues 建议明确来源

issue.source 建议固定为：

```text
test
security
acceptance
runner
workflow
user
```

---

## 11. API 调整建议

当前 API 设计可继续使用，MVP 建议优先实现：

```text
POST /api/projects
GET /api/projects/{project_id}
GET /api/projects/{project_id}/status
POST /api/projects/{project_id}/pause
POST /api/projects/{project_id}/resume

POST /api/projects/{project_id}/tasks
GET /api/projects/{project_id}/tasks
POST /api/tasks/{task_id}/start
POST /api/tasks/{task_id}/retry
POST /api/tasks/{task_id}/cancel

POST /api/runner/task-runs
GET /api/runner/task-runs/{task_run_id}
POST /api/runner/task-runs/{task_run_id}/cancel

POST /api/projects/{project_id}/artifacts
GET /api/projects/{project_id}/artifacts

GET /api/projects/{project_id}/issues
POST /api/projects/{project_id}/issues
POST /api/issues/{issue_id}/resolve
POST /api/issues/{issue_id}/reopen

POST /api/feishu/events
POST /api/feishu/interactive

GET /api/projects/{project_id}/escalations
POST /api/escalations/{escalation_id}/decision
```

Workflow 的外部 API 要谨慎：

```text
POST /api/projects/{project_id}/workflow/advance
POST /api/projects/{project_id}/workflow/reject
```

这些接口不应允许外部任意推进状态，只能用于受控操作，并且必须经过 StateTransitionGuard。

---

## 12. 飞书交互设计

### 12.1 用户只和 PM 交互

用户入口保持简单：

```text
创建项目
补充需求
确认 PRD
查看进度
处理异常升级
验收结果
暂停 / 恢复 / 取消项目
```

### 12.2 PM 主动通知场景

```text
PRD 待确认
任务开始执行
开发完成并进入测试
测试发现问题
连续失败超过阈值
需要用户决策
等待用户验收
项目完成
项目暂停或取消
```

### 12.3 飞书卡片按钮

MVP 建议支持：

```text
确认 PRD
驳回 PRD
继续自动修复
转人工处理
修改需求
暂停项目
恢复项目
确认验收通过
验收不通过
取消项目
```

---

## 13. 第一阶段目录结构建议

```text
ccHermesAgents/
  app/
    main.py

    core/
      database.py
      logging.py
      settings.py
      ids.py
      time.py

    config/
      loader.py
      model_resolver.py
      agent_resolver.py

    agents/
      registry.py
      prompt_builder.py
      executor.py
      roles/
        pm.yaml
        pdm.yaml
        dev.yaml
        test.yaml
        research.yaml
        research_judge.yaml

    projects/
      models.py
      schemas.py
      service.py
      router.py

    workflows/
      phases.py
      state_machine.py
      guards.py
      engine.py

    tasks/
      models.py
      schemas.py
      service.py
      router.py

    runners/
      models.py
      schemas.py
      router.py
      worker.py
      claude_code_runner.py
      workspace_manager.py
      prompt_builder.py
      result_parser.py
      artifact_collector.py
      log_collector.py

    artifacts/
      models.py
      schemas.py
      service.py
      router.py

    issues/
      models.py
      schemas.py
      service.py
      router.py

    escalations/
      models.py
      schemas.py
      service.py
      router.py

    feishu/
      router.py
      client.py
      parser.py
      card_builder.py
      handlers.py

    messaging/
      models.py
      service.py

    observability/
      events.py
      metrics.py

  configs/
    app.yaml
    agents.yaml
    models.yaml

  docs/
    designs/
    prd/
    test-reports/
    security-reports/

  scripts/
    dev.sh
    worker.sh

  tests/
```

---

## 14. 推荐技术栈

MVP 推荐：

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

说明：

```text
SQLite 适合个人和小团队第一版；
Dramatiq / RQ 比 Celery 更轻；
Docker Compose 足够支撑单机 Runner Worker；
后续需要多项目并发时再迁移 Postgres 和分布式队列。
```

---

## 15. 落地路线

### 15.1 Phase 1：基础控制面

目标：系统能创建项目、创建任务、调用 Runner、记录结果。

范围：

```text
FastAPI 项目骨架
SQLite 初始化
Project / Task / TaskRun / Artifact 表
WorkflowEngine 基础状态机
Runner Worker
ClaudeCodeRunner
WorkspaceManager
基础日志和错误记录
```

验收标准：

```text
可以手动创建一个任务；
Runner 可以调用 Claude Code CLI；
执行日志和产物可以登记；
任务状态可以从 running 变成 completed / failed。
```

### 15.2 Phase 2：飞书 PM 入口

目标：用户可以通过飞书驱动项目。

范围：

```text
Feishu webhook
Feishu interactive card
PM 消息解析
项目创建命令
项目状态查询
PRD 确认卡片
异常升级卡片
```

验收标准：

```text
用户可以通过飞书创建项目；
系统可以推送 PRD 待确认卡片；
用户点击确认后 WorkflowEngine 推进阶段。
```

### 15.3 Phase 3：PRD -> DEV 闭环

目标：从需求到开发自测跑通。

范围：

```text
PDM Agent Prompt
PRD Artifact
DEV Agent Prompt
代码 workspace
自测报告 Artifact
diff Artifact
```

验收标准：

```text
PDM 能生成 PRD；
用户确认 PRD；
DEV 能基于 PRD 修改代码；
系统能保存 diff 和自测结果。
```

### 15.4 Phase 4：TEST -> Issue -> DEV 修复闭环

目标：测试发现问题后能回流开发修复。

范围：

```text
TEST Agent Prompt
测试清单 Artifact
Issue 模型
Issue 回流 Workflow
DEV 修复任务
TEST 复测任务
```

验收标准：

```text
TEST 失败会创建 Issue；
WorkflowEngine 会创建 DEV 修复任务；
DEV 修复后 TEST 能复测；
全部通过后进入用户验收。
```

### 15.5 Phase 5：安全与扩展

目标：增强 Runner 安全和项目稳定性。

范围：

```text
Runner 容器隔离
资源限制
日志脱敏
SEC Agent
SAST 集成
Review 模块增强
多项目并发控制
Postgres 迁移准备
```

---

## 16. 后续可扩展方向

### 16.1 引入独立 ARCH Agent

适合在以下条件满足后引入：

```text
PRD -> DEV -> TEST 已稳定；
项目复杂度上升；
需要接口设计、数据库设计、技术选型沉淀。
```

### 16.2 引入 SEC Agent

适合在以下条件满足后引入：

```text
Runner 隔离已经完成；
项目开始处理真实代码仓库；
需要依赖扫描、SAST、敏感信息扫描。
```

### 16.3 引入 Research Agent 调研池

适合在以下条件满足后增强：

```text
PRD -> DEV -> TEST 闭环已稳定；
需求经常出现技术选型或竞品分析；
需要降低单个 Agent 调研偏差；
需要为方案决策保留可审计依据。
```

推荐实现方式：

```text
Research Agent 按需派生多个实例；
每个实例独立调研一个方向；
Research Judge 汇总 battle 结果；
最终输出 research_report artifact；
ARCH / PDM / PM 对最终方案负责。
```

### 16.4 引入 Multi-agent 框架

后续可以把 OpenClaw / AutoGen / CrewAI 作为 AgentExecutor 的一种实现：

```text
AgentExecutor
  +--> ClaudeCodeCliExecutor
  +--> DirectLlmExecutor
  +--> MultiAgentExecutor
```

但即使引入，也不能让 multi-agent 框架直接接管项目状态。

---

## 17. 最终建议

本项目应优先建设为：

```text
状态机驱动的多角色软件工程团队平台，
而不是自由对话式 multi-agent 实验平台。
```

第一版的目标应该是小而闭环：

```text
飞书创建项目
PRD 生成与确认
DEV 编码
TEST 验证
Issue 回流
用户验收
项目完成
```

只要这个闭环稳定，后续再逐步加入：

```text
ARCH
SEC
RES 调研池
复杂评审
多项目并发
成本统计
Web 控制台
Multi-agent 框架适配
```

最关键的设计原则：

```text
Agent 负责产出，WorkflowEngine 负责决策；
Runner 负责执行，Hermes 负责状态；
飞书负责交互，Artifact 负责沉淀。
```
