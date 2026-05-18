# Hermes 设计文档优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 直接优化现有三份设计文档，修复评审发现的状态机、Runner 队列、API/DDL 一致性和 MVP 落地性问题。

**Architecture:** 本次不改代码，只修改现有 Markdown 设计文档。主设计文档作为权威架构说明，API 和 DDL 文档同步其枚举、状态流转和数据结构；避免新增中间规格文档。

**Tech Stack:** Markdown 文档；无需运行应用测试；验证方式为 grep/人工一致性检查/git diff。

---

## File Structure

- Modify: `hermes-agent-software-team-design-v1.5.md`
  - 修正 `SCOPE_CHANGE` 定义。
  - 补充 Task 状态机、Task Queue / Runner Worker 执行模型、幂等推进、Result Review 责任边界。
  - 补充 `project_agents`、`test_checklists`、MVP 路线图裁剪建议。

- Modify: `api-design-v0.1.md`
  - 同步删除 `SCOPE_CHANGE` phase。
  - 补充 scope change 作为 command / escalation decision。
  - 明确 task 状态流转、Runner complete artifact 批量登记事务、Confirmation 字段。

- Modify: `database-ddl-v0.1.md`
  - 删除 `agents` 自引用外键。
  - 新增 `project_agents` 表。
  - 调整 `task_contracts`，避免展开字段与 `contract_json` 双写冲突。
  - 新增 `test_checklists` 父表。
  - 补充 `confirmations.timeout_minutes`。
  - 同步删除 `SCOPE_CHANGE` phase 枚举。

---

### Task 1: 修正主设计状态机与 scope change

**Files:**
- Modify: `hermes-agent-software-team-design-v1.5.md`

- [ ] **Step 1: 修改阶段枚举**

在 `## 5. Workflow 设计` 的 `### 5.1 统一阶段枚举` 中，从阶段枚举删除：

```text
SCOPE_CHANGE
```

并在枚举后新增说明：

```text
SCOPE_CHANGE 不作为 current_phase，也不作为 project.status。
它是用户或系统触发的变更命令，由 Confirmation / Escalation 承载。
变更被确认后，WorkflowEngine 根据影响范围创建新的 PRD 修订任务，通常回到 REQUIREMENT_DISCOVERY 或 REQUIREMENT_DRAFTING。
```

- [ ] **Step 2: 修改异常状态说明**

将原文：

```text
任意阶段 -> status=SCOPE_CHANGE（触发新 PRD 流程）
```

替换为：

```text
任意阶段 -> scope_change command / escalation decision
  -> 用户确认变更范围
  -> REQUIREMENT_DISCOVERY 或 REQUIREMENT_DRAFTING
  -> 生成新版 PRD artifact
```

- [ ] **Step 3: 增加 scope change 处理规则**

在 `问题回流` 或 `异常状态` 后补充：

```text
需求变更处理规则：
  - scope change 不直接修改 current_phase 或 status；
  - Feishu / PM 只提交 change_requirement 命令或 escalation decision；
  - WorkflowEngine 创建 scope_change_approval confirmation；
  - 用户确认后，按影响范围回到 REQUIREMENT_DISCOVERY 或 REQUIREMENT_DRAFTING；
  - 原 PRD / 设计 / 测试用例保留为历史 artifact，新版本通过 parent_artifact_id 关联；
  - 未确认前，项目可保持原阶段 paused，避免半变更状态。
```

- [ ] **Step 4: 自查主设计中不再出现 `status=SCOPE_CHANGE`**

Run:

```bash
grep -n "status=SCOPE_CHANGE\|SCOPE_CHANGE" hermes-agent-software-team-design-v1.5.md
```

Expected: 不再出现 `status=SCOPE_CHANGE`；如果出现 `SCOPE_CHANGE`，只能是说明“不作为 current_phase/status”的上下文。

---

### Task 2: 补充主设计 Task 状态机与 Runner Queue 模型

**Files:**
- Modify: `hermes-agent-software-team-design-v1.5.md`

- [ ] **Step 1: 在 `## 7. Agent 与 Runner 协作模型` 后新增 Task 状态机小节**

新增内容：

```text
### 7.5 Task 状态机

Task 表达业务任务，TaskRun 表达一次执行。Task 状态只能由 TaskService、Runner Worker 回调、Result Review 和 WorkflowEngine 按规则推进。

Task 状态转移：
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

约束：
  - task_run.status 不能直接决定 task.status=completed；
  - task.completed 必须依赖 Result Review passed；
  - WorkflowEngine 只使用 completed task / passed review / closed issue / approved confirmation 作为推进 evidence。
```

- [ ] **Step 2: 在 `## 8. Runner 设计` 中新增 Task Queue 小节**

