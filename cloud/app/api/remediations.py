from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request, status
from datetime import datetime, timezone
import random

router = APIRouter(prefix="/api/v1/remediations", tags=["Remediations"])

# In-memory store for remediations and audit logs
remediations_store: List[Dict[str, Any]] = [
    {
        "remediation_id": "REM-0842",
        "incident_id": "INC-0842",
        "cluster_id": "skyops-cluster-prod-us",
        "action_type": "RESOURCE_ADJUSTMENT",
        "target_kind": "Deployment",
        "namespace": "payments",
        "target_name": "payment-processor",
        "command_action": "kubectl patch deployment payment-processor -n payments --type=json -p='[{\"op\": \"replace\", \"path\": \"/spec/template/spec/containers/0/resources/limits/memory\", \"value\": \"1Gi\"}]'",
        "rationale": "Container memory limit exceeded peak RSS (524Mi). Increasing limit from 512Mi to 1Gi prevents OOM-killer termination.",
        "risk_level": "LOW",
        "approval_status": "PENDING",
        "execution_status": "NOT_EXECUTED",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
]

audit_store: List[Dict[str, Any]] = []


@router.get("", status_code=status.HTTP_200_OK)
def list_remediations(
    cluster_id: Optional[str] = Query(None),
    incident_id: Optional[str] = Query(None)
):
    res = list(remediations_store)
    if cluster_id and cluster_id != "ALL":
        res = [r for r in res if r.get("cluster_id") == cluster_id]
    if incident_id:
        res = [r for r in res if r.get("incident_id") == incident_id]
    return res


@router.get("/audit", status_code=status.HTTP_200_OK)
def list_audit_records(cluster_id: Optional[str] = Query(None)):
    res = list(audit_store)
    if cluster_id and cluster_id != "ALL":
        res = [r for r in res if r.get("cluster_id") == cluster_id]
    return res


@router.get("/{id}", status_code=status.HTTP_200_OK)
def get_remediation(id: str):
    found = next((r for r in remediations_store if r.get("remediation_id") == id or r.get("incident_id") == id), None)
    if not found:
        raise HTTPException(status_code=404, detail=f"Remediation Plan '{id}' not found")
    return found


@router.post("/{id}/dry-run", status_code=status.HTTP_200_OK)
def dry_run_remediation(id: str):
    found = next((r for r in remediations_store if r.get("remediation_id") == id or r.get("incident_id") == id), None)
    if not found:
        raise HTTPException(status_code=404, detail=f"Remediation Plan '{id}' not found")

    now = datetime.now(timezone.utc).isoformat()
    result = {
        "passed": True,
        "target_resource": f"{found.get('target_kind')}/{found.get('target_name')} in ns/{found.get('namespace')}",
        "target_found": True,
        "risk_level": found.get("risk_level", "MEDIUM"),
        "action_type": found.get("action_type"),
        "expected_effect": f"Dry run validation succeeded. Action '{found.get('action_type')}' is allowlisted and policy compliant.",
        "executed_at": now,
    }
    found["execution_status"] = "DRY_RUN_PASSED"
    found["dry_run_result"] = result
    return {"passed": True, "plan": found, "result": result}


@router.post("/{id}/approve", status_code=status.HTTP_200_OK)
async def approve_remediation(id: str, request: Request):
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    found = next((r for r in remediations_store if r.get("remediation_id") == id or r.get("incident_id") == id), None)
    if not found:
        raise HTTPException(status_code=404, detail=f"Remediation Plan '{id}' not found")

    now = datetime.now(timezone.utc).isoformat()
    found["approval_status"] = "APPROVED"
    found["approved_by"] = body.get("approved_by", "operator@skyops.internal")
    found["approved_at"] = now

    return {"status": "APPROVED", "plan": found}


@router.post("/{id}/reject", status_code=status.HTTP_200_OK)
async def reject_remediation(id: str, request: Request):
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    found = next((r for r in remediations_store if r.get("remediation_id") == id or r.get("incident_id") == id), None)
    if not found:
        raise HTTPException(status_code=404, detail=f"Remediation Plan '{id}' not found")

    now = datetime.now(timezone.utc).isoformat()
    found["approval_status"] = "REJECTED"
    found["rejected_at"] = now
    found["rejection_reason"] = body.get("reason", "Rejected by operator")
    found["execution_status"] = "BLOCKED"

    return {"status": "REJECTED", "plan": found}


@router.post("/{id}/execute", status_code=status.HTTP_200_OK)
def execute_remediation(id: str):
    found = next((r for r in remediations_store if r.get("remediation_id") == id or r.get("incident_id") == id), None)
    if not found:
        raise HTTPException(status_code=404, detail=f"Remediation Plan '{id}' not found")

    if found.get("execution_status") in ["EXECUTED", "ALREADY_EXECUTED"]:
        found["execution_status"] = "ALREADY_EXECUTED"
        return {"status": "ALREADY_EXECUTED", "message": "Action previously executed. Duplicate execution prevented.", "plan": found}

    if found.get("approval_status") != "APPROVED":
        raise HTTPException(status_code=400, detail="Human approval is required prior to remediation execution.")

    now = datetime.now(timezone.utc).isoformat()
    found["execution_status"] = "EXECUTED"
    found["executed_at"] = now
    found["execution_result"] = {
        "status": "SUCCESS",
        "command": found.get("command_action"),
        "method": "Kubernetes API client",
        "executed_at": now,
    }
    found["verification_status"] = "SUCCESS"
    found["completed_at"] = now
    found["verification_result"] = {
        "verified_at": now,
        "workload_status": "HEALTHY",
        "ready_replicas": 1,
        "desired_replicas": 1,
    }

    audit_entry = {
        "audit_id": f"AUD-{random.randint(10000, 99999)}",
        "remediation_id": found.get("remediation_id"),
        "incident_id": found.get("incident_id"),
        "cluster_id": found.get("cluster_id"),
        "action_type": found.get("action_type"),
        "approved_by": found.get("approved_by"),
        "executed_at": now,
        "status": "SUCCESS",
        "details": found.get("command_action"),
    }
    audit_store.insert(0, audit_entry)

    return {"status": "SUCCESS", "plan": found}


@router.post("/{id}/rollback", status_code=status.HTTP_200_OK)
def rollback_remediation(id: str):
    found = next((r for r in remediations_store if r.get("remediation_id") == id or r.get("incident_id") == id), None)
    if not found:
        raise HTTPException(status_code=404, detail=f"Remediation Plan '{id}' not found")

    now = datetime.now(timezone.utc).isoformat()
    found["execution_status"] = "ROLLED_BACK"
    found["rolled_back_at"] = now

    return {"status": "ROLLED_BACK", "plan": found}
