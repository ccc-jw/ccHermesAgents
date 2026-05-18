# 数据库 DDL 设计 v0.2

## 1. 设计目标

数据库用于承载 Hermes Agent 软件工程团队平台的长期项目状态、任务执行记录、评审记录、缺陷记录、异常升级、Agent 间消息、人工确认、Runner 策略和产物索引。

初期使用 SQLite，DDL 尽量保持与 Postgres 兼容，便于后续迁移。

设计原则：

```text
projects 保存当前状态快照；
project_events 保存审计事件；
tasks 表达业务任务；
task_runs 表达一次具体执行；
task_contracts 固化 Agent 意图与 Runner 执行契约；
artifacts 保存产物索引和版本链；
reviews / review_comments 支撑结构化评审；
issues 支撑缺陷修复与复测闭环；
confirmations 支撑人工确认与飞书卡片决策；
runner_policies 支撑 Runner 安全策略审计。
```

---

## 2. 表清单

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
confirmations
escalations
agent_messages
runner_policies
```

---

## 3. DDL

### 3.1 projects

```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    owner_user_id TEXT NOT NULL,
    repo_url TEXT,
    default_branch TEXT DEFAULT 'main',
    status TEXT NOT NULL DEFAULT 'active',
    current_phase TEXT NOT NULL DEFAULT 'INIT',
    workflow_template TEXT NOT NULL DEFAULT 'standard',
    size_level TEXT NOT NULL DEFAULT 'M',
    current_round_json TEXT,
    paused_reason TEXT,
    cancelled_reason TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_projects_owner_user_id ON projects(owner_user_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_current_phase ON projects(current_phase);
CREATE INDEX idx_projects_size_level ON projects(size_level);
```

---

### 3.2 project_events

```sql
CREATE TABLE project_events (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_key TEXT,
    actor_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    correlation_id TEXT,
    causation_id TEXT,
    evidence_json TEXT,
    payload_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE UNIQUE INDEX idx_project_events_event_key ON project_events(event_key) WHERE event_key IS NOT NULL;
CREATE INDEX idx_project_events_project_id ON project_events(project_id);
CREATE INDEX idx_project_events_event_type ON project_events(event_type);
CREATE INDEX idx_project_events_created_at ON project_events(created_at);
CREATE INDEX idx_project_events_correlation_id ON project_events(correlation_id);
```

---

### 3.3 agents

```sql
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL,
    description TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    executor_type TEXT NOT NULL DEFAULT 'claude_code_cli',
    model_config_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_agents_enabled ON agents(enabled);
CREATE INDEX idx_agents_role ON agents(role);
```

`model_config_json` 字段采用统一的 OpenAI 兼容格式：

```json
{
  "provider": "openai_compatible",
  "base_url": "https://api.openai.com/v1",
  "api_key_env": "DEV_MODEL_API_KEY",
  "model": "gpt-4o",
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

运行时构造请求时从环境变量读取 `api_key_env` 对应的真实 Key，
确保 API Key 不写入数据库、不写入日志、不写入 prompt。

---

### 3.4 project_agents

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

agents 是全局 Agent 配置；project_agents 是项目级启用快照。
项目执行时以 project_agents 中的 prompt/model/config snapshot 为准，避免全局配置变更影响历史项目复现。

---

### 3.5 tasks

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    phase TEXT NOT NULL,
    owner_agent TEXT NOT NULL,
    task_type TEXT NOT NULL DEFAULT 'agent_task',
    runner_type TEXT,
    workspace_strategy TEXT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    priority TEXT NOT NULL DEFAULT 'normal',
    risk_level TEXT NOT NULL DEFAULT 'normal',
    requires_user_confirmation INTEGER NOT NULL DEFAULT 0,
    input_artifacts_json TEXT,
    expected_artifacts_json TEXT,
    depends_on_json TEXT,
    blocked_by_json TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    created_by TEXT NOT NULL,
    assigned_to TEXT,
    deadline TEXT,
    deadline_policy TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX idx_tasks_project_id ON tasks(project_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_phase ON tasks(phase);
CREATE INDEX idx_tasks_owner_agent ON tasks(owner_agent);
CREATE INDEX idx_tasks_task_type ON tasks(task_type);
CREATE INDEX idx_tasks_risk_level ON tasks(risk_level);
```

---

### 3.6 task_contracts

```sql
CREATE TABLE task_contracts (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT 'v1',
    task_goal TEXT NOT NULL,
    role TEXT NOT NULL,
    phase TEXT NOT NULL,
    input_artifacts_json TEXT,
    must_read_artifacts_json TEXT,
    allowed_paths_json TEXT,
    forbidden_paths_json TEXT,
    expected_artifacts_json TEXT,
    acceptance_criteria_json TEXT,
    quality_gates_json TEXT,
    risk_controls_json TEXT,
    review_required INTEGER NOT NULL DEFAULT 1,
    max_changed_files INTEGER,
    timeout_seconds INTEGER,
    contract_json TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX idx_task_contracts_task_id ON task_contracts(task_id);
CREATE INDEX idx_task_contracts_project_id ON task_contracts(project_id);
```

contract_json 是 Task Contract 的权威存储。
展开字段用于查询、过滤和常用校验，写入时必须由同一个 contract_json 派生，禁止由调用方分别提交两套值。
如果 MVP 需要进一步简化，可只保留 contract_json、task_goal、role、phase、timeout_seconds、created_by、created_at。

---

### 3.7 task_runs

```sql
CREATE TABLE task_runs (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    task_contract_id TEXT,
    runner_policy_id TEXT,
    agent_name TEXT NOT NULL,
    runner_type TEXT NOT NULL DEFAULT 'claude_code_cli',
    workspace_path TEXT,
    workspace_strategy TEXT,
    status TEXT NOT NULL DEFAULT 'CREATED',
    input_snapshot_path TEXT,
    task_contract_path TEXT,
    input_artifacts_manifest_path TEXT,
    output_manifest_path TEXT,
    agent_config_snapshot_json TEXT,
    model_config_snapshot_json TEXT,
    runner_config_snapshot_json TEXT,
    repo_url TEXT,
    repo_commit_sha TEXT,
    base_branch TEXT,
    worktree_branch TEXT,
    timeout_seconds INTEGER,
    output_size_bytes INTEGER,
    artifact_size_bytes INTEGER,
    exit_code INTEGER,
    started_at TEXT,
    finished_at TEXT,
    cancel_requested_at TEXT,
    cancelled_at TEXT,
    logs_path TEXT,
    stdout_path TEXT,
    stderr_path TEXT,
    diff_path TEXT,
    summary TEXT,
    error_code TEXT,
    error_type TEXT,
    error_message TEXT,
    security_policy_result_json TEXT,
    contract_check_result_json TEXT,
    result_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (task_contract_id) REFERENCES task_contracts(id),
    FOREIGN KEY (runner_policy_id) REFERENCES runner_policies(id)
);

CREATE INDEX idx_task_runs_task_id ON task_runs(task_id);
CREATE INDEX idx_task_runs_project_id ON task_runs(project_id);
CREATE INDEX idx_task_runs_status ON task_runs(status);
CREATE INDEX idx_task_runs_agent_name ON task_runs(agent_name);
CREATE INDEX idx_task_runs_runner_policy_id ON task_runs(runner_policy_id);
```

---

### 3.8 task_result_reviews

```sql
CREATE TABLE task_result_reviews (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    task_run_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    reviewer_agent TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    contract_compliance TEXT,
    semantic_compliance TEXT,
    test_compliance TEXT,
    summary TEXT,
    required_changes_json TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (task_run_id) REFERENCES task_runs(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX idx_task_result_reviews_task_id ON task_result_reviews(task_id);
CREATE INDEX idx_task_result_reviews_task_run_id ON task_result_reviews(task_run_id);
CREATE INDEX idx_task_result_reviews_status ON task_result_reviews(status);
```

---

### 3.9 artifacts

```sql
CREATE TABLE artifacts (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    task_id TEXT,
    source_task_run_id TEXT,
    artifact_type TEXT NOT NULL,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    logical_path TEXT,
    version TEXT NOT NULL DEFAULT 'v1',
    status TEXT NOT NULL DEFAULT 'active',
    created_by TEXT NOT NULL,
    checksum TEXT,
    content_type TEXT,
    size_bytes INTEGER,
    storage_backend TEXT NOT NULL DEFAULT 'local',
    is_final INTEGER NOT NULL DEFAULT 0,
    parent_artifact_id TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (source_task_run_id) REFERENCES task_runs(id),
    FOREIGN KEY (parent_artifact_id) REFERENCES artifacts(id)
);

CREATE INDEX idx_artifacts_project_id ON artifacts(project_id);
CREATE INDEX idx_artifacts_task_id ON artifacts(task_id);
CREATE INDEX idx_artifacts_source_task_run_id ON artifacts(source_task_run_id);
CREATE INDEX idx_artifacts_type ON artifacts(artifact_type);
CREATE INDEX idx_artifacts_is_final ON artifacts(is_final);
```

---

### 3.10 reviews

```sql
CREATE TABLE reviews (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    type TEXT NOT NULL,
    phase TEXT NOT NULL,
    round INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'open',
    owner_agent TEXT NOT NULL,
    participants_json TEXT NOT NULL,
    required_participants_json TEXT,
    submitted_participants_json TEXT,
    input_artifacts_json TEXT,
    blocking_comment_count INTEGER NOT NULL DEFAULT 0,
    major_comment_count INTEGER NOT NULL DEFAULT 0,
    conclusion TEXT,
    summary TEXT,
    evidence_json TEXT,
    deadline TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX idx_reviews_project_id ON reviews(project_id);
CREATE INDEX idx_reviews_type ON reviews(type);
CREATE INDEX idx_reviews_status ON reviews(status);
CREATE INDEX idx_reviews_phase ON reviews(phase);
```

---

### 3.11 review_comments

```sql
CREATE TABLE review_comments (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL,
    reviewer_agent TEXT NOT NULL,
    comment_type TEXT NOT NULL DEFAULT 'issue',
    status TEXT NOT NULL DEFAULT 'open',
    severity TEXT NOT NULL DEFAULT 'minor',
    comment TEXT NOT NULL,
    required_change TEXT,
    related_artifact TEXT,
    resolved_by TEXT,
    resolved_at TEXT,
    resolution_note TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (review_id) REFERENCES reviews(id)
);

CREATE INDEX idx_review_comments_review_id ON review_comments(review_id);
CREATE INDEX idx_review_comments_reviewer_agent ON review_comments(reviewer_agent);
CREATE INDEX idx_review_comments_status ON review_comments(status);
CREATE INDEX idx_review_comments_comment_type ON review_comments(comment_type);
```

---

### 3.12 issues

```sql
CREATE TABLE issues (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    source TEXT NOT NULL,
    phase TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT NOT NULL DEFAULT 'major',
    priority TEXT NOT NULL DEFAULT 'normal',
    assigned_agent TEXT,
    related_artifacts_json TEXT,
    reproduce_steps_json TEXT,
    expected_result TEXT,
    actual_result TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    source_review_comment_id TEXT,
    source_task_run_id TEXT,
    source_checklist_item_id TEXT,
    fixed_by_task_id TEXT,
    verification_task_id TEXT,
    verified_by TEXT,
    verified_at TEXT,
    root_cause TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (source_review_comment_id) REFERENCES review_comments(id),
    FOREIGN KEY (source_task_run_id) REFERENCES task_runs(id),
    FOREIGN KEY (source_checklist_item_id) REFERENCES test_checklist_items(id),
    FOREIGN KEY (fixed_by_task_id) REFERENCES tasks(id),
    FOREIGN KEY (verification_task_id) REFERENCES tasks(id)
);

CREATE INDEX idx_issues_project_id ON issues(project_id);
CREATE INDEX idx_issues_status ON issues(status);
CREATE INDEX idx_issues_source ON issues(source);
CREATE INDEX idx_issues_severity ON issues(severity);
CREATE INDEX idx_issues_assigned_agent ON issues(assigned_agent);
```

---

### 3.13 test_checklists

测试清单父表，用于记录测试清单整体元数据和执行统计。

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

---

### 3.14 test_checklist_items

测试清单逐条明细，用于结构化跟踪每个测试用例的执行状态，支撑"共 50 条，通过 42 条，失败 8 条"的进度查询。

```sql
CREATE TABLE test_checklist_items (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    checklist_id TEXT NOT NULL,
    item_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    test_steps TEXT,
    expected_result TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    actual_result TEXT,
    failure_description TEXT,
    linked_issue_id TEXT,
    verified_by TEXT,
    verified_at TEXT,
    verification_task_run_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (checklist_id) REFERENCES test_checklists(id),
    FOREIGN KEY (linked_issue_id) REFERENCES issues(id),
    FOREIGN KEY (verification_task_run_id) REFERENCES task_runs(id)
);

CREATE INDEX idx_test_checklist_items_project_id ON test_checklist_items(project_id);
CREATE INDEX idx_test_checklist_items_checklist_id ON test_checklist_items(checklist_id);
CREATE INDEX idx_test_checklist_items_status ON test_checklist_items(status);
CREATE INDEX idx_test_checklist_items_linked_issue ON test_checklist_items(linked_issue_id);
```

---

### 3.15 confirmations

```sql
CREATE TABLE confirmations (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    confirmation_type TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    requested_to_user_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    options_json TEXT NOT NULL,
    timeout_minutes INTEGER,
    selected_option TEXT,
    decision_comment TEXT,
    expires_at TEXT,
    decided_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX idx_confirmations_project_id ON confirmations(project_id);
CREATE INDEX idx_confirmations_type ON confirmations(confirmation_type);
CREATE INDEX idx_confirmations_status ON confirmations(status);
CREATE INDEX idx_confirmations_target ON confirmations(target_type, target_id);
```

---

### 3.16 escalations

```sql
CREATE TABLE escalations (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    type TEXT NOT NULL,
    phase TEXT NOT NULL,
    source_agent TEXT,
    target_user_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending_user_decision',
    blocking_object_type TEXT,
    blocking_object_id TEXT,
    retry_count INTEGER NOT NULL,
    threshold INTEGER NOT NULL,
    summary TEXT NOT NULL,
    options_json TEXT NOT NULL,
    selected_option TEXT,
    decision TEXT,
    decision_comment TEXT,
    expires_at TEXT,
    decided_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX idx_escalations_project_id ON escalations(project_id);
CREATE INDEX idx_escalations_status ON escalations(status);
CREATE INDEX idx_escalations_type ON escalations(type);
CREATE INDEX idx_escalations_blocking_object ON escalations(blocking_object_type, blocking_object_id);
```

---

### 3.17 agent_messages

```sql
CREATE TABLE agent_messages (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    from_agent TEXT NOT NULL,
    to_agent TEXT NOT NULL,
    message_type TEXT NOT NULL,
    phase TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    related_artifacts_json TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    guard_result_json TEXT,
    requires_response INTEGER NOT NULL DEFAULT 0,
    responded_at TEXT,
    response_artifact_id TEXT,
    linked_issue_id TEXT,
    linked_review_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (response_artifact_id) REFERENCES artifacts(id),
    FOREIGN KEY (linked_issue_id) REFERENCES issues(id),
    FOREIGN KEY (linked_review_id) REFERENCES reviews(id)
);

CREATE INDEX idx_agent_messages_project_id ON agent_messages(project_id);
CREATE INDEX idx_agent_messages_to_agent ON agent_messages(to_agent);
CREATE INDEX idx_agent_messages_from_agent ON agent_messages(from_agent);
CREATE INDEX idx_agent_messages_status ON agent_messages(status);
CREATE INDEX idx_agent_messages_type ON agent_messages(message_type);
```

---

### 3.18 runner_policies

```sql
CREATE TABLE runner_policies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    policy_json TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_runner_policies_name ON runner_policies(name);
CREATE INDEX idx_runner_policies_enabled ON runner_policies(enabled);
```

---

## 4. 枚举建议

### 4.1 project.status

```text
active
paused
failed
cancelled
done
```

### 4.2 project.current_phase

项目阶段枚举，仅表达项目当前处于哪个工作阶段。
项目状态（active/paused/failed/cancelled/done）由 projects.status 字段独立管理。

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

需求变更通过 confirmation_type=scope_change_approval 或 escalation decision=change_requirement 表达，不进入 project.current_phase。

当项目暂停时，projects.status='paused' 但 current_phase 保留暂停前的真实阶段（如 DEVELOPMENT），
恢复项目时可准确恢复到暂停时的阶段继续执行。

### 4.3 task.status

```text
pending
assigned
queued
running
result_pending_review
needs_revision
blocked
failed
completed
cancelled
```

### 4.4 task_run.status

```text
CREATED
PREPARING_WORKSPACE
BUILDING_CONTEXT
RUNNING
COLLECTING_RESULTS
PARSING_OUTPUT
COMPLETED
FAILED
TIMEOUT
CANCELLED
```

### 4.5 review.status

```text
open
passed
failed
cancelled
timeout
```

### 4.6 task_result_review.status

```text
pending
passed
failed
needs_revision
cancelled
```

### 4.7 review_comment.status

```text
open
resolved
accepted
rejected
```

### 4.8 issue.status

```text
open
assigned
fixing
fixed
retesting
verified
reopened
rejected
deferred
closed
blocked
```

### 4.9 issue.source

```text
test
security
acceptance
review
runner
workflow
user
```

### 4.10 confirmation.status

```text
pending
approved
rejected
expired
cancelled
```

### 4.11 confirmation_type

```text
prd_approval
design_approval
risky_action_approval
scope_change_approval
delivery_acceptance
escalation_decision
```

### 4.12 artifact_type

```text
prd_draft
prd_final
design_draft
design_final
testcase_doc          # Markdown 格式测试用例文档（评审用）
test_checklist        # Excel 格式测试清单（逐条执行用，由 script_runner 从 testcase_doc 生成）
diff_patch
self_test_report
test_report
security_report
research_report
acceptance_report
runner_log
task_contract
result_review
```

### 4.13 agent_message.status

```text
pending
sent
responded
rejected_by_guard
cancelled
```

### 4.14 runner_type

```text
claude_code_cli
direct_llm
script_runner
sast_runner
test_runner
multi_agent_runner
```

### 4.15 test_checklist_item.status

```text
pending
pass
fail
blocked
skipped
```

### 4.16 workspace_strategy

```text
artifact_workspace
copy_workspace
git_worktree
clean_git_worktree
readonly_worktree
container_readonly_mount
no_repo_workspace
```

### 4.17 runner error_code

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

---

## 5. 状态一致性原则

```text
projects.current_phase / projects.status 是当前状态快照；
project_events 是审计日志；
状态变更时必须同时更新 projects 快照并写 project_events；
MVP 不要求完全通过 event replay 恢复状态；
后续可演进为完整 Event Sourcing。
```

---

## 6. 下一步

DDL v0.2 与主设计 v2.0、API v0.2 对齐后，可以进入实现计划拆分。

新增 test_checklist_items 表用于结构化跟踪测试清单逐条执行结果。
