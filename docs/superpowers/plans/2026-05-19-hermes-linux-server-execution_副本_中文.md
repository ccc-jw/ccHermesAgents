# Hermes Agent Linux 服务器执行实现计划

> **给 Agent 工作器的说明：** 必需子技能：使用 `superpowers:subagent-driven-development`，推荐；或者使用 `superpowers:executing-plans`，按任务逐项实现本计划。步骤使用 checkbox，即 `- [ ]` 语法，用于跟踪进度。

**目标：** 准备一台 Linux 服务器，并基于现有的全阶段实现计划作为权威任务来源，从 Phase 0 执行到最终验证，完成 Hermes Agent 的实现与部署。

**架构：** 本计划是面向目标 Linux 环境的执行手册，不替代原始实现计划。Linux 服务器承载代码仓库、Python 虚拟环境、Redis 队列、SQLite MVP 数据库、存储目录、Claude Code CLI Runner、飞书回调服务以及运维脚本；每个阶段都通过测试优先的提交方式执行，并且在进入下一阶段前必须通过阶段门禁。

**技术栈：** Linux server、Git、Python 3.11+、venv、FastAPI、SQLAlchemy、Alembic、SQLite、Redis、Dramatiq、pytest、ruff、Claude Code CLI、systemd、Nginx 或 Caddy 反向代理、飞书回调 HTTPS 端点。

---

## 文件结构

本计划会创建或使用以下服务器端文件和目录。

```text
/opt/hermes-agent/
  ccHermesAgent/                         # Git 仓库工作目录
  venv/                                  # Python 虚拟环境
  storage/                               # 运行时存储根目录
    artifacts/
    runs/
    workspaces/
    logs/
  env/
    hermes.env                           # 运行时环境变量，权限 chmod 600
  scripts/
    phase-gate.sh                        # 阶段验证包装脚本
    run-api.sh                           # API 进程启动脚本
    run-worker.sh                        # Worker 进程启动脚本
    backup-sqlite.sh                     # SQLite 备份辅助脚本
  systemd/
    hermes-api.service
    hermes-worker.service
    hermes-patrol.service
```

作为权威实现输入使用的仓库文件：

```text
ccHermesAgent/docs/superpowers/plans/2026-05-18-hermes-all-phases-implementation.md
ccHermesAgent/hermes-agent-software-team-design-v1.5.md
ccHermesAgent/api-design-v0.1.md
ccHermesAgent/database-ddl-v0.1.md
```

---

## 服务器执行全局规则

- 在 Linux 服务器上执行实现，而不是在本地 macOS 工作树中执行。
- 每完成一个实现任务，创建一个 git commit；除非任务在绿色验证前被阻塞。
- 除非人工明确要求，否则自动化流程不要 push。
- 不要把 API key 存入 git、prompt artifacts、日志、数据库行或任务输出。
- 密钥只能存储在 `/opt/hermes-agent/env/hermes.env`，权限必须为 `600`。
- 进入下一阶段前，必须运行当前阶段的 phase gate。
- 如果某个验证命令无法运行，停止当前任务并记录阻塞原因，不要声称成功。

---

## Task L0：准备 Linux 服务器基础环境

**文件：**

- 创建：`/opt/hermes-agent/`
- 创建：`/opt/hermes-agent/storage/`
- 创建：`/opt/hermes-agent/env/`

### Step 1：创建服务用户和基础目录

在 Linux 服务器上运行：

```bash
sudo useradd --system --create-home --shell /bin/bash hermes || true
sudo mkdir -p /opt/hermes-agent/{storage/artifacts,storage/runs,storage/workspaces,storage/logs,env,scripts,systemd}
sudo chown -R hermes:hermes /opt/hermes-agent
sudo chmod 750 /opt/hermes-agent
sudo chmod 700 /opt/hermes-agent/env
```

预期结果：目录存在，并且归属用户为 `hermes`。

### Step 2：安装操作系统软件包

