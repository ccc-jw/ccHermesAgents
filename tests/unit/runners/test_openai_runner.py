from pathlib import Path

import httpx

from app.core.config import Settings
from app.runners.openai_runner import OpenAICompatibleRunner
from app.runners.types import RunnerStatus, TaskContract
from app.runners.workspace_manager import WorkspaceManager


TEST_API_KEY = "sk-test-secret-value"


def build_runner(tmp_path: Path, monkeypatch, handler):
    monkeypatch.setenv("HERMES_RUNNER_API_KEY", TEST_API_KEY)
    transport = httpx.MockTransport(handler)
    settings = Settings(
        storage_root=str(tmp_path),
        runner_api_base_url="https://example.test/v1",
        runner_model="test-model",
    )
    workspace = WorkspaceManager(tmp_path).prepare_workspace("proj", "run")
    return OpenAICompatibleRunner(settings=settings, transport=transport), workspace


def test_openai_runner_writes_response_artifact(tmp_path: Path, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://example.test/v1/chat/completions"
        assert request.headers["authorization"] == f"Bearer {TEST_API_KEY}"
        payload = request.read().decode()
        assert TEST_API_KEY not in payload
        return httpx.Response(200, json={"choices": [{"message": {"content": "done"}}]})

    runner, workspace = build_runner(tmp_path, monkeypatch, handler)

    result = runner.run(
        workspace=workspace,
        contract=TaskContract(task_goal="x", role="DEV", phase="DEVELOPMENT"),
        prompt="hello",
        timeout_seconds=5,
    )

    assert result.status is RunnerStatus.COMPLETED
    assert result.exit_code == 0
    assert (workspace.artifacts_dir / "response.md").read_text(encoding="utf-8") == "done"
    assert Path(result.stdout_path).read_text(encoding="utf-8") == "done"
    assert TEST_API_KEY not in result.model_dump_json()
    assert TEST_API_KEY not in Path(result.logs_path).read_text(encoding="utf-8")


def test_openai_runner_accepts_plain_text_response(tmp_path: Path, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="plain done")

    runner, workspace = build_runner(tmp_path, monkeypatch, handler)

    result = runner.run(
        workspace=workspace,
        contract=TaskContract(task_goal="x", role="DEV", phase="DEVELOPMENT"),
        prompt="hello",
        timeout_seconds=5,
    )

    assert result.status is RunnerStatus.COMPLETED
    assert (workspace.artifacts_dir / "response.md").read_text(encoding="utf-8") == "plain done"


def test_openai_runner_rejects_html_response(tmp_path: Path, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<!doctype html><html></html>")

    runner, workspace = build_runner(tmp_path, monkeypatch, handler)

    result = runner.run(
        workspace=workspace,
        contract=TaskContract(task_goal="x", role="DEV", phase="DEVELOPMENT"),
        prompt="hello",
        timeout_seconds=5,
    )

    assert result.status is RunnerStatus.FAILED
    assert result.error_code == "RUNNER_API_PARSE_ERROR"
    assert not (workspace.artifacts_dir / "response.md").exists()


def test_openai_runner_handles_http_error_without_key_leak(tmp_path: Path, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "bad"}, request=request)

    runner, workspace = build_runner(tmp_path, monkeypatch, handler)

    result = runner.run(
        workspace=workspace,
        contract=TaskContract(task_goal="x", role="DEV", phase="DEVELOPMENT"),
        prompt="hello",
        timeout_seconds=5,
    )

    assert result.status is RunnerStatus.FAILED
    assert result.error_code == "RUNNER_API_HTTP_ERROR"
    assert TEST_API_KEY not in result.model_dump_json()
    assert TEST_API_KEY not in Path(result.stderr_path).read_text(encoding="utf-8")


def test_openai_runner_handles_timeout(tmp_path: Path, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("too slow", request=request)

    runner, workspace = build_runner(tmp_path, monkeypatch, handler)

    result = runner.run(
        workspace=workspace,
        contract=TaskContract(task_goal="x", role="DEV", phase="DEVELOPMENT"),
        prompt="hello",
        timeout_seconds=1,
    )

    assert result.status is RunnerStatus.TIMEOUT
    assert result.error_code == "RUNNER_TIMEOUT"


def test_openai_runner_handles_missing_api_key(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("HERMES_RUNNER_API_KEY", raising=False)
    settings = Settings(
        storage_root=str(tmp_path),
        runner_api_base_url="https://example.test/v1",
        runner_model="test-model",
    )
    workspace = WorkspaceManager(tmp_path).prepare_workspace("proj", "run")
    runner = OpenAICompatibleRunner(settings=settings)

    result = runner.run(
        workspace=workspace,
        contract=TaskContract(task_goal="x", role="DEV", phase="DEVELOPMENT"),
        prompt="hello",
        timeout_seconds=1,
    )

    assert result.status is RunnerStatus.FAILED
    assert result.error_code == "RUNNER_API_KEY_MISSING"
    assert "HERMES_RUNNER_API_KEY" in result.error_message
