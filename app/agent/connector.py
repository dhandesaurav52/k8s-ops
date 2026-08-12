from abc import ABC, abstractmethod
import logging
import os
import time
from typing import Any, Dict, Optional

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
        if isinstance(incident, dict):
            inc_id = incident.get("incident_id", "INC-UNKNOWN")
        else:
            inc_id = getattr(incident, "incident_id", "INC-UNKNOWN")
        logger.info(f"[StubConnector] Incident '{inc_id}' reported (Stub mode).")
        return True


class CloudConnector(ClusterConnector):
    """
    Production-capable CloudConnector that communicates with SkyOps Cloud Backend via HTTPS.
    Supports secure token authentication, transient retries with exponential backoff,
    and credential redaction in logs.
    """

    def __init__(
        self,
        cloud_url: Optional[str] = None,
        agent_token: Optional[str] = None,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        raw_url = cloud_url or os.getenv("SKYOPS_SERVER_URL") or os.getenv("SKYOPS_CLOUD_URL", "http://localhost:8000")
        self.cloud_url = raw_url.rstrip("/")
        self.agent_token = agent_token or os.getenv("SKYOPS_AGENT_TOKEN", "skyops-agent-secret-token")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.registered = False

    def _redact(self, text: str) -> str:
        """Redact security tokens from log and exception strings."""
        if self.agent_token and self.agent_token in text:
            return text.replace(self.agent_token, "[REDACTED_TOKEN]")
        return text

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SkyOps-Agent/1.0",
        }
        if self.agent_token:
            headers["Authorization"] = f"Bearer {self.agent_token}"
        return headers

    def register(self, cluster_info: Dict[str, Any]) -> bool:
        """Register or synchronize cluster metadata with SkyOps Cloud."""
        payload = {
            "cluster_id": cluster_info.get("cluster_id", "unknown"),
            "name": cluster_info.get("name", cluster_info.get("cluster_name", "unknown")),
            "kubernetes_version": str(cluster_info.get("kubernetes_version", "unknown")),
            "status": "CONNECTED",
            "node_count": int(cluster_info.get("nodes", cluster_info.get("node_count", 0))),
            "pod_count": int(cluster_info.get("pods", cluster_info.get("pod_count", 0))),
            "namespace_count": int(cluster_info.get("namespaces", cluster_info.get("namespace_count", 0))),
        }

        success, _ = self._post("/api/v1/clusters", payload)
        if success:
            self.registered = True
            logger.info(f"Successfully registered cluster '{payload['cluster_id']}' with SkyOps API.")
        else:
            logger.warning(f"Failed to register cluster '{payload['cluster_id']}' with SkyOps API.")
        return success

    def send_incident(self, incident: Any) -> bool:
        """Send or update an incident on SkyOps API."""
        success, _ = self.send_incident_status(incident)
        return success

    def send_incident_status(self, incident: Any) -> tuple[bool, bool]:
        """
        Send or update an incident on SkyOps API.
        Returns a tuple: (success: bool, is_fatal: bool).
        """
        if isinstance(incident, dict):
            payload = incident
        else:
            resource = getattr(incident, "resource", None)
            res_kind = getattr(resource, "kind", "Pod") if resource else "Pod"
            res_namespace = getattr(resource, "namespace", "default") if resource else "default"
            res_name = getattr(resource, "name", "unknown") if resource else "unknown"
            res_uid = getattr(resource, "uid", "") if resource else ""

            severity = "MEDIUM"
            if hasattr(incident, "diagnosis") and isinstance(incident.diagnosis, dict):
                severity = incident.diagnosis.get("severity", "MEDIUM")

            payload = {
                "cluster_id": getattr(incident, "cluster_id", os.getenv("SKYOPS_CLUSTER_ID", "unknown")),
                "incident_id": getattr(incident, "incident_id", "INC-UNKNOWN"),
                "resource_kind": res_kind,
                "resource_namespace": res_namespace,
                "resource_name": res_name,
                "resource_uid": res_uid,
                "category": getattr(incident, "category", "Unknown"),
                "status": getattr(incident, "status", "OPEN"),
                "current_state": getattr(incident, "current_state", ""),
                "severity": getattr(incident, "severity", severity),
                "occurrences": getattr(incident, "occurrences", 1),
                "diagnosis": getattr(incident, "diagnosis", {}) or {},
                "investigation": getattr(incident, "investigation", {}) or {},
                "ai_analysis": getattr(incident, "ai_analysis", {}) or {},
                "state_history": getattr(incident, "state_history", []) or [],
            }

        inc_id = payload.get("incident_id", "INC-UNKNOWN")
        success, is_fatal = self._post("/api/v1/incidents", payload)
        if success:
            logger.info(f"Successfully synchronized incident '{inc_id}' to SkyOps API.")
        else:
            logger.warning(f"Failed to synchronize incident '{inc_id}' to SkyOps API (fatal={is_fatal}).")
        return success, is_fatal

    def _post(self, endpoint: str, data: Dict[str, Any]) -> tuple[bool, bool]:
        """
        Helper to send HTTP POST request with bounded retries and exponential backoff.
        Returns a tuple: (success: bool, is_fatal: bool).
        """
        import httpx

        url = f"{self.cloud_url}{endpoint}"
        headers = self._get_headers()

        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(url, json=data, headers=headers)

                if response.status_code in (200, 201):
                    return True, False
                
                if response.status_code in (401, 403):
                    # Authentication / authorization failures fail fast, do not retry forever
                    logger.error(
                        f"Authentication failed ({response.status_code}) posting to SkyOps API at {url}. "
                        "Please verify SKYOPS_AGENT_TOKEN."
                    )
                    return False, True

                if response.status_code in (400, 422):
                    # Validation / client error, fail fast
                    logger.error(
                        self._redact(f"Client error ({response.status_code}) posting to SkyOps API: {response.text}")
                    )
                    return False, True

                # Transient server / rate limit errors (500, 502, 503, 504, 429) -> retry
                logger.warning(
                    self._redact(
                        f"Attempt {attempt}/{self.max_retries}: Transient HTTP {response.status_code} "
                        f"from SkyOps API at {url}. Retrying..."
                    )
                )

            except Exception as e:
                err_str = self._redact(str(e))
                logger.warning(
                    f"Attempt {attempt}/{self.max_retries}: Connection error to SkyOps API at {url}: {err_str}"
                )

            if attempt < self.max_retries:
                sleep_time = self.backoff_factor * (2 ** (attempt - 1))
                time.sleep(sleep_time)

        return False, False

