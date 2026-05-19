from app.agents.prompt_builder import PromptBuilder
from app.runners.types import TaskContract


class AgentExecutor:
    def __init__(self, prompt_builder: PromptBuilder | None = None):
        self.prompt_builder = prompt_builder or PromptBuilder()

    def build_task_prompt(self, role: str, instruction: str, contract: TaskContract) -> str:
        return self.prompt_builder.build(role=role, instruction=instruction, contract=contract)
