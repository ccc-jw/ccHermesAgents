import json
import os
from typing import Any

import httpx

from app.core.config import Settings
from app.runners.types import RunnerResult, RunnerStatus, TaskContract
from app.runners.workspace_manager import RunnerWorkspace


class OpenAICompatibleRunner:
    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        self.settings = settings or Settings()
        self.transport = transport

    def run(
        self,
        workspace: RunnerWorkspace,
        contract: TaskContract,
        prompt: str,
        timeout_seconds: int,
    ) -> RunnerResult:
        prompt_path = workspace.input_dir / "task_prompt.md"
        contract_path = workspace.input_dir / "task_contract.json"
        stdout_path = workspace.logs_dir / "stdout.log"
        stderr_path = workspace.logs_dir / "stderr.log"
        execution_log_path = workspace.logs_dir / "execution.log"
        response_path = workspace.artifacts_dir / "response.md"
        prompt_path.write_text(prompt, encoding="utf-8")
        contract_path.write_text(contract.model_dump_json(indent=2), encoding="utf-8")

        api_key = os.environ.get(self.settings.runner_api_key_env)
        if not api_key:
            stderr_path.write_text("runner api key env is not configured", encoding="utf-8")
            execution_log_path.write_text("status=configuration_error", encoding="utf-8")
            return RunnerResult(
                status=RunnerStatus.FAILED,
                summary="Runner API key is not configured",
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                logs_path=str(execution_log_path),
                error_code="RUNNER_API_KEY_MISSING",
                error_message=(
                    f"Missing API key environment variable: {self.settings.runner_api_key_env}"
                ),
            )

        if not self.settings.runner_api_base_url or not self.settings.runner_model:
            stderr_path.write_text(
                "runner api base url or model is not configured",
                encoding="utf-8",
            )
            execution_log_path.write_text("status=configuration_error", encoding="utf-8")
            return RunnerResult(
                status=RunnerStatus.FAILED,
                summary="Runner API is not configured",
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                logs_path=str(execution_log_path),
                error_code="RUNNER_API_CONFIG_MISSING",
                error_message="Runner API base URL and model must be configured",
            )

        try:
            response = self._post_completion(api_key, contract, prompt, timeout_seconds)
            response.raise_for_status()
            response_json = response.json()
            output = self._extract_output(response_json)
        except json.JSONDecodeError as exc:
            raw_output = self._redact(response.text, api_key).strip()
            if raw_output and not self._looks_like_html(raw_output):
                output = raw_output
            else:
                safe_message = self._redact(str(exc), api_key)
                stderr_path.write_text(safe_message, encoding="utf-8")
                execution_log_path.write_text("status=parse_error", encoding="utf-8")
                return RunnerResult(
                    status=RunnerStatus.FAILED,
                    summary="Runner API returned an invalid response",
                    stdout_path=str(stdout_path),
                    stderr_path=str(stderr_path),
                    logs_path=str(execution_log_path),
                    error_code="RUNNER_API_PARSE_ERROR",
                    error_message=safe_message,
                )
        except httpx.TimeoutException:
            stderr_path.write_text("runner api timed out", encoding="utf-8")
            execution_log_path.write_text("status=timeout", encoding="utf-8")
            return RunnerResult(
                status=RunnerStatus.TIMEOUT,
                summary="Runner API timed out",
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                logs_path=str(execution_log_path),
                error_code="RUNNER_TIMEOUT",
                error_message="Runner API exceeded timeout",
            )
        except httpx.HTTPStatusError as exc:
            safe_message = self._redact(str(exc), api_key)
            stderr_path.write_text(safe_message, encoding="utf-8")
            execution_log_path.write_text(
                f"status=http_error\nstatus_code={exc.response.status_code}", encoding="utf-8"
            )
            return RunnerResult(
                status=RunnerStatus.FAILED,
                summary="Runner API returned an error",
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                logs_path=str(execution_log_path),
                error_code="RUNNER_API_HTTP_ERROR",
                error_message=safe_message,
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            safe_message = self._redact(str(exc), api_key)
            stderr_path.write_text(safe_message, encoding="utf-8")
            execution_log_path.write_text("status=api_error", encoding="utf-8")
            return RunnerResult(
                status=RunnerStatus.FAILED,
                summary="Runner API failed",
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                logs_path=str(execution_log_path),
                error_code="RUNNER_API_ERROR",
                error_message=safe_message,
            )

        response_path.write_text(output, encoding="utf-8")
        stdout_path.write_text(output, encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        execution_log_path.write_text("status=completed", encoding="utf-8")
        return RunnerResult(
            status=RunnerStatus.COMPLETED,
            exit_code=0,
            summary="Runner API completed",
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            logs_path=str(execution_log_path),
        )

    def _post_completion(
        self,
        api_key: str,
        contract: TaskContract,
        prompt: str,
        timeout_seconds: int,
    ) -> httpx.Response:
        base_url = self.settings.runner_api_base_url.rstrip("/")
        payload = {
            "model": self.settings.runner_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are executing a Hermes task contract. "
                        "Return the final task output only."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "prompt": prompt,
                            "contract": contract.model_dump(),
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        with httpx.Client(timeout=timeout_seconds, transport=self.transport) as client:
            return client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

    def _extract_output(self, response_json: dict[str, Any]) -> str:
        content = response_json["choices"][0]["message"]["content"]
        if isinstance(content, str):
            return content
        return json.dumps(content, ensure_ascii=False)

    def _looks_like_html(self, value: str) -> bool:
        normalized = value.lstrip().lower()
        return normalized.startswith("<!doctype html") or normalized.startswith("<html")

    def _redact(self, value: str, api_key: str) -> str:
        if not api_key:
            return value
        return value.replace(api_key, "[REDACTED]")
