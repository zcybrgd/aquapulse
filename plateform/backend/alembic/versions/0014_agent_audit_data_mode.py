"""Allow ingested agent audit events, not only mock_agent_data."""

from alembic import op

revision = "0014_agent_audit_data_mode"
down_revision = "0013_device_network"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_agent_audit_data_mode", "agent_audit_events", type_="check")


def downgrade() -> None:
    op.create_check_constraint("ck_agent_audit_data_mode", "agent_audit_events", "data_mode = 'mock_agent_data'")
