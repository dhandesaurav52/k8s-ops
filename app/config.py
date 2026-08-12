import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
INCIDENTS_FILE = DATA_DIR / "incidents.json"

# Kubernetes Watcher Settings
WATCH_NAMESPACE = os.getenv("SKYOPS_NAMESPACE", None)  # None = all namespaces
WATCH_TIMEOUT_SECONDS = int(os.getenv("SKYOPS_WATCH_TIMEOUT", "60"))
RECONNECT_DELAY_SECONDS = int(os.getenv("SKYOPS_RECONNECT_DELAY", "5"))

# Logging & Environment
LOG_LEVEL = os.getenv("SKYOPS_LOG_LEVEL", "INFO")
CLUSTER_NAME = os.getenv("SKYOPS_CLUSTER_NAME", "default-cluster")
AGENT_PORT = int(os.getenv("SKYOPS_AGENT_PORT", "8080"))
AGENT_NAMESPACE = os.getenv("SKYOPS_AGENT_NAMESPACE", "skyops")
CLUSTER_ID_FILE = DATA_DIR / "cluster_id.txt"

# Security
MASK_SECRET_KEYS = True

# AI Reasoning Engine Configuration
ENABLE_AI_INTEGRATION = False  # Set to True when AI features are needed
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", None)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
AI_MAX_RETRIES = int(os.getenv("SKYOPS_AI_MAX_RETRIES", "2"))
AI_INPUT_COST_PER_MILLION_TOKENS = float(os.getenv("AI_INPUT_COST_PER_MILLION_TOKENS", "0.10"))
AI_OUTPUT_COST_PER_MILLION_TOKENS = float(os.getenv("AI_OUTPUT_COST_PER_MILLION_TOKENS", "0.40"))
SKYOPS_RUN_LIVE_AI_TEST = os.getenv("SKYOPS_RUN_LIVE_AI_TEST", "false").lower() in ("true", "1", "yes")
