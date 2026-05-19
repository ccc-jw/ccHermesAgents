from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app.models import Artifact, Project, Task, TaskContract, TaskRun


def test_core_models_persist_together():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        project = Project(
            id="proj_1",
            name="Demo",
            owner_user_id="u1",
            created_at="now",
            updated_at="now",
        )
        task = Task(
            id="task_1",
            project_id="proj_1",
            phase="DEVELOPMENT",
            owner_agent="DEV",
            title="Do",
            created_by="PM",
            created_at="now",
            updated_at="now",
        )
        contract = TaskContract(
            id="contract_1",
            task_id="task_1",
            project_id="proj_1",
            task_goal="Do",
            role="DEV",
            phase="DEVELOPMENT",
            contract_json="{}",
            created_by="PM",
            created_at="now",
        )
        run = TaskRun(
            id="run_1",
            task_id="task_1",
            project_id="proj_1",
            agent_name="DEV",
            created_at="now",
            updated_at="now",
        )
        artifact = Artifact(
            id="artifact_1",
            project_id="proj_1",
            artifact_type="diff_patch",
            name="diff.patch",
            path="x",
            created_by="DEV",
            created_at="now",
            updated_at="now",
        )
        session.add_all([project, task, contract, run, artifact])
        session.commit()

        assert session.get(Project, "proj_1").current_phase == "INIT"
        assert session.get(Task, "task_1").status == "pending"
        assert session.get(TaskRun, "run_1").status == "CREATED"
