from pathlib import Path

from app.runners.artifact_collector import ArtifactCollector
from app.runners.workspace_manager import WorkspaceManager


def test_artifact_collector_hashes_files(tmp_path: Path):
    workspace = WorkspaceManager(tmp_path).prepare_workspace("proj", "run")
    artifact_file = workspace.artifacts_dir / "report.md"
    artifact_file.write_text("hello", encoding="utf-8")

    artifacts = ArtifactCollector().collect(workspace)

    assert len(artifacts) == 1
    assert artifacts[0].name == "report.md"
    assert artifacts[0].artifact_type == "runner_artifact"
    assert artifacts[0].checksum.startswith("sha256:")
    assert artifacts[0].size_bytes == 5