在 `### 8.2 Runner 生命周期` 后新增：

```text
### 8.2.1 Task Queue / Runner Worker 模型

MVP 推荐使用 Dramatiq + Redis 作为任务队列，SQLite 仍然是业务状态源。

入队时机：
  - TaskService 创建 task_run 后，将 task.status 置为 queued；
  - 队列消息只包含 task_run_id，不携带完整上下文；
  - Runner Worker 领取后从数据库读取 task_run、task_contract、runner_policy 和输入快照路径。

队列消息：
{
  "task_run_id": "run_001",
  "idempotency_key": "task_run:run_001:start"
}

Worker 并发：
  - 同一项目同一时间最多一个 DEV 写工作区任务运行；
  - TEST / SEC 只读任务可以并行；
  - PDM / PM 文档任务可并行，但同一 artifact 只能有一个最终版标记任务；
  - Worker 池按 runner_type 设置并发上限。

状态更新责任：
  - Runner Worker 只更新 task_run.status 和运行输出；
  - TaskService 根据 Worker 开始执行事件把 task.status 从 queued 推到 running；
  - Result Review 决定 task.status 是 completed 还是 needs_revision；
  - WorkflowEngine 根据 evidence 推进 project.current_phase。

重试策略：
  - 队列框架只负责投递失败重试；
  - 业务重试次数以 tasks.retry_count / max_retries 为准；
  - Runner 超时、CLI 非零退出、输出缺失等错误写入 task_runs.error_code；
  - 达到 max_retries 后创建 escalation，不继续自动重试。
```

- [ ] **Step 3: 补充幂等推进说明**

在 `### 5.5 阶段推进原则` 后新增：

```text
幂等规则：
  - 所有会导致状态变化的命令必须带 idempotency key；
  - project_events.event_key 作为状态变更幂等键；
  - Feishu event_id / open_message_id、confirmation decision、runner complete/fail、review complete 都必须映射到稳定 event_key；
  - 如果 event_key 已存在，服务返回已有处理结果，不重复推进状态。
```

- [ ] **Step 4: 自查主设计新增小节存在**

Run:

```bash
grep -n "Task 状态机\|Task Queue / Runner Worker\|幂等规则" hermes-agent-software-team-design-v1.5.md
```

Expected: 三个关键词均有匹配。

---

### Task 3: 同步主设计数据模型与路线图

**Files:**
- Modify: `hermes-agent-software-team-design-v1.5.md`

- [ ] **Step 1: 更新数据模型建议表清单**

在 `## 13. 数据模型建议` 的表清单中增加：

```text
project_agents
task_contracts
task_result_reviews
test_checklists
```

确保表清单包含：

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

- [ ] **Step 2: 更新关键增强方向**

补充：

```text
project_agents 记录项目启用的 Agent、角色、配置快照和 prompt 版本；
task_contracts 以 contract_json 为权威存储，常用字段只做查询索引，避免双写冲突；
test_checklists 作为测试清单父表，test_checklist_items 记录逐条执行结果；
confirmations 增加 timeout_minutes，便于与 API 请求保持一致。
```

- [ ] **Step 3: 收敛路线图**

将 `## 17. 路线图` 调整为：

```text
Phase 0：Runner 安全执行验证
  只证明 Claude Code CLI 可以被安全、可控、可恢复地作为 Runner 后端。

Phase 1：最小控制面
  Project / Task / TaskContract / TaskRun / Artifact / Runner Worker。
  不做完整 Review，不接飞书，不做多角色完整闭环。

Phase 2：本地最小闭环
  PDM -> DEV -> TEST -> Issue -> Fix -> Result Review。
  使用本地命令或内部 API 驱动，不依赖飞书。

Phase 3：飞书 PM 入口
  Feishu event / interactive card / Confirmation / 状态查询 / PRD 确认 / 验收确认。

Phase 4：评审、巡检与升级
  Requirement Review / Design Review / Test Review / PM Patrol Scheduler / Escalation。

Phase 5：质量增强与研究能力
  ARCH / SEC / RES / SAST / dependency scan / Research Judge。
```

- [ ] **Step 4: 自查路线图包含最小控制面**

Run:

```bash
grep -n "最小控制面\|本地最小闭环\|飞书 PM 入口" hermes-agent-software-team-design-v1.5.md
```

Expected: 三个关键词均有匹配。

---

### Task 4: 同步 API 文档枚举、状态语义和 Runner 事务

**Files:**
- Modify: `api-design-v0.1.md`

- [ ] **Step 1: 删除 API phase 枚举中的 `SCOPE_CHANGE`**

在 `### 3.1 project.current_phase` 中删除：

```text
SCOPE_CHANGE
```

并新增说明：

