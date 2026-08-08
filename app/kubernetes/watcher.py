import logging
import time
from typing import Optional
from kubernetes import client, watch

from app.incidents.manager import IncidentManager

logger = logging.getLogger("SkyOps.Watcher")


class KubernetesWatcher:
    """
    Kubernetes Stream Watcher.
    Continuously monitors Kubernetes Pod events using the Kubernetes Watch API.
    Features automatic reconnection and retry logic to recover from network drops or watch timeouts.
    """

    def __init__(self, v1: client.CoreV1Api, manager: IncidentManager, namespace: Optional[str] = None):
        self.v1 = v1
        self.manager = manager
        self.namespace = namespace
        self._running = False

    def start(self, max_runs: Optional[int] = None) -> None:
        """
        Starts watching Kubernetes events continuously.
        max_runs: Optional limit on stream reconnect loops (used in unit tests).
        """
        self._running = True
        logger.info(f"Starting SkyOps Watcher on namespace: {self.namespace or 'ALL'}")
        runs = 0

        while self._running:
            w = watch.Watch()
            try:
                if self.namespace:
                    stream = w.stream(
                        self.v1.list_namespaced_pod,
                        namespace=self.namespace,
                        timeout_seconds=60,
                    )
                else:
                    stream = w.stream(
                        self.v1.list_pod_for_all_namespaces,
                        timeout_seconds=60,
                    )

                for event in stream:
                    if not self._running:
                        break
                    event_type = event.get("type")
                    pod = event.get("object")
                    if pod:
                        self.manager.process_pod_event(event_type, pod)

            except client.exceptions.ApiException as e:
                logger.warning(f"Kubernetes watch API error: {e}. Reconnecting in 5 seconds...")
            except Exception as e:
                logger.warning(f"Kubernetes watch disconnected: {e}. Reconnecting in 5 seconds...")
            finally:
                w.stop()

            runs += 1
            if max_runs and runs >= max_runs:
                logger.info("Reached maximum watch run iterations.")
                break

            if self._running:
                time.sleep(2)

    def stop(self) -> None:
        self._running = False
        logger.info("SkyOps Watcher stopped.")
