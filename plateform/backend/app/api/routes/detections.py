from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_detection_service, get_investigation_service
from app.schemas.detections import (
    AddNoteRequest,
    DetectionDetail,
    DetectionEvidenceResponse,
    DetectionListResponse,
    DetectionPriority,
    DetectionQueueStats,
    DetectionSortField,
    DetectionStatus,
    DismissDetectionRequest,
    InvestigationAgentInputV1,
    InvestigationHistoryResponse,
    MergeDetectionRequest,
    PromoteDetectionRequest,
    PromoteDetectionResponse,
    ReopenDetectionRequest,
    SortOrder,
    StartReviewRequest,
)
from app.services.detections import DetectionService
from app.services.investigation import InvestigationService

router = APIRouter(prefix="/detections", tags=["detections"])


@router.get("", response_model=DetectionListResponse)
def get_detections(
    status: DetectionStatus | None = Query(default=None),
    priority: DetectionPriority | None = Query(default=None),
    rule: str | None = Query(default=None, description="Rule code"),
    sensor: str | None = Query(default=None),
    zone: str | None = Query(default=None),
    reason_code: str | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    search: str | None = Query(default=None),
    sort_by: DetectionSortField = Query(default=DetectionSortField.detected_at),
    sort_order: SortOrder = Query(default=SortOrder.desc),
    service: DetectionService = Depends(get_detection_service),
) -> DetectionListResponse:
    return service.list_detections(
        status=status,
        priority=priority,
        rule_code=rule,
        sensor=sensor,
        zone=zone,
        reason_code=reason_code,
        start=start,
        end=end,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/summary", response_model=DetectionQueueStats)
def get_detection_summary(
    service: DetectionService = Depends(get_detection_service),
) -> DetectionQueueStats:
    return service.summary()


@router.get("/{detection_id}", response_model=DetectionDetail)
def get_detection_detail(
    detection_id: str,
    service: DetectionService = Depends(get_detection_service),
) -> DetectionDetail:
    return service.get_detection(detection_id)


@router.get("/{detection_id}/evidence", response_model=DetectionEvidenceResponse)
def get_detection_evidence(
    detection_id: str,
    service: DetectionService = Depends(get_detection_service),
) -> DetectionEvidenceResponse:
    return service.get_evidence(detection_id)


@router.get("/{detection_id}/agent-input", response_model=InvestigationAgentInputV1)
def get_detection_agent_input(
    detection_id: str,
    service: DetectionService = Depends(get_detection_service),
) -> InvestigationAgentInputV1:
    return service.agent_input(detection_id)


@router.get("/{detection_id}/history", response_model=InvestigationHistoryResponse)
def get_detection_history(
    detection_id: str,
    service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationHistoryResponse:
    return service.history(detection_id)


@router.post("/{detection_id}/review", response_model=DetectionDetail)
def start_detection_review(
    detection_id: str,
    payload: StartReviewRequest,
    service: InvestigationService = Depends(get_investigation_service),
) -> DetectionDetail:
    return service.start_review(detection_id, payload)


@router.post("/{detection_id}/notes", response_model=DetectionDetail)
def add_detection_note(
    detection_id: str,
    payload: AddNoteRequest,
    service: InvestigationService = Depends(get_investigation_service),
) -> DetectionDetail:
    return service.add_note(detection_id, payload)


@router.post("/{detection_id}/dismiss", response_model=DetectionDetail)
def dismiss_detection(
    detection_id: str,
    payload: DismissDetectionRequest,
    service: InvestigationService = Depends(get_investigation_service),
) -> DetectionDetail:
    return service.dismiss(detection_id, payload)


@router.post("/{detection_id}/reopen", response_model=DetectionDetail)
def reopen_detection(
    detection_id: str,
    payload: ReopenDetectionRequest,
    service: InvestigationService = Depends(get_investigation_service),
) -> DetectionDetail:
    return service.reopen(detection_id, payload)


@router.post("/{detection_id}/merge", response_model=DetectionDetail)
def merge_detection(
    detection_id: str,
    payload: MergeDetectionRequest,
    service: InvestigationService = Depends(get_investigation_service),
) -> DetectionDetail:
    return service.merge(detection_id, payload)


@router.post("/{detection_id}/promote", response_model=PromoteDetectionResponse)
def promote_detection(
    detection_id: str,
    payload: PromoteDetectionRequest,
    service: InvestigationService = Depends(get_investigation_service),
) -> PromoteDetectionResponse:
    return service.promote(detection_id, payload)
