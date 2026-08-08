from app.incidents.models import Incident


def test_incident_identity_key_stability():
    """
    Verifies that state shifts like ErrImagePull -> ImagePullBackOff generate the SAME identity key.
    """
    key1 = Incident.compute_identity_key("default", "Pod", "uid-123", "ErrImagePull")
    key2 = Incident.compute_identity_key("default", "Pod", "uid-123", "ImagePullBackOff")

    assert key1 == key2, "ErrImagePull and ImagePullBackOff should map to the same identity key"


def test_different_resource_different_identity():
    """
    Verifies that different resources generate DIFFERENT identity keys.
    """
    key1 = Incident.compute_identity_key("default", "Pod", "uid-nginx-1", "ImagePullBackOff")
    key2 = Incident.compute_identity_key("default", "Pod", "uid-nginx-2", "ImagePullBackOff")

    assert key1 != key2, "Different pods must have different identity keys"
