from app.runners.types import TaskContract


class PromptBuilder:
    def build(self, role: str, instruction: str, contract: TaskContract) -> str:
        return "\n".join(
            [
                f"Role: {role}",
                "Instruction:",
                instruction,
                "Task Contract:",
                contract.model_dump_json(indent=2),
            ]
        )
