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


class MockCondition:
    def __init__(self, c_type, status, reason="", message=""):
        self.type = c_type
        self.status = status
        self.reason = reason
        self.message = message


class MockContainerStateWaiting:
    def __init__(self, reason="ContainerCreating", message=""):
        self.reason = reason
        self.message = message


class MockContainerState:
    def __init__(self, waiting=None):
        self.waiting = waiting


class MockContainerStatus:
    def __init__(self, name="nginx", image="nginx:does-not-exist", waiting=None):
        self.name = name
        self.image = image
        self.state = MockContainerState(waiting=waiting)


class MockContainerSpec:
    def __init__(self, name="nginx", image="nginx:does-not-exist"):
        self.name = name
        self.image = image


class MockPodSpec:
    def __init__(self, node_name="node01", containers=None):
        self.node_name = node_name
        self.containers = containers or [MockContainerSpec()]


class MockPodStatus:
    def __init__(self, phase="Pending", conditions=None, container_statuses=None):
        self.phase = phase
        self.conditions = conditions or [MockCondition("PodScheduled", "True")]
        self.container_statuses = container_statuses or [
            MockContainerStatus(waiting=MockContainerStateWaiting("ContainerCreating", "image pull failed"))
        ]


class MockPod:
    def __init__(self):
        self.status = MockPodStatus()
        self.spec = MockPodSpec()


def test_pod_pending_scheduled_does_not_diagnose_unschedulable():
    pod = MockPod()
    events = [{"message": "Failed to pull image nginx:does-not-exist: rpc error: code = Unknown desc = failed to pull and unpack image"}]

    from app.kubernetes.collector import get_pod_unhealthy_state
    is_unhealthy, reason, desc = get_pod_unhealthy_state(pod)
    assert is_unhealthy is True
    assert reason in ["ImagePullFailure", "ContainerCreating"]
    assert "unschedulable" not in desc.lower()

    diagnosis, recs = DiagnosisEngine.diagnose(reason, desc, events, pod_obj=pod)
    assert diagnosis["incident_category"] in ["ImagePullFailure", "ContainerStartupFailure"]
    assert "cannot be scheduled" not in diagnosis["root_cause"].lower()
    assert diagnosis["confidence_score"] >= 80

