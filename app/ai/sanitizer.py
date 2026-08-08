import copy
import re
from typing import Any, Dict, List, Union

SENSITIVE_KEY_PATTERNS = [
    r"password",
    r"passwd",
    r"secret",
    r"token",
    r"auth",
    r"credential",
    r"private_key",
    r"privatekey",
    r"cert",
    r"bearer",
    r"api_key",
    r"apikey",
]

SENSITIVE_KEYS_EXACT = {
    "data",
    "stringdata",
    "stringData",
    "authorization",
    "proxy-authorization",
}


EXCLUDED_METADATA_KEYS = {
    "secrets",
    "secretname",
    "secret_name",
    "secretref",
    "secret_ref",
    "secretkeyref",
    "secret_key_ref",
}


class EvidenceSanitizer:
    """
    Sanitizes deep investigation evidence and incidents before sending to AI providers.
    Ensures zero leak of Secret data, credentials, tokens, or private keys,
    and applies request-size limits to control token costs.
    """

    MAX_EVENTS = 15
    MAX_EVENT_MESSAGE_LENGTH = 300
    MAX_STRING_LENGTH = 1000
    MAX_FINDINGS = 25
    MAX_RELATIONSHIPS = 30

    @classmethod
    def sanitize(cls, raw_evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for sanitizing an incident/investigation evidence dictionary.
        Returns a clean, safe, structure-bounded payload.
        """
        copied = copy.deepcopy(raw_evidence)
        sanitized = cls._sanitize_recursive(copied)

        # Apply specific high-level structural constraints for AI reasoning payload
        payload = {
            "incident": {
                "id": sanitized.get("incident_id", "INC-UNKNOWN"),
                "category": sanitized.get("category", "Unknown"),
                "state": sanitized.get("current_state", "Unknown"),
                "status": sanitized.get("status", "OPEN"),
                "occurrences": sanitized.get("occurrences", 1),
                "severity": sanitized.get("diagnosis", {}).get("severity", "MEDIUM"),
            },
            "target": {
                "kind": sanitized.get("resource", {}).get("kind", "Pod"),
                "namespace": sanitized.get("resource", {}).get("namespace", "default"),
                "name": sanitized.get("resource", {}).get("name", "unknown"),
            },
            "deterministic_diagnosis": sanitized.get("diagnosis", {}),
            "findings": cls._limit_list(sanitized.get("investigation", {}).get("findings", []), cls.MAX_FINDINGS),
            "relationships": cls._limit_list(sanitized.get("investigation", {}).get("relationships", []), cls.MAX_RELATIONSHIPS),
        }

        inv = sanitized.get("investigation", {})
        if inv.get("pod"):
            payload["pod"] = cls._sanitize_pod_info(inv["pod"])

        if inv.get("controllers"):
            payload["controllers"] = inv["controllers"]

        if inv.get("services"):
            payload["services"] = inv["services"]

        if inv.get("endpoints"):
            payload["endpoints"] = inv["endpoints"]

        if inv.get("node"):
            payload["node"] = inv["node"]

        if inv.get("storage"):
            payload["storage"] = inv["storage"]

        if inv.get("events"):
            payload["events"] = cls._sanitize_events(inv["events"])
        elif sanitized.get("evidence"):
            payload["events"] = cls._sanitize_events(sanitized["evidence"])

        if inv.get("configmaps"):
            payload["configmaps"] = [
                {"name": cm.get("name"), "namespace": cm.get("namespace"), "keys": cm.get("keys", [])}
                for cm in inv["configmaps"] if isinstance(cm, dict)
            ]

        if inv.get("secrets"):
            # Include secret names and namespaces ONLY - NEVER data or values
            payload["secrets"] = [
                {"name": sec.get("name"), "namespace": sec.get("namespace")}
                for sec in inv["secrets"] if isinstance(sec, dict)
            ]

        return payload

    @classmethod
    def _sanitize_pod_info(cls, pod_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitizes pod specification and status info.
        Redacts sensitive env variables and trims large fields.
        """
        clean_pod = copy.deepcopy(pod_info)

        containers = clean_pod.get("containers", [])
        for c in containers:
            if isinstance(c, dict) and "env" in c:
                clean_env = []
                for env in c["env"]:
                    if isinstance(env, dict):
                        name = env.get("name", "")
                        if cls._is_sensitive_key(name):
                            clean_env.append({"name": name, "value": "[REDACTED]"})
                        else:
                            clean_env.append(env)
                c["env"] = clean_env

        return clean_pod

    @classmethod
    def _sanitize_events(cls, events: List[Any]) -> List[Dict[str, Any]]:
        """
        Sanitizes and bounds event lists.
        """
        if not isinstance(events, list):
            return []

        # Sort or take last N events
        limited_events = events[-cls.MAX_EVENTS:]
        sanitized = []
        for ev in limited_events:
            if isinstance(ev, dict):
                msg = str(ev.get("message", ""))
                if len(msg) > cls.MAX_EVENT_MESSAGE_LENGTH:
                    msg = msg[: cls.MAX_EVENT_MESSAGE_LENGTH] + "... [TRUNCATED]"
                sanitized.append({
                    "type": ev.get("type", "Warning"),
                    "reason": ev.get("reason", "Unknown"),
                    "message": msg,
                    "count": ev.get("count", 1),
                    "first_timestamp": ev.get("first_timestamp"),
                    "last_timestamp": ev.get("last_timestamp"),
                })
            elif isinstance(ev, str):
                sanitized.append({"type": "Warning", "reason": "Event", "message": ev[:cls.MAX_EVENT_MESSAGE_LENGTH]})
        return sanitized

    @classmethod
    def _sanitize_recursive(cls, data: Any) -> Any:
        """
        Recursively strips sensitive keys like 'data', 'stringData', 'password', etc.
        from nested structures.
        """
        if isinstance(data, dict):
            clean_dict = {}
            for k, v in data.items():
                k_lower = str(k).lower()
                if k in SENSITIVE_KEYS_EXACT or k_lower in SENSITIVE_KEYS_EXACT:
                    continue  # Completely remove secret data dicts like Secret.data / Secret.stringData
                if cls._is_sensitive_key(str(k)) and not isinstance(v, (dict, list)):
                    clean_dict[k] = "[REDACTED]"
                else:
                    clean_dict[k] = cls._sanitize_recursive(v)
            return clean_dict
        elif isinstance(data, list):
            return [cls._sanitize_recursive(item) for item in data]
        elif isinstance(data, str):
            if len(data) > cls.MAX_STRING_LENGTH:
                return data[: cls.MAX_STRING_LENGTH] + "... [TRUNCATED]"
            return data
        return data

    @classmethod
    def _is_sensitive_key(cls, key_name: str) -> bool:
        key_lower = key_name.lower()
        if key_lower in EXCLUDED_METADATA_KEYS:
            return False
        for pattern in SENSITIVE_KEY_PATTERNS:
            if re.search(pattern, key_lower):
                return True
        return False

    @classmethod
    def _limit_list(cls, items: List[Any], limit: int) -> List[Any]:
        if isinstance(items, list) and len(items) > limit:
            return items[:limit]
        return items if isinstance(items, list) else []
