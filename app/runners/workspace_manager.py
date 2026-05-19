from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunnerWorkspace:
    root: Path
    input_dir: Path
    output_dir: Path
    artifacts_dir: Path
    logs_dir: Path

    def is_inside_workspace(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.root.resolve())
        except ValueError:
            return False
        return True


class WorkspaceManager:
    def __init__(self, storage_root: Path | str):
        self.storage_root = Path(storage_root)

    def prepare_workspace(self, project_id: str, task_run_id: str) -> RunnerWorkspace:
        root = self.storage_root / "runs" / project_id / task_run_id
        workspace = RunnerWorkspace(
            root=root,
            input_dir=root / "input",
            output_dir=root / "output",
            artifacts_dir=root / "artifacts",
            logs_dir=root / "logs",
        )
        for directory in [
            workspace.root,
            workspace.input_dir,
            workspace.output_dir,
            workspace.artifacts_dir,
            workspace.logs_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)
        return workspace
