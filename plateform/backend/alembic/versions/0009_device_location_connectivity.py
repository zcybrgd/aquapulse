"""Device location labels, cellular identity, and zone backfill checks.

assets.zone_id already exists from 0001. This revision adds device_msisdn and
location_label, backfills any missing zone_id from the pipeline segment, and
fails if a zone cannot be derived.
"""

from alembic import op
import sqlalchemy as sa

revision = "0009_device_location"
down_revision = "0008_agent_integration_readiness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("device_msisdn", sa.String(length=16), nullable=True))
    op.add_column("assets", sa.Column("location_label", sa.String(length=160), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE assets AS asset
            SET zone_id = segment.zone_id
            FROM pipeline_segments AS segment
            WHERE asset.pipeline_segment_id = segment.id
              AND asset.zone_id IS NULL
            """
        )
    )

    missing = op.get_bind().execute(sa.text("SELECT external_id FROM assets WHERE zone_id IS NULL")).fetchall()
    if missing:
        ids = ", ".join(row[0] for row in missing)
        raise RuntimeError(
            f"asset_zone_required: these assets have no derivable zone: {ids}"
        )

    mismatched = op.get_bind().execute(
        sa.text(
            """
            SELECT asset.external_id
            FROM assets AS asset
            JOIN pipeline_segments AS segment ON asset.pipeline_segment_id = segment.id
            WHERE asset.zone_id <> segment.zone_id
            """
        )
    ).fetchall()
    if mismatched:
        ids = ", ".join(row[0] for row in mismatched)
        raise RuntimeError(
            f"asset_zone_segment_mismatch: these assets disagree with their pipeline segment zone: {ids}"
        )

    op.create_check_constraint(
        "ck_assets_device_msisdn_e164",
        "assets",
        "device_msisdn IS NULL OR device_msisdn ~ '^\\+[1-9][0-9]{1,14}$'",
    )
    op.create_check_constraint(
        "ck_assets_location_label_length",
        "assets",
        "location_label IS NULL OR (char_length(location_label) >= 1 AND char_length(location_label) <= 160)",
    )
    op.create_index(
        "uq_assets_device_msisdn",
        "assets",
        ["device_msisdn"],
        unique=True,
        postgresql_where=sa.text("device_msisdn IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_assets_device_msisdn", table_name="assets")
    op.drop_constraint("ck_assets_location_label_length", "assets", type_="check")
    op.drop_constraint("ck_assets_device_msisdn_e164", "assets", type_="check")
    op.drop_column("assets", "location_label")
    op.drop_column("assets", "device_msisdn")
