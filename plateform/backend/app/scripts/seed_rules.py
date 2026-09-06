"""Idempotent seed for versioned deterministic detection rules."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DetectionRule, Organization
from app.detection.catalog import RULE_CATALOG

ORG_SLUG = "aquapulse-demo"


def seed_detection_rules(session: Session, *, organization: Organization | None = None) -> int:
    org = organization or session.scalar(select(Organization).where(Organization.slug == ORG_SLUG))
    if org is None:
        raise RuntimeError("Organization must be seeded before detection rules.")
    count = 0
    for spec in RULE_CATALOG:
        lookup = {
            "organization_id": org.id,
            "code": spec["code"],
            "version": spec["version"],
        }
        instance = session.scalar(select(DetectionRule).filter_by(**lookup))
        values = {
            "name": spec["name"],
            "description": spec["description"],
            "rule_type": spec["rule_type"],
            "metric": spec["metric"],
            "operator": spec["operator"],
            "threshold": spec["threshold"],
            "secondary_threshold": spec["secondary_threshold"],
            "window_minutes": spec["window_minutes"],
            "minimum_points": spec["minimum_points"],
            "severity_weight": spec["severity_weight"],
            "enabled": spec["enabled"],
            "configuration": spec["configuration"],
        }
        if instance is None:
            instance = DetectionRule(**lookup, **values)
            session.add(instance)
            session.flush()
        else:
            for key, value in values.items():
                setattr(instance, key, value)
        count += 1
    return count
