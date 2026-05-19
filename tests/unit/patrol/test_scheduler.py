from app.patrol.scheduler import PatrolScheduler


def test_patrol_flags_overdue_review():
    scheduler = PatrolScheduler()
    risks = scheduler.scan_project(
        {
            "reviews": [{"id": "review_1", "status": "open", "deadline_passed": True}],
            "tasks": [],
            "issues": [],
        }
    )

    assert risks == [{"type": "review_timeout", "object_id": "review_1"}]
