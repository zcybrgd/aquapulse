"""Enable PostGIS and add nullable geometry columns for the live network map."""

from alembic import op
from geoalchemy2 import Geometry
import sqlalchemy as sa

revision = "0003_postgis_map"
down_revision = "0002_asset_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.add_column(
        "zones",
        sa.Column(
            "boundary",
            Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=True,
        ),
    )
    op.add_column(
        "pipeline_segments",
        sa.Column(
            "geometry",
            Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=False),
            nullable=True,
        ),
    )
    op.add_column(
        "assets",
        sa.Column(
            "location",
            Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=True,
        ),
    )

    op.create_index("ix_zones_boundary", "zones", ["boundary"], postgresql_using="gist")
    op.create_index(
        "ix_pipeline_segments_geometry",
        "pipeline_segments",
        ["geometry"],
        postgresql_using="gist",
    )
    op.create_index("ix_assets_location", "assets", ["location"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_index("ix_assets_location", table_name="assets")
    op.drop_index("ix_pipeline_segments_geometry", table_name="pipeline_segments")
    op.drop_index("ix_zones_boundary", table_name="zones")
    op.drop_column("assets", "location")
    op.drop_column("pipeline_segments", "geometry")
    op.drop_column("zones", "boundary")
    # Keep the PostGIS extension. Other objects may depend on it.
