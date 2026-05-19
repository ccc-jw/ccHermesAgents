from fnmatch import fnmatch

from pydantic import BaseModel, Field

from app.runners.types import TaskContract


class ContractCheckResult(BaseModel):
    passed: bool
    violations: list[str] = Field(default_factory=list)


class ContractChecker:
    def check_changed_paths(
        self, contract: TaskContract, changed_paths: list[str]
    ) -> ContractCheckResult:
        violations: list[str] = []
        for path in changed_paths:
            if self._matches_any(path, contract.forbidden_paths):
                violations.append(f"forbidden path modified: {path}")
                continue
            if contract.allowed_paths and not self._matches_any(path, contract.allowed_paths):
                violations.append(f"path outside allowed paths: {path}")
        return ContractCheckResult(passed=not violations, violations=violations)

    def _matches_any(self, path: str, patterns: list[str]) -> bool:
        return any(fnmatch(path, pattern) for pattern in patterns)
