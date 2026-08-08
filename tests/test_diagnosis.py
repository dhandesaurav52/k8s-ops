from app.diagnosis.engine import DiagnosisEngine


def test_image_pull_backoff_diagnosis():
    events = [{"message": "Failed to pull image docker.io/library/nginxd:latest: rpc error: code = NotFound"}]
    diagnosis, recommendations = DiagnosisEngine.diagnose("ImagePullBackOff", "ImagePullBackOff", events)

    assert diagnosis["incident_category"] == "ImagePullFailure"
    assert diagnosis["severity"] == "MEDIUM"
    assert "non-existent" in diagnosis["root_cause"].lower() or "tag not found" in diagnosis["root_cause"].lower()
    assert len(recommendations) > 0


def test_crashloop_backoff_diagnosis():
    events = []
    diagnosis, recommendations = DiagnosisEngine.diagnose("CrashLoopBackOff", "CrashLoopBackOff", events)

    assert diagnosis["incident_category"] == "CrashLoopBackOff"
    assert diagnosis["severity"] == "HIGH"
    assert "exited prematurely" in diagnosis["root_cause"].lower()
    assert len(recommendations) > 0