```text
需求变更不作为 current_phase。外部通过 project command 或 escalation decision 提交 change_requirement，由 WorkflowEngine 创建 confirmation 并在用户确认后回到 REQUIREMENT_DISCOVERY 或 REQUIREMENT_DRAFTING。
```

- [ ] **Step 2: 补充 task.status 语义**

在 `### 3.2 task.status` 后新增：

```text
状态语义：
  pending：任务已创建，尚未分派。
  assigned：已分派 owner_agent / assigned_to。
  queued：已创建 task_run 并写入队列。
  running：Runner Worker 已领取并开始执行。
  result_pending_review：Runner 完成且机械校验通过，等待 Result Review。
  needs_revision：Result Review 要求修订。
  blocked：等待依赖、确认或外部条件。
  failed：执行失败且不可继续自动重试，或达到重试上限。
  completed：Result Review passed。
  cancelled：任务被取消。
```

- [ ] **Step 3: 修改 Task start API 说明**

在 `### 6.5 启动任务` 的说明后补充：

```text
启动任务时，服务端必须：
  1. 生成或锁定 task_contract；
  2. 创建 task_run；
  3. 将 task.status 置为 queued；
  4. 向队列写入仅包含 task_run_id 和 idempotency_key 的消息；
  5. 写 project_events 记录。
```

- [ ] **Step 4: 修改 Runner complete API 说明**

在 `### 16.4 Runner 完成` 后补充：

```text
Runner complete 的 artifacts 数组由内部服务在同一事务内登记到 artifacts 表。
如果任一 artifact 登记失败，complete 请求整体失败并保持 task_run 可重试或待人工处理。
Runner complete 只更新 task_run 和 artifact，不直接将 task 标记为 completed。
Task 是否完成由 Result Review 决定。
```

- [ ] **Step 5: 补充 Confirmation timeout 字段说明**

在 `### 12.1 创建确认请求` 后补充：

```text
timeout_minutes 用于记录创建确认时的原始超时配置；expires_at 是根据创建时间和 timeout_minutes 计算出的绝对过期时间。两者同时保存，便于审计和后续策略分析。
```

- [ ] **Step 6: 自查 API 文档不再把 SCOPE_CHANGE 当 phase**

Run:

```bash
grep -n "SCOPE_CHANGE\|需求变更不作为 current_phase\|Runner complete 只更新 task_run" api-design-v0.1.md
```

Expected: 不出现 phase 枚举中的 `SCOPE_CHANGE`；允许出现解释性说明。

---

### Task 5: 修正 DDL agents、project_agents 和 task_contracts

**Files:**
- Modify: `database-ddl-v0.1.md`

- [ ] **Step 1: 更新表清单**

在 `## 2. 表清单` 中增加：

```text
project_agents
```

放在 `agents` 后。

- [ ] **Step 2: 删除 agents 自引用外键**

在 `### 3.3 agents` 的 SQL 中删除：

```sql
    FOREIGN KEY (name) REFERENCES agents(name)
```

并确保前一行 `updated_at TEXT NOT NULL` 没有多余逗号。

- [ ] **Step 3: 在 agents 后新增 project_agents 表**

新增：

```sql
CREATE TABLE project_agents (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    role TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    prompt_version TEXT,
    agent_config_snapshot_json TEXT,
    model_config_snapshot_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (agent_name) REFERENCES agents(name)
);

CREATE UNIQUE INDEX idx_project_agents_project_agent ON project_agents(project_id, agent_name);
CREATE INDEX idx_project_agents_project_id ON project_agents(project_id);
CREATE INDEX idx_project_agents_agent_name ON project_agents(agent_name);
CREATE INDEX idx_project_agents_role ON project_agents(role);
```

并补充说明：

```text
agents 是全局 Agent 配置；project_agents 是项目级启用快照。
项目执行时以 project_agents 中的 prompt/model/config snapshot 为准，避免全局配置变更影响历史项目复现。
```

- [ ] **Step 4: 调整 task_contracts 权威字段说明**

保留 `contract_json TEXT NOT NULL`，并在 task_contracts 后补充：

```text
contract_json 是 Task Contract 的权威存储。
展开字段用于查询、过滤和常用校验，写入时必须由同一个 contract_json 派生，禁止由调用方分别提交两套值。
如果 MVP 需要进一步简化，可只保留 contract_json、task_goal、role、phase、timeout_seconds、created_by、created_at。
```

- [ ] **Step 5: 自查 agents 自引用已删除**

Run:

```bash
grep -n "FOREIGN KEY (name) REFERENCES agents(name)\|CREATE TABLE project_agents\|contract_json 是 Task Contract" database-ddl-v0.1.md
```

Expected: 不出现自引用 FK；出现 `CREATE TABLE project_agents` 和 task_contracts 权威说明。

