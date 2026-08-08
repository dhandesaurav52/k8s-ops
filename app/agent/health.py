import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

logger = logging.getLogger("SkyOps.HealthServer")


class AgentHealthRequestHandler(BaseHTTPRequestHandler):
    """
    HTTP Request Handler serving /health and /ready probe endpoints for Kubernetes.
    """

    # Class-level state shared across requests
    k8s_connected: bool = False
    cluster_id: str = "unknown"

    def log_message(self, format, *args):
        # Suppress noise in stdout for health checks unless in debug
        logger.debug("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format % args))

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"status": "healthy"}
            self.wfile.write(json.dumps(response).encode("utf-8"))

        elif self.path == "/ready":
            if AgentHealthRequestHandler.k8s_connected:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response = {
                    "status": "ready",
                    "kubernetes": "connected",
                    "cluster_id": AgentHealthRequestHandler.cluster_id,
                }
            else:
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response = {
                    "status": "not_ready",
                    "kubernetes": "disconnected",
                }
            self.wfile.write(json.dumps(response).encode("utf-8"))

        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))


class HealthServer:
    """
    HTTP Health Server manager running as a background daemon thread.
    Exposes /health and /ready endpoints on the configured port.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def set_k8s_status(self, connected: bool, cluster_id: str = "unknown"):
        AgentHealthRequestHandler.k8s_connected = connected
        AgentHealthRequestHandler.cluster_id = cluster_id

    def start(self):
        try:
            self._server = HTTPServer((self.host, self.port), AgentHealthRequestHandler)
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
            logger.info(f"Health server started on http://{self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to start Agent health server: {e}")

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            logger.info("Health server stopped.")
