from app.runners.contract_checker import ContractChecker
from app.runners.types import TaskContract


def make_contract() -> TaskContract:
    return TaskContract(
        task_goal="edit docs",
        role="DEV",
        phase="DEVELOPMENT",
        allowed_paths=["src/**", "tests/**"],
        forbidden_paths=[".env", "deploy/**"],
        expected_artifacts=["diff_patch"],
    )


def test_contract_checker_allows_matching_paths():
    result = ContractChecker().check_changed_paths(make_contract(), ["src/auth.py", "tests/test_auth.py"])
    assert result.passed is True
    assert result.violations == []


def test_contract_checker_blocks_forbidden_paths():
    result = ContractChecker().check_changed_paths(make_contract(), [".env"])
    assert result.passed is False
    assert result.violations == ["forbidden path modified: .env"]


def test_contract_checker_blocks_outside_allowed_paths():
    result = ContractChecker().check_changed_paths(make_contract(), ["README.md"])
    assert result.passed is False
    assert result.violations == ["path outside allowed paths: README.md"]
