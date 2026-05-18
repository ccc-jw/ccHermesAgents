# 后端 API 设计 v0.2

## 1. 设计目标

本 API 设计用于支撑 Hermes Agent 软件工程团队平台。

API 面向四类调用方：

```text
飞书回调；
PM / 用户状态查询；
内部 Agent / Workflow 调度；
Runner Worker。
```

核心原则：

```text
外部 API 表达用户意图；
内部服务决定能不能执行；
WorkflowEngine 决定状态是否推进；
Runner API 只服务受控执行，不暴露给普通用户；
Feishu handler 不直接写业务状态，只转换成 command / confirmation decision。
```

---

## 2. 通用响应格式

成功：

```json
{
  "success": true,
  "data": {},
  "request_id": "req_001"
}
```

失败：

```json
{
  "success": false,
  "error": {
    "code": "PROJECT_NOT_FOUND",
    "message": "项目不存在"
  },
  "request_id": "req_001"
}
```

---

## 3. 统一枚举

### 3.1 project.current_phase

项目阶段枚举，仅表达当前工作阶段。
项目状态（active/paused/failed/cancelled/done）由 projects.status 独立管理，
暂停/恢复时不丢失当前所处阶段信息。

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

需求变更不作为 current_phase。外部通过 project command 或 escalation decision 提交 change_requirement，由 WorkflowEngine 创建 confirmation 并在用户确认后回到 REQUIREMENT_DISCOVERY 或 REQUIREMENT_DRAFTING。

### 3.2 task.status

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

状态语义：