Ubuntu/Debian：

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates build-essential python3.11 python3.11-venv python3.11-dev redis-server sqlite3 nginx
```

预期结果：命令退出码为 0。

### Step 3：验证基础工具

运行：

```bash
git --version
python3.11 --version
redis-server --version
sqlite3 --version
```

预期结果：每个命令都输出版本号。

### Step 4：提交状态

本任务只准备服务器基础设施，因此不创建仓库 commit。

---

## Task L1：克隆仓库并创建 Python 环境

**文件：**

- 创建：`/opt/hermes-agent/ccHermesAgent/`
- 创建：`/opt/hermes-agent/venv/`

### Step 1：克隆或更新仓库

以 `hermes` 用户运行：

```bash
sudo -iu hermes bash -lc 'cd /opt/hermes-agent && git clone https://github.com/ccc-jw/ccHermesAgents ccHermesAgent'
```

如果仓库已经存在，则运行：

```bash
sudo -iu hermes bash -lc 'cd /opt/hermes-agent/ccHermesAgent && git fetch origin && git checkout main && git pull --ff-only origin main'
```

预期结果：仓库位于 `/opt/hermes-agent/ccHermesAgent`。

### Step 2：验证必要计划文件存在

运行：

```bash
sudo -iu hermes bash -lc 'test -f /opt/hermes-agent/ccHermesAgent/docs/superpowers/plans/2026-05-18-hermes-all-phases-implementation.md'
sudo -iu hermes bash -lc 'test -f /opt/hermes-agent/ccHermesAgent/hermes-agent-software-team-design-v1.5.md'
sudo -iu hermes bash -lc 'test -f /opt/hermes-agent/ccHermesAgent/api-design-v0.1.md'
sudo -iu hermes bash -lc 'test -f /opt/hermes-agent/ccHermesAgent/database-ddl-v0.1.md'
```

预期结果：所有命令退出码均为 0。

### Step 3：创建虚拟环境

运行：

```bash
sudo -iu hermes bash -lc 'python3.11 -m venv /opt/hermes-agent/venv'
sudo -iu hermes bash -lc '/opt/hermes-agent/venv/bin/python -m pip install --upgrade pip setuptools wheel'
```

预期结果：虚拟环境存在，并且 pip 升级成功。

### Step 4：在 Phase 0 Task 0.1 创建 `pyproject.toml` 后安装项目依赖

在 Phase 0 Task 0.1 创建 `pyproject.toml` 前，不要运行此步骤。

运行：

```bash
sudo -iu hermes bash -lc 'cd /opt/hermes-agent/ccHermesAgent && /opt/hermes-agent/venv/bin/pip install -e ".[dev]"'
```

预期结果：项目和开发依赖安装成功。

---

## Task L2：配置运行时密钥和本地服务

**文件：**

- 创建：`/opt/hermes-agent/env/hermes.env`

### Step 1：创建运行时环境变量文件

运行：

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

预期结果：文件存在，权限为 `600`。

### Step 2：手动填写密钥值

运行：

```bash
sudo -iu hermes nano /opt/hermes-agent/env/hermes.env
```

预期结果：飞书密钥和模型服务商环境变量已配置，并且没有提交到 git。

### Step 3：启动 Redis

运行：

```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
redis-cli ping
```

预期结果：输出 `PONG`。

### Step 4：验证 Claude Code CLI 可用

以 `hermes` 用户运行：

```bash
sudo -iu hermes bash -lc 'claude --version'
```

预期结果：Claude Code CLI 输出版本号。如果未安装，则按官方 Claude Code 服务器安装方式安装后重新运行此命令。

---

## Task L3：为每个实现任务建立执行循环

**文件：**

- 创建：`/opt/hermes-agent/scripts/phase-gate.sh`

### Step 1：创建阶段门禁脚本

运行：

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

预期结果：脚本存在且可执行。

### Step 2：对全阶段计划中的每个任务使用此循环

对于 `docs/superpowers/plans/2026-05-18-hermes-all-phases-implementation.md` 中的每个任务，执行以下流程：

```bash
cd /opt/hermes-agent/ccHermesAgent
git status --short
# 编写或更新该任务指定的测试。
/opt/hermes-agent/venv/bin/python -m pytest <task-specific-test> -v
# 确认测试因预期原因失败。
# 只实现该任务列出的文件。
/opt/hermes-agent/venv/bin/python -m pytest <task-specific-test> -v
# 确认测试通过。
/opt/hermes-agent/venv/bin/python -m ruff check <changed-python-paths>
git add <task-files>
git commit -m "<task commit message>"
```

预期结果：每个任务都以特定测试通过和一个 commit 结束。

### Step 3：每个阶段后运行 phase gate

运行：

```bash
sudo -iu hermes bash -lc '/opt/hermes-agent/scripts/phase-gate.sh'
```

预期结果：pytest 和 ruff 通过；git status 干净，或只包含有意未提交的、git 外部的运维文件。

---

# Phase 0 服务器执行：Runner 安全执行验证

权威实现任务位于：

```text
docs/superpowers/plans/2026-05-18-hermes-all-phases-implementation.md
```

Phase 0 需要在 Linux 上执行的任务：

```text
Task 0.1 Bootstrap Python Project
Task 0.2 Define Runner Domain Types
Task 0.3 Implement Workspace Manager
Task 0.4 Implement Contract Checker
Task 0.5 Implement Claude Code CLI Runner Process Wrapper
Task 0.6 Implement Artifact Collector
```

### Step 1：执行 Task 0.1

按全阶段实现计划中的 Task 0.1 精确步骤执行。

预期验证：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/unit/test_bootstrap.py -v
```

