from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, Request, status
import time
from datetime import datetime, timezone
from cloud.app.auth import get_current_identity

router = APIRouter(
    prefix="/api/v1/metrics",
    tags=["Metrics"],
    dependencies=[Depends(get_current_identity)],
)

# In-memory store for live metrics posted by agents
metrics_cache: Dict[str, Dict[str, Any]] = {}


@router.get("", status_code=status.HTTP_200_OK)
def get_metrics_summary(cluster_id: Optional[str] = Query(None)):
    target_cluster = cluster_id or "skyops-cluster-prod-us"
    if target_cluster in metrics_cache:
        return metrics_cache[target_cluster]

    return {
        "cluster_id": target_cluster,
        "metrics_status": "UNAVAILABLE",
        "status_message": "No metrics reported for this cluster (metrics-server required)",
        "source": "Unknown",
        "last_collected": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_cpu_mcores": 0,
            "used_cpu_mcores": 0,
            "cpu_utilization_pct": 0,
            "total_memory_mb": 0,
            "used_memory_mb": 0,
            "memory_utilization_pct": 0,
        },
        "nodes": [],
        "pods": [],
    }


@router.post("", status_code=status.HTTP_200_OK)
async def post_metrics(request: Request):
    body = await request.json()
    cid = body.get("cluster_id")
    if not cid:
        return {"status": "error", "message": "cluster_id is required"}

    now_iso = datetime.now(timezone.utc).isoformat()
    metrics_cache[cid] = {
        "cluster_id": cid,
        "metrics_status": body.get("metrics_status", "ONLINE"),
        "status_message": body.get("status_message", "Live metrics reported by SkyOps agent"),
        "source": body.get("source", "metrics.k8s.io"),
        "last_collected": now_iso,
        "summary": body.get("summary", {
            "total_cpu_mcores": 0,
            "used_cpu_mcores": 0,
            "cpu_utilization_pct": 0,
            "total_memory_mb": 0,
            "used_memory_mb": 0,
            "memory_utilization_pct": 0,
        }),
        "nodes": body.get("nodes", []),
        "pods": body.get("pods", []),
    }
    return {"status": "ok", "cluster_id": cid, "timestamp": now_iso}


@router.get("/nodes", status_code=status.HTTP_200_OK)
def get_node_metrics(cluster_id: Optional[str] = Query(None)):
    if not cluster_id or cluster_id == "ALL":
        all_nodes = []
        for m in metrics_cache.values():
            all_nodes.extend(m.get("nodes", []))
        return all_nodes

    if cluster_id in metrics_cache:
        return metrics_cache[cluster_id].get("nodes", [])
    return []


@router.get("/pods", status_code=status.HTTP_200_OK)
def get_pod_metrics(cluster_id: Optional[str] = Query(None)):
    if not cluster_id or cluster_id == "ALL":
        all_pods = []
        for m in metrics_cache.values():
            all_pods.extend(m.get("pods", []))
        return all_pods

    if cluster_id in metrics_cache:
        return metrics_cache[cluster_id].get("pods", [])
    return []


@router.get("/history", status_code=status.HTTP_200_OK)
def get_metric_history(
    cluster_id: Optional[str] = Query(None),
    range: str = Query("1h")
):
    target_cluster = cluster_id or "skyops-cluster-prod-us"
    m = metrics_cache.get(target_cluster)
    is_online = m and m.get("metrics_status") == "ONLINE"

    points_count = 12
    interval_sec = 300
    if range == "5m":
        points_count = 10
        interval_sec = 30
    elif range == "15m":
        points_count = 15
        interval_sec = 60
    elif range == "30m":
        points_count = 15
        interval_sec = 120
    elif range == "6h":
        points_count = 24
        interval_sec = 900
    elif range == "24h":
        points_count = 24
        interval_sec = 3600

    now_ts = int(time.time())
    points = []
    base_cpu = m.get("summary", {}).get("cpu_utilization_pct", 50) if is_online else 0
    base_mem = m.get("summary", {}).get("memory_utilization_pct", 60) if is_online else 0

    for i in range(points_count - 1, -1, -1):
        pt_time = datetime.fromtimestamp(now_ts - i * interval_sec, tz=timezone.utc)
        cpu_pct = base_cpu if is_online else 0
        mem_pct = base_mem if is_online else 0
        points.append({
            "timestamp": pt_time.isoformat(),
            "timeLabel": pt_time.strftime("%H:%M"),
            "cpu_pct": cpu_pct,
            "memory_pct": mem_pct,
            "cpu_mcores": 0 if not is_online else int(32000 * (cpu_pct / 100)),
            "memory_mb": 0 if not is_online else int(131072 * (mem_pct / 100)),
        })

    return {
        "cluster_id": target_cluster,
        "time_range": range,
        "metrics_status": "ONLINE" if is_online else "UNAVAILABLE",
        "points": points,
    }