---

### Task 6: 补齐 DDL test_checklists、confirmation 和 phase 枚举

**Files:**
- Modify: `database-ddl-v0.1.md`

- [ ] **Step 1: 更新表清单**

在 `test_checklist_items` 前新增：

```text
test_checklists
```

- [ ] **Step 2: 在 test_checklist_items 前新增 test_checklists 表**

新增：

```sql
CREATE TABLE test_checklists (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    source_artifact_id TEXT NOT NULL,
    name TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT 'v1',
    status TEXT NOT NULL DEFAULT 'active',
    total_count INTEGER NOT NULL DEFAULT 0,
    passed_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    blocked_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (source_artifact_id) REFERENCES artifacts(id)
);

CREATE INDEX idx_test_checklists_project_id ON test_checklists(project_id);
CREATE INDEX idx_test_checklists_source_artifact_id ON test_checklists(source_artifact_id);
CREATE INDEX idx_test_checklists_status ON test_checklists(status);
```

- [ ] **Step 3: 给 test_checklist_items.checklist_id 增加外键**

在 `test_checklist_items` SQL 中加入：

```sql
    FOREIGN KEY (checklist_id) REFERENCES test_checklists(id),
```

位置放在 `FOREIGN KEY (project_id) REFERENCES projects(id),` 后。

- [ ] **Step 4: confirmations 增加 timeout_minutes**

在 confirmations 表中 `options_json TEXT NOT NULL,` 后增加：

```sql
    timeout_minutes INTEGER,
```

- [ ] **Step 5: 删除 DDL phase 枚举中的 `SCOPE_CHANGE`**

在 `### 4.2 project.current_phase` 删除：

```text
SCOPE_CHANGE
```

并补充：

```text
需求变更通过 confirmation_type=scope_change_approval 或 escalation decision=change_requirement 表达，不进入 project.current_phase。
```

- [ ] **Step 6: 自查 DDL 新增内容和枚举**

Run:

```bash
grep -n "CREATE TABLE test_checklists\|timeout_minutes\|SCOPE_CHANGE\|scope_change_approval" database-ddl-v0.1.md
```

Expected: 出现 `CREATE TABLE test_checklists`、`timeout_minutes`、`scope_change_approval`；不应再有 phase 枚举中的 `SCOPE_CHANGE`。

---

### Task 7: 全文一致性检查与收尾

**Files:**
- Inspect: `hermes-agent-software-team-design-v1.5.md`
- Inspect: `api-design-v0.1.md`
- Inspect: `database-ddl-v0.1.md`

- [ ] **Step 1: 检查关键术语一致性**

Run:

```bash
grep -n "SCOPE_CHANGE\|status=SCOPE_CHANGE\|project_agents\|test_checklists\|Task Queue / Runner Worker\|Task 状态机" hermes-agent-software-team-design-v1.5.md api-design-v0.1.md database-ddl-v0.1.md
```

Expected:
- 不出现 `status=SCOPE_CHANGE`。
- `SCOPE_CHANGE` 只出现在“不是 phase/status”的说明里，或完全不出现。
- `project_agents` 和 `test_checklists` 在主设计与 DDL 中都出现。
- Task Queue / Task 状态机在主设计中出现。

- [ ] **Step 2: 检查 API/DDL confirmation 字段一致**

Run:

```bash
grep -n "timeout_minutes\|expires_at" api-design-v0.1.md database-ddl-v0.1.md
```

Expected: API 和 DDL 均包含 `timeout_minutes` 与 `expires_at`。

- [ ] **Step 3: 查看 diff**

Run:

```bash
git diff -- hermes-agent-software-team-design-v1.5.md api-design-v0.1.md database-ddl-v0.1.md
```

Expected: diff 只包含设计文档优化，不包含无关文件或格式化大改。

- [ ] **Step 4: 最终状态检查**

Run:

```bash
git status --short
```

Expected: 只显示三份设计文档和本计划文件有变更，除非用户另有未提交文件。

- [ ] **Step 5: 不提交变更，等待用户确认**

本任务不自动 commit。向用户汇报：

```text
已按评审建议优化三份设计文档，重点修复状态机、Runner 队列、API/DDL 一致性和 MVP 路线图。请 review diff 后决定是否继续细化或提交。
```

---

## Self-Review

- Spec coverage: 覆盖了用户选择的“直接优化现有三份文档”，包括状态机、Task Queue、Task 状态、API/DDL 同步、DDL 错误 FK、project_agents、test_checklists、MVP 裁剪。
- Placeholder scan: 无 TBD/TODO/类似占位指令。
- Type consistency: 术语统一为 `project_agents`、`test_checklists`、`Task Queue / Runner Worker`、`scope_change_approval`、`change_requirement`。