预期结果：2 个测试通过。

### Step 2：Task 0.1 创建 `pyproject.toml` 后安装依赖

运行：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/pip install -e ".[dev]"
```

预期结果：项目和开发依赖安装完成。

### Step 3：按顺序执行 Task 0.2 到 0.6

每个任务使用 Task L3 中的执行循环。

Task 0.6 后的预期验证：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/unit -v
/opt/hermes-agent/venv/bin/python -m pytest tests/integration -v
```

预期结果：所有 Phase 0 单元测试和集成测试通过。

### Step 4：运行受控 Runner 冒烟测试

运行：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python scripts/smoke_runner.py
```

预期结果：冒烟任务在 `/opt/hermes-agent/storage/workspaces` 中运行，在 `/opt/hermes-agent/storage/artifacts` 下产生产物，并且不会修改禁止路径。

### Step 5：提交 Phase 0 gate 记录

运行：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/scripts/phase-gate.sh
git log --oneline --max-count=10
```

预期结果：阶段门禁通过，最近 commit 包含所有 Phase 0 任务。

---

# Phase 1 服务器执行：最小控制面

Phase 1 需要在 Linux 上执行的任务：

```text
Task 1.1 Add SQLAlchemy Database Base and IDs
Task 1.2 Add Core SQLAlchemy Models
Task 1.3 Implement Project API
Task 1.4 Implement Task Start and Runner Worker Integration
```

### Step 1：执行 Task 1.1

按全阶段实现计划中的 Task 1.1 精确步骤执行。

预期验证：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/unit/core -v
```

预期结果：数据库基础和 ID 测试通过。

### Step 2：执行 Task 1.2

按全阶段实现计划中的 Task 1.2 精确步骤执行。

预期验证：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/unit/models/test_core_models.py -v
```

预期结果：核心模型测试通过。

### Step 3：执行 Task 1.3

按全阶段实现计划中的 Task 1.3 精确步骤执行。

预期验证：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/integration/test_project_api.py -v
```

预期结果：Project API 测试通过。

### Step 4：执行 Task 1.4

按全阶段实现计划中的 Task 1.4 精确步骤执行。

预期验证：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/integration/test_task_start_runner_integration.py -v
```

预期结果：任务启动会创建 task contract、task run、队列消息和 project event。

### Step 5：运行 Phase 1 API 冒烟测试