```text
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

### 3.3 task_run.status

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

### 3.4 task_result_review.status

```text
pending
passed
failed
needs_revision
cancelled
```

### 3.5 agent_message.status

```text
pending
sent
responded
rejected_by_guard
cancelled
```

### 3.6 runner_type

```text
claude_code_cli      # MVP 主要使用，代码生成和文档生成
script_runner        # MVP 使用，Excel 生成/简单脚本测试/SAST 扫描
direct_llm           # MVP 后使用
sast_runner          # MVP 后使用
test_runner          # MVP 后使用
multi_agent_runner   # MVP 后使用
```

### 3.7 workspace_strategy

```text
artifact_workspace
copy_workspace
git_worktree
clean_git_worktree
readonly_worktree
container_readonly_mount
no_repo_workspace
```

### 3.8 artifact_type

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

---

## 4. Project API

### 4.1 创建项目

```http
POST /api/projects
```

请求：

```json
{
  "name": "用户登录功能",
  "description": "实现账号密码登录、错误提示和权限校验",
  "owner_user_id": "feishu_user_001",
  "repo_url": "https://github.com/example/app",
  "default_branch": "main",
  "initial_requirement": "需要实现登录功能",
  "size_level": "M",
  "workflow_template": "standard"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "id": "proj_001",
    "name": "用户登录功能",
    "status": "active",
    "current_phase": "INIT"
  },
  "request_id": "req_001"
}
```

### 4.2 查询项目详情

```http
GET /api/projects/{project_id}
```

响应：

```json
{
  "success": true,
  "data": {
    "id": "proj_001",
    "name": "用户登录功能",
    "description": "实现账号密码登录、错误提示和权限校验",
    "owner_user_id": "feishu_user_001",
    "repo_url": "https://github.com/example/app",
    "default_branch": "main",
    "status": "active",
    "current_phase": "REQUIREMENT_REVIEW",
    "size_level": "M",
    "workflow_template": "standard",
    "created_at": "2026-05-17T10:00:00+08:00",
    "updated_at": "2026-05-17T10:10:00+08:00"
  },
  "request_id": "req_002"
}
```

### 4.3 查询项目状态

```http
GET /api/projects/{project_id}/status
```

响应：

```json
{
  "success": true,
  "data": {
    "project_id": "proj_001",
    "current_phase": "DESIGN_REVIEW",
    "status": "active",
    "progress_summary": "详细设计和测试清单正在评审。",
    "pending_user_actions": [],
    "open_issues_count": 2,
    "running_tasks": ["task_010"],
    "blocked_reason": null,
    "next_expected_action": "等待 TEST 提交详细设计评审意见",
    "risks": []
  },
  "request_id": "req_003"
}
```

### 4.4 暂停项目

```http
POST /api/projects/{project_id}/pause
```

请求：

```json
{
  "reason": "等待用户确认设计变更"
}
```

### 4.5 恢复项目

```http
POST /api/projects/{project_id}/resume
```

请求：

```json
{
  "reason": "用户已确认继续推进"
}
```

### 4.6 终止项目

```http
POST /api/projects/{project_id}/cancel
```

请求：

```json
{
  "reason": "用户决定终止当前需求"
}
```

---

## 5. Workflow Query API

Workflow 推进不对外开放任意 `advance/reject`。外部调用方提交确认、评审、任务结果、Issue 验证等 evidence 后，由 WorkflowEngine 判断能否推进。

### 5.1 查询工作流状态

```http
GET /api/projects/{project_id}/workflow
```

响应：

```json
{
  "success": true,
  "data": {
    "project_id": "proj_001",
    "current_phase": "DESIGN_REVIEW",
    "allowed_user_actions": [
      "pause",
      "cancel"
    ],
    "waiting_evidence": [
      "design_review_passed",
      "testcase_review_passed"
    ]
  },
  "request_id": "req_006"
}
```

---

## 6. Task API

### 6.1 创建任务

```http
POST /api/projects/{project_id}/tasks
```

请求：

```json
{
  "phase": "DEVELOPMENT",
  "owner_agent": "DEV",
  "task_type": "coding",
  "runner_type": "claude_code_cli",
  "workspace_strategy": "git_worktree",
  "title": "实现登录接口",
  "description": "根据 PRD 和详细设计实现登录接口",
  "input_artifacts": [
    "artifact_prd_final",
    "artifact_design_final"
  ],
  "expected_artifacts": [
    "diff_patch",
    "self_test_report"
  ],
  "depends_on": [],
  "risk_level": "normal",
  "requires_user_confirmation": false,
  "max_retries": 3,
  "deadline": "2026-05-20T18:00:00+08:00"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "id": "task_001",
    "status": "pending"
  },
  "request_id": "req_004"
}
```

### 6.2 查询任务列表

```http
GET /api/projects/{project_id}/tasks
```

可选查询参数：

```text
status
phase
owner_agent
task_type
```

### 6.3 查询任务详情

```http
GET /api/tasks/{task_id}
```

### 6.4 分派任务

```http
POST /api/tasks/{task_id}/assign
```

请求：

```json
{
  "assigned_to": "DEV"
}
```

### 6.5 启动任务

```http
POST /api/tasks/{task_id}/start
```

该接口不直接启动 subprocess，只创建 `task_run` 并写入队列，由 Runner Worker 拉取执行。

启动任务时，服务端必须：

```text
  1. 生成或锁定 task_contract；
  2. 创建 task_run；
  3. 将 task.status 置为 queued；
  4. 向队列写入仅包含 task_run_id 和 idempotency_key 的消息；
  5. 写 project_events 记录。
