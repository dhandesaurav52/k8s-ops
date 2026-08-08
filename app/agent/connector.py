from abc import ABC, abstractmethod
import logging
from typing import Any, Dict

logger = logging.getLogger("SkyOps.ClusterConnector")


class ClusterConnector(ABC):
    """
    Abstract interface for connecting the SkyOps Agent to a backend cloud service.
    Handles cluster registration and outbound incident delivery.
    """

    @abstractmethod
    def register(self, cluster_info: Dict[str, Any]) -> bool:
        """Register the agent cluster information."""
        pass

    @abstractmethod
    def send_incident(self, incident: Any) -> bool:
        """Send an incident update to the central system."""
        pass


class LocalDevelopmentConnector(ClusterConnector):
    """
    Local/Stub implementation of ClusterConnector.
    Logs cluster registration and incidents locally without external cloud network calls.
    """

    def __init__(self, cloud_url: str = "http://localhost:8000"):
        self.cloud_url = cloud_url
        self.registered = False

    def register(self, cluster_info: Dict[str, Any]) -> bool:
        cluster_id = cluster_info.get("cluster_id", "unknown")
        logger.info(
            f"[StubConnector] Cluster '{cluster_id}' registered locally. "
            f"K8s Version: {cluster_info.get('kubernetes_version')}, Nodes: {cluster_info.get('nodes')}"
        )
        self.registered = True
        return True

    def send_incident(self, incident: Any) -> bool:
        inc_id = getattr(incident, "incident_id", "INC-UNKNOWN")
        logger.info(f"[StubConnector] Incident '{inc_id}' reported (Stub mode).")
        return True
