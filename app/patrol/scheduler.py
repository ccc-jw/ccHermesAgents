class PatrolScheduler:
    def scan_project(self, project_state: dict) -> list[dict]:
        risks: list[dict] = []
        for review in project_state.get("reviews", []):
            if review.get("status") == "open" and review.get("deadline_passed") is True:
                risks.append({"type": "review_timeout", "object_id": review["id"]})
        for task in project_state.get("tasks", []):
            if task.get("status") == "running" and task.get("deadline_passed") is True:
                risks.append({"type": "task_timeout", "object_id": task["id"]})
        return risks
