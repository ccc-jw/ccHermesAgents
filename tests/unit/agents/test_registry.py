from pathlib import Path

from app.agents.registry import AgentRegistry


def test_agent_registry_loads_role_yaml(tmp_path: Path):
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    (roles_dir / "dev.yaml").write_text(
        "name: DEV\nrole: developer\nexecutor_type: claude_code_cli\n", encoding="utf-8"
    )

    registry = AgentRegistry(roles_dir=roles_dir)
    agent = registry.get("DEV")

    assert agent.name == "DEV"
    assert agent.role == "developer"
    assert agent.executor_type == "claude_code_cli"