```

请求：

```json
{
  "runner_type": "claude_code_cli",
  "workspace_strategy": "git_worktree"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "task_run_id": "run_001",
    "status": "CREATED"
  },
  "request_id": "req_005"
}
```

### 6.6 重试任务

```http
POST /api/tasks/{task_id}/retry
```

请求：

```json
{
  "reason": "修复测试失败后重试"
}
```

### 6.7 取消任务

```http
POST /api/tasks/{task_id}/cancel
```

请求：

```json
{
  "reason": "项目已暂停"
}
```

---

## 7. Task Contract API

Task Contract 由 AgentExecutor 生成，是 Agent 意图和 Runner 执行之间的契约。

### 7.1 查询 Task Contract

```http
GET /api/tasks/{task_id}/contract
```

响应：

```json
{
  "success": true,
  "data": {
    "task_goal": "实现账号密码登录接口",
    "role": "DEV",
    "phase": "DEVELOPMENT",
    "must_read_artifacts": ["artifact_prd_final", "artifact_design_final"],
    "allowed_paths": ["src/auth/**", "tests/auth/**"],
    "forbidden_paths": [".env", "deploy/**", "ci/**"],
    "expected_artifacts": ["diff_patch", "self_test_report"],
    "acceptance_criteria": [
      "支持账号密码登录",
      "登录成功返回 token",
      "新增或更新测试用例"
    ],
    "risk_controls": [
      "不要 push",
      "不要执行数据库迁移",
      "不要修改 CI/CD"
    ],
    "review_required": true,
    "timeout_seconds": 1800
  },
  "request_id": "req_contract_001"
}
```

---

## 8. Result Review API

Runner 完成不等于任务完成。Result Review 用于判断 Runner 输出是否满足 Task Contract 和业务语义。

### 8.1 创建结果复核

```http
POST /api/tasks/{task_id}/result-reviews
```

请求：

```json
{
  "task_run_id": "run_001",
  "reviewer_agent": "DEV",
  "input_artifacts": [
    "artifact_task_contract",
    "artifact_diff_patch",
    "artifact_self_test_report"
  ]
}
```

### 8.2 提交结果复核

```http
POST /api/result-reviews/{review_id}/complete
```

请求：

```json
{
  "status": "passed",
  "contract_compliance": "passed",
  "semantic_compliance": "passed",
  "test_compliance": "passed",
  "summary": "实现满足 PRD 和设计要求，相关测试通过。",
  "required_changes": []
}
```

---

## 9. Review API

### 9.1 创建评审

```http
POST /api/projects/{project_id}/reviews
```

请求：

```json
{
  "type": "design_review",
  "phase": "DESIGN_REVIEW",
  "owner_agent": "PM",
  "participants": ["PM", "PDM", "DEV", "TEST", "SEC"],
  "required_participants": ["PDM", "DEV", "TEST"],
  "input_artifacts": ["artifact_design_draft"],
  "deadline": "2026-05-20T18:00:00+08:00"
}
```

### 9.2 查询项目评审

```http
GET /api/projects/{project_id}/reviews
```

### 9.3 查询评审详情

```http
GET /api/reviews/{review_id}
```

### 9.4 提交评审意见

```http
POST /api/reviews/{review_id}/comments
```

请求：

```json
{
  "reviewer_agent": "SEC",
  "comment_type": "issue",
  "status": "open",
  "severity": "major",
  "comment": "当前设计没有说明 token 过期策略",
  "required_change": "补充 token 过期、刷新和失效策略",
  "related_artifact": "artifact_design_draft"
}
```

### 9.5 解决评审意见

```http
POST /api/reviews/{review_id}/comments/{comment_id}/resolve
```

请求：

```json
{
  "resolved_by": "DEV",
  "resolution_note": "已在设计文档中补充 token 过期策略。"
}
```

### 9.6 完成评审

```http
POST /api/reviews/{review_id}/complete
```

评审完成不直接推进阶段，只提交 conclusion 作为 evidence。

请求：

```json
{
  "conclusion": "passed",
  "summary": "详细设计评审通过。",
  "evidence": ["comment_001", "artifact_design_final"]
}
```

---

## 10. Issue API

### 10.1 创建 Issue

```http
POST /api/projects/{project_id}/issues
```

请求：

```json
{
  "source": "test",
  "phase": "TEST_AND_SECURITY_VALIDATION",
  "title": "密码错误提示不符合 PRD",
  "description": "当前返回了具体账号不存在，PRD 要求统一错误提示。",
  "severity": "major",
  "priority": "normal",
  "assigned_agent": "DEV",
  "related_artifacts": ["artifact_test_report"],
  "source_task_run_id": "run_010"
}
```

### 10.2 查询 Issue 列表

```http
GET /api/projects/{project_id}/issues
```

### 10.3 查询 Issue 详情

```http
GET /api/issues/{issue_id}
```

### 10.4 分派 Issue

```http
POST /api/issues/{issue_id}/assign
```

### 10.5 开始修复

```http
POST /api/issues/{issue_id}/start-fix
```

### 10.6 标记已修复

```http
POST /api/issues/{issue_id}/mark-fixed
```

DEV 只能标记 fixed，不能直接 verify / close。

请求：

```json
{
  "fixed_by_task_id": "task_fix_001",
  "summary": "已统一登录失败错误提示。"
}
```

### 10.7 验证 Issue

```http
POST /api/issues/{issue_id}/verify
```

请求：

```json
{
  "verified_by": "TEST",
  "verification_task_id": "task_retest_001",
  "result": "passed"
}
```

### 10.8 重新打开 Issue

```http
POST /api/issues/{issue_id}/reopen
```

### 10.9 关闭 Issue

```http
POST /api/issues/{issue_id}/close
```

---

## 11. Artifact API

### 11.1 登记产物

```http
POST /api/projects/{project_id}/artifacts
```

请求：

```json
{
  "task_id": "task_001",
  "source_task_run_id": "run_001",
  "artifact_type": "design_final",
  "name": "detail-design-final.md",
  "path": "artifacts/proj_001/design/detail-design-final.md",
  "logical_path": "docs/design/detail-design-final.md",
  "version": "v1",
  "created_by": "DEV",
  "checksum": "sha256:xxx",
  "content_type": "text/markdown",
  "size_bytes": 12345,
  "is_final": true,
  "metadata": {
    "phase": "DESIGN_REVIEW"
  }
}
```

### 11.2 查询项目产物

```http
GET /api/projects/{project_id}/artifacts
```

可选查询参数：

```text
artifact_type
created_by
status
is_final
```

### 11.3 查询产物详情

```http
GET /api/artifacts/{artifact_id}
```

### 11.4 标记最终版

```http
POST /api/artifacts/{artifact_id}/mark-final
```

### 11.5 查询产物内容

```http
GET /api/artifacts/{artifact_id}/content
```

大文件只返回下载链接或摘要。

### 11.6 查询产物历史

```http
GET /api/artifacts/{artifact_id}/history
```

---

## 12. Confirmation API

Confirmation 统一承载 PRD 确认、设计确认、危险动作审批、验收确认和异常升级决策。

### 12.1 创建确认请求

```http
POST /api/projects/{project_id}/confirmations
```

请求：

```json
{
  "confirmation_type": "prd_approval",
  "target_type": "artifact",
  "target_id": "artifact_prd_final",
  "requested_by": "PM",
  "requested_to_user_id": "feishu_user_001",
  "options": [
    {"value": "approve", "label": "确认 PRD"},
    {"value": "reject", "label": "驳回 PRD"}
  ],
  "timeout_minutes": 30,
  "expires_at": "2026-05-20T18:00:00+08:00"
}
```

timeout_minutes 用于记录创建确认时的原始超时配置；expires_at 是根据创建时间和 timeout_minutes 计算出的绝对过期时间。两者同时保存，便于审计和后续策略分析。

### 12.2 查询项目确认请求

```http
GET /api/projects/{project_id}/confirmations
```

### 12.3 查询确认详情

```http
GET /api/confirmations/{confirmation_id}
```

### 12.4 提交确认决策

```http
POST /api/confirmations/{confirmation_id}/decide
```

请求：

```json
{
  "selected_option": "approve",
  "decision_comment": "需求确认，可以继续。"
}
```

### 12.5 确认超时

```http
POST /api/confirmations/{confirmation_id}/expire
```

---

## 13. Escalation API

### 13.1 查询项目异常升级

```http
GET /api/projects/{project_id}/escalations
```

### 13.2 提交升级决策

```http
POST /api/escalations/{escalation_id}/decision
```

请求：

```json
{
  "decision": "continue",
  "comment": "再自动修复一轮"
}
```

支持 decision：

```text
continue
redesign
manual
cancel
change_requirement
```

---

## 14. Agent Message API

Agent Message 是结构化协作记录，不是自由聊天通道。发送前必须经过 PhaseCommunicationGuard。

### 14.1 创建 Agent 消息

```http
POST /api/projects/{project_id}/agent-messages
```

请求：

```json
{
  "from_agent": "DEV",
  "to_agent": "PDM",
  "message_type": "requirement_question",
  "phase": "DEVELOPMENT",
  "title": "登录失败是否需要区分账号不存在和密码错误",
  "content": "PRD 当前只说明登录失败返回错误提示，未明确是否需要区分账号不存在和密码错误。",
  "related_artifacts": ["artifact_prd_final"],
  "requires_response": true
}
```

若被 PhaseCommunicationGuard 拦截，响应仍返回消息记录，但状态为 `rejected_by_guard`。

### 14.2 查询 Agent 消息

```http
GET /api/projects/{project_id}/agent-messages
```

可选查询参数：

```text
to_agent
from_agent
message_type
status
```

---

## 15. Feishu API

### 15.1 接收飞书事件

```http
POST /api/feishu/events
```

处理：

```text
普通消息；
slash command；
群聊消息；
用户 @ Bot。
```

### 15.2 接收飞书卡片交互

```http
POST /api/feishu/interactive
```

Feishu handler 只转换为：

```text
confirmation decision；
project command；
project status query。
```

安全要求：

```text
校验飞书签名、timestamp、app_id；
拒绝超过时间窗口的回调，防止重放；
使用 event_id / open_message_id 做幂等去重；
卡片交互只能转换为 confirmation decision 或 project command，不能直接写业务状态。
```

不直接推进 Workflow。

---

## 16. Runner Internal API

Runner Internal API 使用 `/internal` 前缀，只允许内部 Worker 调用。

安全要求：

```text
/internal/runner/* 不暴露给普通用户或飞书入口；
调用方必须通过服务端 token、mTLS 或内网网关鉴权；
heartbeat / complete / fail / cancel 必须校验 task_run 当前状态和调用方身份；
complete / fail 必须具备幂等保护，防止重复提交覆盖最终状态。
```

### 16.1 创建 Runner 执行

```http
POST /internal/runner/task-runs
```

请求：

```json
{
  "task_id": "task_001",
  "project_id": "proj_001",
  "runner_type": "claude_code_cli",
  "workspace_strategy": "git_worktree"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "task_run_id": "run_001",
    "status": "CREATED"
  },
  "request_id": "req_007"
}
```

### 16.2 查询 Runner 执行

```http
GET /internal/runner/task-runs/{task_run_id}
```

### 16.3 Runner 心跳

```http
POST /internal/runner/task-runs/{task_run_id}/heartbeat
```

请求：

```json
{
  "status": "RUNNING",
  "message": "Claude Code CLI is running",
  "output_size_bytes": 10240
}
```

### 16.4 Runner 完成

```http
POST /internal/runner/task-runs/{task_run_id}/complete
```

请求：

```json
{
  "status": "COMPLETED",
  "exit_code": 0,
  "summary": "完成登录接口实现并通过自测",
  "stdout_path": "runs/run_001/stdout.log",
  "stderr_path": "runs/run_001/stderr.log",
  "logs_path": "runs/run_001/execution.log",
  "diff_path": "runs/run_001/diff.patch",
  "output_manifest_path": "runs/run_001/output_manifest.json",
  "contract_check_result": {
    "status": "passed",
    "violations": []
  },
  "artifacts": [
    {
      "artifact_type": "diff_patch",
      "name": "login.diff",
      "path": "artifacts/run_001/login.diff",
      "checksum": "sha256:xxx",
      "content_type": "text/x-patch",
      "size_bytes": 12345
    }
  ]
}
```

Runner complete 的 artifacts 数组由内部服务在同一事务内登记到 artifacts 表。
如果任一 artifact 登记失败，complete 请求整体失败并保持 task_run 可重试或待人工处理。
Runner complete 只更新 task_run 和 artifact，不直接将 task 标记为 completed。
Task 是否完成由 Result Review 决定。

### 16.5 Runner 失败

```http
POST /internal/runner/task-runs/{task_run_id}/fail
```

请求：

```json
{
  "status": "FAILED",
  "error_code": "CONTRACT_VIOLATION",
  "error_message": "修改了 forbidden_paths: .env",
  "exit_code": 1,
  "security_policy_result": {
    "blocked": true,
    "reason": "forbidden path modified"
  }
}
```

### 16.6 取消 Runner 执行

```http
POST /internal/runner/task-runs/{task_run_id}/cancel
```

请求：

```json
{
  "reason": "用户暂停项目"
}
```

---

## 17. API 与状态机边界

```text
Controller：只做鉴权、解析、调用应用服务；
Application Service：创建任务、登记产物、提交评审、提交确认；
WorkflowEngine：检查 evidence，决定是否推进阶段；
Runner Worker：只执行 task_run，不决定业务阶段；
PM Agent：只汇总、建议、通知，不直接切状态。
```

---

## 18. 下一步

API v0.2 与主设计 v2.0 对齐后，下一步应同步更新 DDL，并进入实现计划拆分。
