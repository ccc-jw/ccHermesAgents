from app.runners.policy import RunnerPolicy


def test_runner_policy_blocks_dangerous_commands():
    policy = RunnerPolicy(blocked_commands=["git push", "rm -rf", "kubectl apply"])

    assert policy.allows("pytest tests") is True
    assert policy.allows("git push origin main") is False
    assert policy.allows("rm -rf /tmp/x") is False
