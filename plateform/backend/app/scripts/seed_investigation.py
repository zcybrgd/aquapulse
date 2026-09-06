"""Idempotent demonstration workflow state for existing detections.

Does not create detections or incidents. If DET-000002 is still `new`, start
review so the Investigation Queue has one new, one under_review, and one
merge/dismiss candidate. Never pre-promotes.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AnomalyDetection
from app.schemas.detections import StartReviewRequest
from app.services.investigation import InvestigationService

DEMO_ACTOR = "Demo Operator"
REVIEW_TARGET = "DET-000002"


def seed_investigation_demo(session: Session) -> str | None:
    row = session.scalar(
        select(AnomalyDetection).where(AnomalyDetection.detection_number == REVIEW_TARGET)
    )
    if row is None:
        return None
    if row.status != "new":
        return row.status
    InvestigationService(session).start_review(
        REVIEW_TARGET,
        StartReviewRequest(
            actor_name=DEMO_ACTOR,
            note="Demonstration review started from seed. This is not a confirmed incident.",
        ),
        commit=False,
    )
    return "under_review"
