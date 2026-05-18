# Hermes Agent Linux Server Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare a Linux server and execute the Hermes Agent implementation from Phase 0 through final validation using the existing all-phases implementation plan as the authoritative task source.

**Architecture:** This plan is an execution runbook for the target Linux environment, not a replacement for the implementation plan. The Linux server hosts the repository, Python virtual environment, Redis queue, SQLite MVP database, storage directory, Claude Code CLI Runner, Feishu callback service, and operational scripts; each phase is executed with test-first commits and phase gates before moving forward.

**Tech Stack:** Linux server, Git, Python 3.11+, venv, FastAPI, SQLAlchemy, Alembic, SQLite, Redis, Dramatiq, pytest, ruff, Claude Code CLI, systemd, Nginx or Caddy reverse proxy, Feishu callback HTTPS endpoint.

---

## File Structure

This plan creates or uses the following server-side files and directories.

```text
/opt/hermes-agent/
  ccHermesAgent/                         # Git repository working tree
  venv/                                  # Python virtual environment
  storage/                               # Runtime storage root
    artifacts/
    runs/
    workspaces/
    logs/
  env/
    hermes.env                           # Runtime environment variables, chmod 600
  scripts/
    phase-gate.sh                        # Phase validation wrapper
    run-api.sh                           # API process launcher
    run-worker.sh                        # Worker process launcher
    backup-sqlite.sh                     # SQLite backup helper
  systemd/
    hermes-api.service
    hermes-worker.service
    hermes-patrol.service
```

Repository files used as authoritative implementation inputs:

```text
ccHermesAgent/docs/superpowers/plans/2026-05-18-hermes-all-phases-implementation.md
ccHermesAgent/hermes-agent-software-team-design-v1.5.md
ccHermesAgent/api-design-v0.1.md
ccHermesAgent/database-ddl-v0.1.md
```

---

## Global Rules for Server Execution

- Execute implementation on the Linux server, not on the local macOS worktree.
- Keep one git commit per completed implementation task unless a task is blocked before green verification.
- Do not push from automation unless the human explicitly requests it.
- Do not store API keys in git, prompt artifacts, logs, database rows, or task outputs.
- Store secrets only in `/opt/hermes-agent/env/hermes.env` with mode `600`.
- Run every phase gate before starting the next phase.
- If a verification command cannot run, stop that task and record the blocker instead of claiming success.

---

## Task L0: Provision Linux Server Base

**Files:**
- Create: `/opt/hermes-agent/`
- Create: `/opt/hermes-agent/storage/`
- Create: `/opt/hermes-agent/env/`

- [ ] **Step 1: Create service user and base directories**

Run on the Linux server:

```bash
sudo useradd --system --create-home --shell /bin/bash hermes || true
sudo mkdir -p /opt/hermes-agent/{storage/artifacts,storage/runs,storage/workspaces,storage/logs,env,scripts,systemd}
sudo chown -R hermes:hermes /opt/hermes-agent
sudo chmod 750 /opt/hermes-agent
sudo chmod 700 /opt/hermes-agent/env
```

Expected: directories exist and are owned by `hermes`.

- [ ] **Step 2: Install OS packages**

For Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates build-essential python3.11 python3.11-venv python3.11-dev redis-server sqlite3 nginx
```

Expected: command exits 0.

- [ ] **Step 3: Verify base tools**

Run:

```bash
git --version
python3.11 --version
redis-server --version
sqlite3 --version
```

Expected: each command prints a version.

- [ ] **Step 4: Commit status**

No repository commit is created in this task because it only provisions server infrastructure.

---

## Task L1: Clone Repository and Create Python Environment

**Files:**
- Create: `/opt/hermes-agent/ccHermesAgent/`
- Create: `/opt/hermes-agent/venv/`

- [ ] **Step 1: Clone or update repository**

Run as `hermes`:

```bash
sudo -iu hermes bash -lc 'cd /opt/hermes-agent && git clone https://github.com/ccc-jw/ccHermesAgents ccHermesAgent'
```

If the repository already exists, run:

```bash
sudo -iu hermes bash -lc 'cd /opt/hermes-agent/ccHermesAgent && git fetch origin && git checkout main && git pull --ff-only origin main'
```

Expected: repository is present at `/opt/hermes-agent/ccHermesAgent`.

- [ ] **Step 2: Verify required plan files exist**

Run:

```bash
sudo -iu hermes bash -lc 'test -f /opt/hermes-agent/ccHermesAgent/docs/superpowers/plans/2026-05-18-hermes-all-phases-implementation.md'
sudo -iu hermes bash -lc 'test -f /opt/hermes-agent/ccHermesAgent/hermes-agent-software-team-design-v1.5.md'
sudo -iu hermes bash -lc 'test -f /opt/hermes-agent/ccHermesAgent/api-design-v0.1.md'
sudo -iu hermes bash -lc 'test -f /opt/hermes-agent/ccHermesAgent/database-ddl-v0.1.md'
```

Expected: all commands exit 0.

- [ ] **Step 3: Create virtual environment**

Run:

```bash
sudo -iu hermes bash -lc 'python3.11 -m venv /opt/hermes-agent/venv'
sudo -iu hermes bash -lc '/opt/hermes-agent/venv/bin/python -m pip install --upgrade pip setuptools wheel'
```

Expected: virtual environment exists and pip upgrade exits 0.

- [ ] **Step 4: Install project dependencies after Phase 0 Task 0.1 creates `pyproject.toml`**

Do not run this step until Phase 0 Task 0.1 has created `pyproject.toml`.

Run:

```bash
sudo -iu hermes bash -lc 'cd /opt/hermes-agent/ccHermesAgent && /opt/hermes-agent/venv/bin/pip install -e ".[dev]"'
```

Expected: package installs with dev dependencies.

---

## Task L2: Configure Runtime Secrets and Local Services

**Files:**
- Create: `/opt/hermes-agent/env/hermes.env`

- [ ] **Step 1: Create runtime environment file**

Run:

```bash
sudo -iu hermes bash -lc 'cat > /opt/hermes-agent/env/hermes.env <<EOF
HERMES_APP_NAME=Hermes Agent
HERMES_DATABASE_URL=sqlite:////opt/hermes-agent/storage/hermes.db
HERMES_STORAGE_ROOT=/opt/hermes-agent/storage
HERMES_REDIS_URL=redis://127.0.0.1:6379/0
HERMES_RUNNER_TIMEOUT_SECONDS=1800
HERMES_RUNNER_MAX_OUTPUT_BYTES=5000000
HERMES_FEISHU_APP_ID=
HERMES_FEISHU_APP_SECRET_ENV=HERMES_FEISHU_APP_SECRET
HERMES_FEISHU_VERIFICATION_TOKEN_ENV=HERMES_FEISHU_VERIFICATION_TOKEN
HERMES_FEISHU_ENCRYPT_KEY_ENV=HERMES_FEISHU_ENCRYPT_KEY
HERMES_FEISHU_APP_SECRET=
HERMES_FEISHU_VERIFICATION_TOKEN=
HERMES_FEISHU_ENCRYPT_KEY=
EOF
chmod 600 /opt/hermes-agent/env/hermes.env'
```

Expected: file exists with mode `600`.

- [ ] **Step 2: Fill secret values manually**

Run:

```bash
sudo -iu hermes nano /opt/hermes-agent/env/hermes.env
```

Expected: Feishu secrets and model provider environment variables are set without committing them to git.

- [ ] **Step 3: Start Redis**

Run:

```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
redis-cli ping
```

Expected: `PONG`.

- [ ] **Step 4: Verify Claude Code CLI availability**

Run as `hermes`:

```bash
sudo -iu hermes bash -lc 'claude --version'
```

Expected: Claude Code CLI prints a version. If it is not installed, install it following the official Claude Code installation path for the server, then rerun this command.

---

## Task L3: Establish Execution Loop for Every Implementation Task

**Files:**
- Create: `/opt/hermes-agent/scripts/phase-gate.sh`

- [ ] **Step 1: Create phase gate script**

Run:

```bash
sudo -iu hermes bash -lc 'cat > /opt/hermes-agent/scripts/phase-gate.sh <<"EOF"
#!/usr/bin/env bash
set -euo pipefail
cd /opt/hermes-agent/ccHermesAgent
source /opt/hermes-agent/env/hermes.env
/opt/hermes-agent/venv/bin/python -m pytest -q
/opt/hermes-agent/venv/bin/python -m ruff check .
git status --short
EOF
chmod 750 /opt/hermes-agent/scripts/phase-gate.sh'
```

Expected: script exists and is executable.

- [ ] **Step 2: Use this loop for each task in the all-phases plan**

For every task in `docs/superpowers/plans/2026-05-18-hermes-all-phases-implementation.md`, run the following sequence:

```bash
cd /opt/hermes-agent/ccHermesAgent
git status --short
# Write or update the test specified by the task.
/opt/hermes-agent/venv/bin/python -m pytest <task-specific-test> -v
# Confirm the test fails for the expected reason.
# Implement only the files listed in the task.
/opt/hermes-agent/venv/bin/python -m pytest <task-specific-test> -v
# Confirm the test passes.
/opt/hermes-agent/venv/bin/python -m ruff check <changed-python-paths>
git add <task-files>
git commit -m "<task commit message>"
```

Expected: each task ends with a green task-specific test and a commit.

- [ ] **Step 3: Run phase gate after each phase**

Run:

```bash
sudo -iu hermes bash -lc '/opt/hermes-agent/scripts/phase-gate.sh'
```

Expected: pytest and ruff pass; git status is clean or contains only intentionally uncommitted operational files outside git.

---

## Phase 0 Server Execution: Runner 安全执行验证

Authoritative implementation tasks are in:

```text
docs/superpowers/plans/2026-05-18-hermes-all-phases-implementation.md
```

Phase 0 tasks to execute on Linux:

```text
Task 0.1 Bootstrap Python Project
Task 0.2 Define Runner Domain Types
Task 0.3 Implement Workspace Manager
Task 0.4 Implement Contract Checker
Task 0.5 Implement Claude Code CLI Runner Process Wrapper
Task 0.6 Implement Artifact Collector
```

- [ ] **Step 1: Execute Task 0.1**

Run the exact Task 0.1 steps from the all-phases implementation plan.

Expected verification:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/unit/test_bootstrap.py -v
```