本地运行 API：

```bash
cd /opt/hermes-agent/ccHermesAgent
source /opt/hermes-agent/env/hermes.env
/opt/hermes-agent/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

在另一个 shell 中运行：

```bash
curl -s http://127.0.0.1:8000/api/projects/status || true
```

预期结果：服务器有响应；如果该 endpoint 尚不属于 Phase 1，API 进程仍应能成功启动。

### Step 6：运行 Phase 1 gate

运行：

```bash
sudo -iu hermes bash -lc '/opt/hermes-agent/scripts/phase-gate.sh'
```

预期结果：测试和 ruff 通过。

---

# Phase 2 服务器执行：本地最小闭环

Phase 2 需要在 Linux 上执行的任务：

```text
Task 2.1 Add Agent Registry and Role Prompts
Task 2.2 Add Prompt Builder and Agent Executor
Task 2.3 Add Issue Model and Service
```

### Step 1：执行 Task 2.1

按全阶段实现计划中的 Task 2.1 精确步骤执行。

预期验证：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/unit/agents/test_registry.py -v
```

预期结果：agent registry 加载 PDM、DEV、TEST 角色，并包含配置好的模型引用。

### Step 2：执行 Task 2.2

按全阶段实现计划中的 Task 2.2 精确步骤执行。

预期验证：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/unit/agents/test_prompt_builder.py tests/integration/test_agent_executor.py -v
```

预期结果：prompt builder 包含 task contract 和 artifact 引用，并且不会泄漏真实 API key。

### Step 3：执行 Task 2.3

按全阶段实现计划中的 Task 2.3 精确步骤执行。

预期验证：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/integration/test_issue_flow.py -v
```

预期结果：TEST 可以创建 issue，DEV 可以标记为 fixed，TEST 可以验证并关闭 issue。

### Step 4：运行本地闭环冒烟测试

运行：

```bash
cd /opt/hermes-agent/ccHermesAgent
source /opt/hermes-agent/env/hermes.env
/opt/hermes-agent/venv/bin/python scripts/smoke_runner.py --flow local-minimal-loop
```

预期结果：PDM → DEV → TEST → Issue → Fix → Verify 流程通过本地 API 或内部服务调用完成。

### Step 5：运行 Phase 2 gate

运行：

```bash
sudo -iu hermes bash -lc '/opt/hermes-agent/scripts/phase-gate.sh'
```

预期结果：测试和 ruff 通过。

---

# Phase 3 服务器执行：飞书 PM 入口

Phase 3 需要在 Linux 上执行的任务：

```text
Task 3.1 Implement Feishu Signature Verification
Task 3.2 Implement Feishu Event Router
Task 3.3 Implement Confirmation API
```

### Step 1：执行 Task 3.1

按全阶段实现计划中的 Task 3.1 精确步骤执行。

预期验证：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/unit/feishu/test_security.py -v
```

预期结果：有效飞书签名通过；过期时间戳和无效签名失败。

### Step 2：执行 Task 3.2

按全阶段实现计划中的 Task 3.2 精确步骤执行。

预期验证：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/integration/test_feishu_event_router.py -v
```

预期结果：普通消息、slash command、卡片交互只会路由到 command、confirmation、status 处理逻辑。

### Step 3：执行 Task 3.3

按全阶段实现计划中的 Task 3.3 精确步骤执行。

预期验证：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/integration/test_confirmation_api.py -v
```

预期结果：confirmation 的 create、decide、expire 行为具备幂等性。

### Step 4：为飞书回调配置反向代理

创建 Nginx site：

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

预期结果：Nginx 配置测试通过，反向代理重载成功。

### Step 5：运行飞书回调冒烟测试

运行：

```bash
curl -s -X POST http://127.0.0.1:8000/api/feishu/events \
  -H 'Content-Type: application/json' \
  -d '{"type":"url_verification","challenge":"test_challenge"}'
