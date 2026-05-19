from app.agents.prompt_builder import PromptBuilder
from app.runners.types import TaskContract


def test_prompt_builder_includes_role_and_contract():
    prompt = PromptBuilder().build(
        role="DEV",
        instruction="Implement login",
        contract=TaskContract(task_goal="login", role="DEV", phase="DEVELOPMENT"),
    )

    assert "Role: DEV" in prompt
    assert "Implement login" in prompt
    assert "task_goal" in prompt