Expected: 2 tests pass.

- [ ] **Step 2: Install dependencies after Task 0.1 creates `pyproject.toml`**

Run:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/pip install -e ".[dev]"
```

Expected: project and dev dependencies install.

- [ ] **Step 3: Execute Tasks 0.2 through 0.6 in order**

Use the execution loop from Task L3 for each task.

Expected verification after Task 0.6:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/unit -v
/opt/hermes-agent/venv/bin/python -m pytest tests/integration -v
```

Expected: all Phase 0 unit and integration tests pass.

- [ ] **Step 4: Run controlled Runner smoke test**

Run:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python scripts/smoke_runner.py
```

Expected: smoke task runs in `/opt/hermes-agent/storage/workspaces`, produces artifacts under `/opt/hermes-agent/storage/artifacts`, and does not modify forbidden paths.

- [ ] **Step 5: Commit Phase 0 gate record**

Run:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/scripts/phase-gate.sh
git log --oneline --max-count=10
```

Expected: phase gate passes and recent commits include all Phase 0 tasks.

---

## Phase 1 Server Execution: 最小控制面

Phase 1 tasks to execute on Linux:

```text
Task 1.1 Add SQLAlchemy Database Base and IDs
Task 1.2 Add Core SQLAlchemy Models
Task 1.3 Implement Project API
Task 1.4 Implement Task Start and Runner Worker Integration
```

- [ ] **Step 1: Execute Task 1.1**

Run the exact Task 1.1 steps from the all-phases implementation plan.

Expected verification:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/unit/core -v
```

Expected: database base and ID tests pass.

- [ ] **Step 2: Execute Task 1.2**

Run the exact Task 1.2 steps from the all-phases implementation plan.

Expected verification:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/unit/models/test_core_models.py -v
```

Expected: core model tests pass.

- [ ] **Step 3: Execute Task 1.3**

Run the exact Task 1.3 steps from the all-phases implementation plan.

Expected verification:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/integration/test_project_api.py -v
```

Expected: Project API tests pass.

- [ ] **Step 4: Execute Task 1.4**

Run the exact Task 1.4 steps from the all-phases implementation plan.

Expected verification:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/integration/test_task_start_runner_integration.py -v
```

Expected: task start creates task contract, task run, queue message, and project event.

- [ ] **Step 5: Run Phase 1 API smoke test**

Run API locally:

```bash
cd /opt/hermes-agent/ccHermesAgent
source /opt/hermes-agent/env/hermes.env
/opt/hermes-agent/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another shell, run:

```bash
curl -s http://127.0.0.1:8000/api/projects/status || true
```

Expected: server responds; if the endpoint is not part of Phase 1 yet, API process still starts successfully.

- [ ] **Step 6: Run Phase 1 gate**

Run:

```bash
sudo -iu hermes bash -lc '/opt/hermes-agent/scripts/phase-gate.sh'
```

Expected: tests and ruff pass.

---

## Phase 2 Server Execution: 本地最小闭环

Phase 2 tasks to execute on Linux:

```text
Task 2.1 Add Agent Registry and Role Prompts
Task 2.2 Add Prompt Builder and Agent Executor
Task 2.3 Add Issue Model and Service
```

- [ ] **Step 1: Execute Task 2.1**

Run the exact Task 2.1 steps from the all-phases implementation plan.

Expected verification:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/unit/agents/test_registry.py -v
```