```

预期结果：响应符合 Phase 3 实现的飞书 URL 验证行为。

### Step 6：运行 Phase 3 gate

运行：

```bash
sudo -iu hermes bash -lc '/opt/hermes-agent/scripts/phase-gate.sh'
```

预期结果：测试和 ruff 通过。

---

# Phase 4 服务器执行：评审、巡检与升级

Phase 4 需要在 Linux 上执行的任务：

```text
Task 4.1 Implement Review API
Task 4.2 Implement Escalation API
Task 4.3 Implement PM Patrol Scanner
```

### Step 1：执行 Task 4.1

按全阶段实现计划中的 Task 4.1 精确步骤执行。

预期验证：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/integration/test_review_api.py -v
```

预期结果：review 的 create、comment、resolve、complete 生效，并且 review completion 只产生 evidence。

### Step 2：执行 Task 4.2

按全阶段实现计划中的 Task 4.2 精确步骤执行。

预期验证：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/integration/test_escalation_api.py -v
```

预期结果：escalation decision 支持 continue、redesign、manual、cancel、change_requirement。

### Step 3：执行 Task 4.3

按全阶段实现计划中的 Task 4.3 精确步骤执行。

预期验证：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/unit/patrol/test_scheduler.py tests/integration/test_pm_patrol.py -v
```

预期结果：PM patrol 能检测 blocked、stale、risky 项目，并创建状态摘要或升级事项。

### Step 4：实现存在后添加 patrol 服务

创建 systemd unit：

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

预期结果：unit 文件注册成功。在 `app.patrol.scheduler` 存在且 Phase 4 测试通过前，不要启动该服务。

### Step 5：运行 Phase 4 gate

运行：

```bash
sudo -iu hermes bash -lc '/opt/hermes-agent/scripts/phase-gate.sh'
```

预期结果：测试和 ruff 通过。

---

# Phase 5 服务器执行：质量增强与研究能力

Phase 5 需要在 Linux 上执行的任务：

```text
Task 5.1 Add Security Role and Security Report Artifact Flow
Task 5.2 Add Research Agent Roles and Report Contract
Task 5.3 Add Test Checklist Excel Generator
```

### Step 1：执行 Task 5.1

按全阶段实现计划中的 Task 5.1 精确步骤执行。

预期验证：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/integration/test_security_report_flow.py -v
```

预期结果：SEC 角色可以生成安全报告 artifact，并能阻止存在高风险发现的任务进入验收。

### Step 2：执行 Task 5.2

按全阶段实现计划中的 Task 5.2 精确步骤执行。

预期验证：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/integration/test_research_report_flow.py -v
```

预期结果：RES 和 Research Judge 角色可以生成并验证 research report contract。

### Step 3：执行 Task 5.3

按全阶段实现计划中的 Task 5.3 精确步骤执行。

预期验证：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest tests/unit/test_generate_test_checklist.py -v
```

预期结果：Markdown 测试用例可以转换为 Excel checklist，并且行与状态保持稳定。

### Step 4：运行完整质量门禁

运行：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest -q
/opt/hermes-agent/venv/bin/python -m ruff check .
```

预期结果：所有测试和 ruff 通过。

### Step 5：运行 Phase 5 gate

运行：

```bash
sudo -iu hermes bash -lc '/opt/hermes-agent/scripts/phase-gate.sh'
```

预期结果：阶段门禁通过。

---

## Task L4：配置长期运行服务

**文件：**

- 创建：`/etc/systemd/system/hermes-api.service`
- 创建：`/etc/systemd/system/hermes-worker.service`
- 修改：`/etc/systemd/system/hermes-patrol.service`

### Step 1：创建 API 服务

运行：

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

预期结果：API service 文件注册成功。

### Step 2：创建 worker 服务

运行：

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

预期结果：worker service 文件注册成功。

### Step 3：启用并启动服务

仅在所有 phase gate 都通过后运行：

