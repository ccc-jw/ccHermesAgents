from app.runners.types import RunnerStatus, TaskContract, RunnerResult


def test_task_contract_serializes_expected_fields():
    contract = TaskContract(
        task_goal="write docs",
        role="PDM",
        phase="REQUIREMENT_DRAFTING",
        input_artifacts=[],
        must_read_artifacts=["prd_draft"],
        allowed_paths=["docs/**"],
        forbidden_paths=[".env"],
        expected_artifacts=["prd_final"],
        acceptance_criteria=["PRD is written"],
        quality_gates=["markdown generated"],
        risk_controls=["do not push"],
        review_required=True,
        max_changed_files=5,
        timeout_seconds=600,
    )
    data = contract.model_dump()
    assert data["task_goal"] == "write docs"
    assert data["forbidden_paths"] == [".env"]


def test_runner_result_defaults_to_completed_status():
    result = RunnerResult(status=RunnerStatus.COMPLETED, exit_code=0, summary="ok")
    assert result.status is RunnerStatus.COMPLETED
    assert result.artifacts == []
