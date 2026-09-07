from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Asset
from app.db.models.device_network import DeviceNetworkSnapshot


class DeviceNetworkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def next_public_id(self) -> str:
        latest = self.session.scalar(
            select(DeviceNetworkSnapshot.public_id)
            .order_by(DeviceNetworkSnapshot.public_id.desc())
            .limit(1)
        )
        highest = 0
        if latest and latest.upper().startswith("DNS-"):
            try:
                highest = int(latest.split("-", 1)[1])
            except ValueError:
                highest = 0
        return f"DNS-{highest + 1:06d}"

    def get_by_public_id(self, public_id: str) -> DeviceNetworkSnapshot | None:
        return self.session.scalar(
            select(DeviceNetworkSnapshot).where(
                func.upper(DeviceNetworkSnapshot.public_id) == public_id.strip().upper()
            )
        )

    def latest_for_asset(self, asset_id: UUID) -> DeviceNetworkSnapshot | None:
        return self.session.scalar(
            select(DeviceNetworkSnapshot)
            .where(DeviceNetworkSnapshot.asset_id == asset_id)
            .order_by(DeviceNetworkSnapshot.retrieved_at.desc(), DeviceNetworkSnapshot.created_at.desc())
            .limit(1)
        )

    def latest_for_assets(self, asset_ids: list[UUID]) -> dict[UUID, DeviceNetworkSnapshot]:
        if not asset_ids:
            return {}
        rows = self.session.scalars(
            select(DeviceNetworkSnapshot)
            .where(DeviceNetworkSnapshot.asset_id.in_(asset_ids))
            .distinct(DeviceNetworkSnapshot.asset_id)
            .order_by(DeviceNetworkSnapshot.asset_id, DeviceNetworkSnapshot.retrieved_at.desc())
        )
        return {row.asset_id: row for row in rows}

    def history_for_asset(self, asset_id: UUID, *, limit: int = 20) -> list[DeviceNetworkSnapshot]:
        return list(
            self.session.scalars(
                select(DeviceNetworkSnapshot)
                .where(DeviceNetworkSnapshot.asset_id == asset_id)
                .order_by(DeviceNetworkSnapshot.retrieved_at.desc(), DeviceNetworkSnapshot.created_at.desc())
                .limit(limit)
            ).all()
        )

    def latest_retrieved_at(self) -> datetime | None:
        return self.session.scalar(select(func.max(DeviceNetworkSnapshot.retrieved_at)))

    def add(self, snapshot: DeviceNetworkSnapshot) -> DeviceNetworkSnapshot:
        self.session.add(snapshot)
        self.session.flush()
        return snapshot

    def list_assets(self) -> list[Asset]:
        return list(
            self.session.scalars(
                select(Asset)
                .options(joinedload(Asset.zone), joinedload(Asset.pipeline_segment))
                .order_by(Asset.external_id.asc())
            ).unique().all()
        )
