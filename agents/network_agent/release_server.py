import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agents.network_agent.camara_api import camara_service
logger = logging.getLogger("network_agent.release_server")

app = FastAPI(title="AquaPulse Network Release Service")


class ReleaseRequest(BaseModel):
    session_id: str
    incident_id: str


@app.post("/v1/qod/release")
def release_qod(body: ReleaseRequest) -> dict:
    result = camara_service.delete_qod_session(session_id=body.session_id)
    if result.get("status") != "DELETED":
        logger.error(
            "qod_release_FAILED incident_id=%s session_id=%s error=%s",
            body.incident_id, body.session_id, result.get("error"),
        )
        raise HTTPException(status_code=502, detail=result.get("error", "QoD release failed"))
    logger.info(
        "qod_released incident_id=%s session_id=%s",
        body.incident_id, body.session_id,
    )
    return {"status": "DELETED", "session_id": body.session_id}


@app.post("/v1/slice/release")
def release_slice(body: ReleaseRequest) -> dict:
    # session_id for a slice grant is the slice_id (see webhook_server.trigger_response_agent_grant)
    result = camara_service.delete_network_slice(slice_id=body.session_id)
    if result.get("status") != "DELETED":
        logger.error(
            "slice_release_FAILED incident_id=%s slice_id=%s error=%s",
            body.incident_id, body.session_id, result.get("error"),
        )
        raise HTTPException(status_code=502, detail=result.get("error", "Slice release failed"))
    logger.info(
        "slice_released incident_id=%s slice_id=%s",
        body.incident_id, body.session_id,
    )
    return {"status": "DELETED", "slice_id": body.session_id}


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}