```bash
sudo systemctl enable hermes-api hermes-worker hermes-patrol
sudo systemctl start hermes-api hermes-worker hermes-patrol
sudo systemctl status hermes-api --no-pager
sudo systemctl status hermes-worker --no-pager
sudo systemctl status hermes-patrol --no-pager
```

预期结果：所有服务处于 active；或者缺失的可选 patrol 服务在配置完成前被有意禁用。

### Step 4：检查服务日志

运行：

```bash
sudo journalctl -u hermes-api -n 100 --no-pager
sudo journalctl -u hermes-worker -n 100 --no-pager
sudo journalctl -u hermes-patrol -n 100 --no-pager
```

预期结果：没有打印密钥，也没有启动错误。

---

## Task L5：最终端到端验证

**文件：**

- 使用：`docs/superpowers/plans/2026-05-18-hermes-all-phases-implementation.md`

### Step 1：运行最终仓库检查

运行：

```bash
cd /opt/hermes-agent/ccHermesAgent
/opt/hermes-agent/venv/bin/python -m pytest -q
/opt/hermes-agent/venv/bin/python -m ruff check .
git status --short
```

预期结果：测试通过、ruff 通过、git status 干净。

### Step 2：运行 API 健康检查

运行：

```bash
curl -s http://127.0.0.1:8000/docs >/tmp/hermes-openapi.html
wc -c /tmp/hermes-openapi.html
```

预期结果：输出大小大于 0。

### Step 3：运行项目生命周期冒烟测试

运行：

```bash
cd /opt/hermes-agent/ccHermesAgent
source /opt/hermes-agent/env/hermes.env
/opt/hermes-agent/venv/bin/python scripts/smoke_runner.py --flow full-local-lifecycle
```

预期结果：冒烟测试创建项目、执行本地任务、记录 artifact、创建并处理 issue、运行 review/confirmation 流程，并到达 acceptance-ready 状态。

### Step 4：运行密钥泄漏扫描

运行：

```bash
cd /opt/hermes-agent/ccHermesAgent
! grep -R "HERMES_FEISHU_APP_SECRET=" -n app tests docs scripts || true
! grep -R "Authorization:" -n /opt/hermes-agent/storage/logs /opt/hermes-agent/storage/artifacts || true
```

预期结果：仓库、日志或 artifact 中不存在真实密钥值。

### Step 5：验证备份可用

创建备份脚本：

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

预期结果：创建了一个 SQLite 备份文件。

### Step 6：最终 commit 和 tag

在所有最终检查通过后运行：

```bash
cd /opt/hermes-agent/ccHermesAgent
git status --short
git tag hermes-phase0-5-local-mvp
```

预期结果：本地 tag 创建成功。只有在人工明确批准后才 push：

```bash
git push origin main --tags
```

---

## 执行顺序总结

按以下顺序执行任务：

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

中文含义：

```text
L0 准备 Linux 服务器基础环境
L1 克隆仓库并创建 Python 环境
L2 配置运行时密钥和本地服务
L3 为每个实现任务建立执行循环
Phase 0 Task 0.1 到 0.6
Phase 1 Task 1.1 到 1.4
Phase 2 Task 2.1 到 2.3
Phase 3 Task 3.1 到 3.3
Phase 4 Task 4.1 到 4.3
Phase 5 Task 5.1 到 5.3
L4 配置长期运行服务
L5 最终端到端验证
```

---

## 自审

- **规格覆盖：** 覆盖 Linux 初始化、仓库设置、Python 环境、密钥、Redis、Claude Code CLI 验证、Phase 0-5 的所有执行门禁、systemd 服务、最终冒烟验证、密钥扫描和备份。
- **占位符扫描：** 没有 TBD、TODO、未指定测试步骤或延期实现占位符。必须由服务器负责人提供的领域值已经明确命名，例如 `YOUR_DOMAIN_HERE`，以及私有 env 文件中的空飞书密钥值。
- **类型一致性：** 使用了与 `2026-05-18-hermes-all-phases-implementation.md` 相同的阶段名称和任务标识；运行时路径统一使用 `/opt/hermes-agent`。
