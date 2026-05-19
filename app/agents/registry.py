from pathlib import Path

import yaml
from pydantic import BaseModel


class AgentConfig(BaseModel):
    name: str
    role: str
    executor_type: str = "claude_code_cli"


class AgentRegistry:
    def __init__(self, roles_dir: Path | str):
        self.roles_dir = Path(roles_dir)

    def get(self, name: str) -> AgentConfig:
        for path in self.roles_dir.glob("*.yaml"):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if data["name"] == name:
                return AgentConfig(**data)
        raise KeyError(name)
