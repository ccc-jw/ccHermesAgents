from pathlib import Path

from app.runners.workspace_manager import WorkspaceManager


def test_workspace_manager_creates_run_directories(tmp_path: Path):
    manager = WorkspaceManager(storage_root=tmp_path)
    workspace = manager.prepare_workspace(project_id="proj_1", task_run_id="run_1")

    assert workspace.root.exists()
    assert workspace.artifacts_dir.exists()
    assert workspace.logs_dir.exists()
    assert workspace.input_dir.exists()
    assert workspace.output_dir.exists()


def test_workspace_manager_rejects_path_escape(tmp_path: Path):
    manager = WorkspaceManager(storage_root=tmp_path)
    workspace = manager.prepare_workspace(project_id="proj_1", task_run_id="run_1")

    assert workspace.is_inside_workspace(workspace.root / "output" / "a.txt") is True
    assert workspace.is_inside_workspace(tmp_path.parent / "secret.txt") is False
