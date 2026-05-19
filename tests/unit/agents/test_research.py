from app.agents.research import ResearchReport


def test_research_report_requires_recommendation_and_evidence():
    report = ResearchReport(
        topic="queue choice",
        options=["Dramatiq", "RQ"],
        recommendation="Dramatiq",
        evidence=["supports Redis broker", "simple worker model"],
    )

    assert report.recommendation == "Dramatiq"
    assert len(report.evidence) == 2
