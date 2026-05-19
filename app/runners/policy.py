from pydantic import BaseModel


class RunnerPolicy(BaseModel):
    blocked_commands: list[str]

    def allows(self, command: str) -> bool:
        return not any(command.startswith(blocked) for blocked in self.blocked_commands)