Expected: agent registry loads PDM, DEV, TEST roles with configured model references.

- [ ] **Step 2: Execute Task 2.2**

Run the exact Task 2.2 steps from the all-phases implementation plan.

Expected verification:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/unit/agents/test_prompt_builder.py tests/integration/test_agent_executor.py -v
```

Expected: prompt builder includes task contract and artifact references without leaking real API keys.

- [ ] **Step 3: Execute Task 2.3**

Run the exact Task 2.3 steps from the all-phases implementation plan.

Expected verification:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/integration/test_issue_flow.py -v
```

Expected: TEST can create an issue, DEV can mark fixed, TEST can verify and close.

- [ ] **Step 4: Run local closed-loop smoke**

Run:

```bash
cd /opt/hermes-agent/ccHermesAgent
source /opt/hermes-agent/env/hermes.env
/opt/hermes-agent/venv/bin/python scripts/smoke_runner.py --flow local-minimal-loop
```

Expected: PDM → DEV → TEST → Issue → Fix → Verify flow completes using local API or internal service calls.

- [ ] **Step 5: Run Phase 2 gate**

Run:

```bash
sudo -iu hermes bash -lc '/opt/hermes-agent/scripts/phase-gate.sh'
```

Expected: tests and ruff pass.

---

## Phase 3 Server Execution: 飞书 PM 入口

Phase 3 tasks to execute on Linux:

```text
Task 3.1 Implement Feishu Signature Verification
Task 3.2 Implement Feishu Event Router
Task 3.3 Implement Confirmation API
```

- [ ] **Step 1: Execute Task 3.1**

Run the exact Task 3.1 steps from the all-phases implementation plan.

Expected verification:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/unit/feishu/test_security.py -v
```

Expected: valid Feishu signatures pass; stale timestamps and invalid signatures fail.

- [ ] **Step 2: Execute Task 3.2**

Run the exact Task 3.2 steps from the all-phases implementation plan.

Expected verification:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/integration/test_feishu_event_router.py -v
```

Expected: ordinary message, slash command, and card interaction route to command/confirmation/status handling only.

- [ ] **Step 3: Execute Task 3.3**

Run the exact Task 3.3 steps from the all-phases implementation plan.

