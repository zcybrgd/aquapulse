"""Simplify incident.status to three current values.

Maps legacy incident rows. Does not rewrite timeline or audit history.
"""

from alembic import op
import sqlalchemy as sa

revision = "0012_incident_statuses"
down_revision = "0011_network_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE incidents
            SET
                status = CASE status
                    WHEN 'open' THEN 'investigating'
                    WHEN 'acknowledged' THEN 'investigating'
                    WHEN 'responding' THEN 'investigating'
                    WHEN 'monitoring' THEN 'investigating'
                    WHEN 'false_alarm' THEN 'resolved'
                    ELSE status
                END,
                resolution_code = CASE
                    WHEN status = 'false_alarm' THEN COALESCE(resolution_code, 'false_alarm')
                    ELSE resolution_code
                END
            WHERE status IN (
                'open',
                'acknowledged',
                'responding',
                'monitoring',
                'false_alarm'
            )
            """
        )
    )

    op.drop_constraint("ck_incidents_false_alarm_requires_code", "incidents", type_="check")
    op.drop_constraint("ck_incidents_active_clears_resolution", "incidents", type_="check")
    op.create_check_constraint(
        "ck_incidents_active_clears_resolution",
        "incidents",
        "status = 'resolved' OR ("
        "resolved_at IS NULL AND resolved_by IS NULL "
        "AND resolution_code IS NULL AND resolution_summary IS NULL)",
    )
    op.create_check_constraint(
        "ck_incidents_status_allowed",
        "incidents",
        "status IN ('investigating', 'awaiting_approval', 'resolved')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_incidents_status_allowed", "incidents", type_="check")
    op.drop_constraint("ck_incidents_active_clears_resolution", "incidents", type_="check")
    op.create_check_constraint(
        "ck_incidents_false_alarm_requires_code",
        "incidents",
        "status <> 'false_alarm' OR ("
        "resolution_code = 'false_alarm' AND resolved_at IS NOT NULL "
        "AND resolved_by IS NOT NULL AND resolution_summary IS NOT NULL "
        "AND btrim(resolution_summary) <> '')",
    )
    op.create_check_constraint(
        "ck_incidents_active_clears_resolution",
        "incidents",
        "status IN ('resolved', 'false_alarm') OR ("
        "resolved_at IS NULL AND resolved_by IS NULL "
        "AND resolution_code IS NULL AND resolution_summary IS NULL)",
    )
