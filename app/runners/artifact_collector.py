import hashlib
from pathlib import Path

from app.runners.types import RunnerArtifact
from app.runners.workspace_manager import RunnerWorkspace


class ArtifactCollector:
    def collect(self, workspace: RunnerWorkspace) -> list[RunnerArtifact]:
        artifacts: list[RunnerArtifact] = []
        for path in sorted(workspace.artifacts_dir.rglob("*")):
            if path.is_file():
                artifacts.append(
                    RunnerArtifact(
                        artifact_type="runner_artifact",
                        name=path.name,
                        path=str(path),
                        checksum=self._sha256(path),
                        content_type="application/octet-stream",
                        size_bytes=path.stat().st_size,
                    )
                )
        return artifacts

    def _sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return f"sha256:{digest.hexdigest()}"