Expected verification:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/integration/test_confirmation_api.py -v
```

Expected: confirmation create/decide/expire works idempotently.

- [ ] **Step 4: Configure reverse proxy for Feishu callback**

Create Nginx site:

```bash
sudo tee /etc/nginx/sites-available/hermes-agent >/dev/null <<'EOF'
server {
    listen 80;
    server_name YOUR_DOMAIN_HERE;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
sudo ln -sf /etc/nginx/sites-available/hermes-agent /etc/nginx/sites-enabled/hermes-agent
sudo nginx -t
sudo systemctl reload nginx
```

Expected: Nginx config test passes and reverse proxy reloads.

- [ ] **Step 5: Run Feishu callback smoke test**

Run:

```bash
curl -s -X POST http://127.0.0.1:8000/api/feishu/events \
  -H 'Content-Type: application/json' \
  -d '{"type":"url_verification","challenge":"test_challenge"}'
```

Expected: response follows Feishu verification behavior implemented by Phase 3.

- [ ] **Step 6: Run Phase 3 gate**

Run:

```bash
sudo -iu hermes bash -lc '/opt/hermes-agent/scripts/phase-gate.sh'
```

Expected: tests and ruff pass.

---

## Phase 4 Server Execution: 评审、巡检与升级

Phase 4 tasks to execute on Linux:

```text
Task 4.1 Implement Review API
Task 4.2 Implement Escalation API
Task 4.3 Implement PM Patrol Scanner
```

- [ ] **Step 1: Execute Task 4.1**

Run the exact Task 4.1 steps from the all-phases implementation plan.

Expected verification:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/integration/test_review_api.py -v
```

Expected: review create/comment/resolve/complete works and review completion only emits evidence.

- [ ] **Step 2: Execute Task 4.2**

Run the exact Task 4.2 steps from the all-phases implementation plan.

Expected verification:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/integration/test_escalation_api.py -v
```

Expected: escalation decisions support continue/redesign/manual/cancel/change_requirement.

- [ ] **Step 3: Execute Task 4.3**

Run the exact Task 4.3 steps from the all-phases implementation plan.

Expected verification:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/unit/patrol/test_scheduler.py tests/integration/test_pm_patrol.py -v
```

Expected: PM patrol detects blocked/stale/risky projects and creates status summaries or escalations.

- [ ] **Step 4: Add patrol service after implementation exists**

Create systemd unit:

```bash
sudo tee /etc/systemd/system/hermes-patrol.service >/dev/null <<'EOF'
[Unit]
Description=Hermes Agent PM Patrol
After=network.target redis-server.service

[Service]
User=hermes
WorkingDirectory=/opt/hermes-agent/ccHermesAgent
EnvironmentFile=/opt/hermes-agent/env/hermes.env
ExecStart=/opt/hermes-agent/venv/bin/python -m app.patrol.scheduler
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
```

Expected: unit file is registered. Do not start it until `app.patrol.scheduler` exists and Phase 4 tests pass.

- [ ] **Step 5: Run Phase 4 gate**

Run:

```bash
sudo -iu hermes bash -lc '/opt/hermes-agent/scripts/phase-gate.sh'
```

Expected: tests and ruff pass.

---

## Phase 5 Server Execution: 质量增强与研究能力

Phase 5 tasks to execute on Linux:

```text
Task 5.1 Add Security Role and Security Report Artifact Flow
Task 5.2 Add Research Agent Roles and Report Contract
Task 5.3 Add Test Checklist Excel Generator
```

- [ ] **Step 1: Execute Task 5.1**

Run the exact Task 5.1 steps from the all-phases implementation plan.

Expected verification:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/integration/test_security_report_flow.py -v
```

Expected: SEC role can produce security report artifacts and block risky findings from acceptance.

- [ ] **Step 2: Execute Task 5.2**

Run the exact Task 5.2 steps from the all-phases implementation plan.

Expected verification:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/integration/test_research_report_flow.py -v
```

Expected: RES and Research Judge roles produce and validate research report contracts.

- [ ] **Step 3: Execute Task 5.3**

Run the exact Task 5.3 steps from the all-phases implementation plan.

Expected verification:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/unit/test_generate_test_checklist.py -v
```

Expected: Markdown test cases convert to Excel checklist with stable rows and statuses.

- [ ] **Step 4: Run full quality gate**

Run:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest -q
/opt/hermes-agent/venv/bin/python -m ruff check .
```

Expected: all tests and ruff pass.

- [ ] **Step 5: Run Phase 5 gate**

Run:

```bash
sudo -iu hermes bash -lc '/opt/hermes-agent/scripts/phase-gate.sh'
```

Expected: phase gate passes.

---

## Task L4: Configure Long-Running Services

**Files:**
- Create: `/etc/systemd/system/hermes-api.service`
- Create: `/etc/systemd/system/hermes-worker.service`
- Modify: `/etc/systemd/system/hermes-patrol.service`

- [ ] **Step 1: Create API service**

Run:

```bash
sudo tee /etc/systemd/system/hermes-api.service >/dev/null <<'EOF'
[Unit]
Description=Hermes Agent API
After=network.target redis-server.service

[Service]
User=hermes
WorkingDirectory=/opt/hermes-agent/ccHermesAgent
EnvironmentFile=/opt/hermes-agent/env/hermes.env
ExecStart=/opt/hermes-agent/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
```

Expected: API service file is registered.

- [ ] **Step 2: Create worker service**

Run:

```bash
sudo tee /etc/systemd/system/hermes-worker.service >/dev/null <<'EOF'
[Unit]
Description=Hermes Agent Runner Worker
After=network.target redis-server.service hermes-api.service

[Service]
User=hermes
WorkingDirectory=/opt/hermes-agent/ccHermesAgent
EnvironmentFile=/opt/hermes-agent/env/hermes.env
ExecStart=/opt/hermes-agent/venv/bin/python -m app.runners.worker
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
```

Expected: worker service file is registered.

- [ ] **Step 3: Enable and start services**

Run only after all phase gates pass:

```bash
sudo systemctl enable hermes-api hermes-worker hermes-patrol
sudo systemctl start hermes-api hermes-worker hermes-patrol
sudo systemctl status hermes-api --no-pager
sudo systemctl status hermes-worker --no-pager
sudo systemctl status hermes-patrol --no-pager
```

Expected: all services are active or the missing optional patrol service is intentionally disabled until configured.

- [ ] **Step 4: Check service logs**

Run:

```bash
sudo journalctl -u hermes-api -n 100 --no-pager
sudo journalctl -u hermes-worker -n 100 --no-pager
sudo journalctl -u hermes-patrol -n 100 --no-pager
```

Expected: no secrets are printed and no startup errors appear.

---

## Task L5: Final End-to-End Validation

**Files:**
- Use: `docs/superpowers/plans/2026-05-18-hermes-all-phases-implementation.md`

- [ ] **Step 1: Run final repository checks**

Run:

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest -q
/opt/hermes-agent/venv/bin/python -m ruff check .
git status --short
```

Expected: tests pass, ruff passes, git status is clean.

- [ ] **Step 2: Run API health check**

Run:

```bash
curl -s http://127.0.0.1:8000/docs >/tmp/hermes-openapi.html
wc -c /tmp/hermes-openapi.html
```

Expected: output size is greater than 0.

- [ ] **Step 3: Run project lifecycle smoke test**

Run:

```bash
cd /opt/hermes-agent/ccHermesAgent
source /opt/hermes-agent/env/hermes.env
/opt/hermes-agent/venv/bin/python scripts/smoke_runner.py --flow full-local-lifecycle
```

Expected: smoke test creates a project, runs local task execution, records artifacts, creates/handles issues, runs review/confirmation flow, and reaches acceptance-ready state.

- [ ] **Step 4: Run secret leakage scan**

Run:

```bash
cd /opt/hermes-agent/ccHermesAgent
! grep -R "HERMES_FEISHU_APP_SECRET=" -n app tests docs scripts || true
! grep -R "Authorization:" -n /opt/hermes-agent/storage/logs /opt/hermes-agent/storage/artifacts || true
```

Expected: no real secret values are present in repository, logs, or artifacts.

- [ ] **Step 5: Verify backup works**

Create backup script:

```bash
sudo -iu hermes bash -lc 'cat > /opt/hermes-agent/scripts/backup-sqlite.sh <<"EOF"
#!/usr/bin/env bash
set -euo pipefail
BACKUP_DIR=/opt/hermes-agent/storage/backups
mkdir -p "$BACKUP_DIR"
sqlite3 /opt/hermes-agent/storage/hermes.db ".backup $BACKUP_DIR/hermes-$(date +%Y%m%d-%H%M%S).db"
find "$BACKUP_DIR" -type f -name "hermes-*.db" -mtime +14 -delete
EOF
chmod 750 /opt/hermes-agent/scripts/backup-sqlite.sh
/opt/hermes-agent/scripts/backup-sqlite.sh
ls -lh /opt/hermes-agent/storage/backups'
```

Expected: a SQLite backup file is created.

- [ ] **Step 6: Final commit and tag**

Run after all final checks pass:

```bash
cd /opt/hermes-agent/ccHermesAgent
git status --short
git tag hermes-phase0-5-local-mvp
```

Expected: tag is created locally. Push only after explicit human approval:

```bash
git push origin main --tags
```

---

## Execution Order Summary

Run tasks in this order:

```text
L0 Provision Linux Server Base
L1 Clone Repository and Create Python Environment
L2 Configure Runtime Secrets and Local Services
L3 Establish Execution Loop for Every Implementation Task
Phase 0 Task 0.1 through 0.6
Phase 1 Task 1.1 through 1.4
Phase 2 Task 2.1 through 2.3
Phase 3 Task 3.1 through 3.3
Phase 4 Task 4.1 through 4.3
Phase 5 Task 5.1 through 5.3
L4 Configure Long-Running Services
L5 Final End-to-End Validation
```

---

## Self-Review

- Spec coverage: Covers Linux provisioning, repository setup, Python environment, secrets, Redis, Claude Code CLI verification, all Phase 0-5 execution gates, systemd services, final smoke validation, secret scan, and backup.
- Placeholder scan: No TBD, TODO, unspecified test steps, or deferred implementation placeholders are present. Domain-specific values that must be supplied by the server owner are named explicitly, such as `YOUR_DOMAIN_HERE` and empty Feishu secret values in the private env file.
- Type consistency: Uses the same phase names and task identifiers as `2026-05-18-hermes-all-phases-implementation.md`; runtime paths consistently use `/opt/hermes-agent`.
