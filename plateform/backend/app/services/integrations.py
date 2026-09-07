from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, InterfaceError, OperationalError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AgentIntegrationError, DatabaseUnavailableError
from app.db.base import utc_now
from app.db.models import AnomalyDetection, Incident
from app.db.models.integration import (
    AgentFinding,
    AgentIntegration,
    AgentResponseRecommendation,
    AgentRun,
)
from app.integrations.adapters.investigation import parse_investigation_response
from app.integrations.adapters.response import parse_response_result
from app.integrations.constants import (
    CLASSIFICATION_LABELS,
    CONTRACT_VERSION,
    EXECUTION_DISABLED_MESSAGE,
    INVESTIGATION_AGENT,
    RESPONSE_AGENT,
    SEVERITY_LABELS,
)
from app.integrations.contracts.investigation import (
    AgentHealth,
    InvestigationRequestV1,
    InvestigationResponseV1,
)
from app.integrations.contracts.response import ResponseRequestV1, ResponseResultV1
from app.integrations.factory import investigation_client, response_client
from app.integrations.identity import MappingLookup, investigation_mapper, response_mapper
from app.integrations.redact import redact_payload
from app.integrations.safety import evaluate_response_safety, never_infer_human_approval
from app.repositories.integrations import IntegrationRepository
from app.schemas.integrations import (
    AgentFindingRecord,
    AgentIngestAccepted,
    AgentIntegrationDetail,
    AgentReadiness,
    AgentRecommendationRecord,
    AgentRunDetail,
    AgentRunSummary,
    AgentSummary,
    ContractMetadata,
    MappingCoverage,
    SafetyFlags,
    ValidationResult,
)


def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise AgentIntegrationError(
        "Agent client cannot run inside an active event loop.",
        code="agent_invalid_response",
        status_code=500,
    )


def _side_effects_none() -> dict[str, bool]:
    return {
        "external_request": False,
        "incident_created": False,
        "detection_mutated": False,
        "notification_sent": False,
        "valve_executed": False,
    }


def _validation_errors(exc: ValidationError) -> list[dict[str, Any]]:
    return [{"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]} for error in exc.errors()]


def _unsupported_version(payload: dict[str, Any]) -> None:
    version = payload.get("schema_version")
    if version is None:
        return
    if str(version) not in {CONTRACT_VERSION, "1.0"}:
        raise AgentIntegrationError(
            "Unsupported agent schema version.",
            code="agent_schema_version_unsupported",
            status_code=422,
        )


class IntegrationService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = IntegrationRepository(session)
        self.sync_from_settings()

    def sync_from_settings(self) -> None:
        specs = (
            (
                INVESTIGATION_AGENT,
                "Investigation Agent",
                self.settings.investigation_agent_enabled,
                self.settings.investigation_agent_mode,
                self.settings.investigation_agent_url,
                self.settings.investigation_agent_contract_version,
            ),
            (
                RESPONSE_AGENT,
                "Response Agent",
                self.settings.response_agent_enabled,
                self.settings.response_agent_mode,
                self.settings.response_agent_url,
                self.settings.response_agent_contract_version,
            ),
        )
        for code, name, enabled, mode, url, version in specs:
            row = self.repository.get_integration(code)
            if row is None:
                row = AgentIntegration(
                    agent_code=code,
                    display_name=name,
                    contract_version=version or CONTRACT_VERSION,
                    enabled=False,
                    mode="disabled",
                    health_status="disabled",
                )
                self.session.add(row)
                self.session.flush()
            row.display_name = name
            row.contract_version = version or CONTRACT_VERSION
            row.enabled = bool(self.settings.agent_integration_enabled and enabled)
            normalized_mode = mode if mode in {"disabled", "mock", "remote"} else "disabled"
            row.mode = normalized_mode if row.enabled else "disabled"
            row.base_url = url.strip() or None
            if not row.enabled:
                row.health_status = "disabled"
        try:
            self.session.commit()
        except (OperationalError, InterfaceError) as exc:
            self.session.rollback()
            raise DatabaseUnavailableError() from exc

    def _agent_url_configured(self, code: str) -> bool:
        if code == INVESTIGATION_AGENT:
            return bool(self.settings.investigation_agent_url.strip())
        return bool(self.settings.response_agent_url.strip())

    def _to_summary(self, row: AgentIntegration) -> AgentSummary:
        return AgentSummary(
            agent_code=row.agent_code,
            display_name=row.display_name,
            enabled=row.enabled,
            mode=row.mode,
            contract_version=row.contract_version,
            url_configured=self._agent_url_configured(row.agent_code),
            health_status=row.health_status,
            last_health_check_at=row.last_health_check_at,
            reachable=row.health_status == "healthy",
        )

    def _to_run_summary(self, run: AgentRun) -> AgentRunSummary:
        return AgentRunSummary(
            run_id=run.public_id,
            agent_type=run.agent_type,
            status=run.status,
            source_type=run.source_type,
            source_public_id=run.source_public_id,
            started_at=run.started_at,
            completed_at=run.completed_at,
            duration_ms=run.duration_ms,
            data_mode=run.data_mode,
            mapping_warning_count=len(run.mapping_warnings or []),
            error_code=run.error_code,
        )

    def readiness(self) -> AgentReadiness:
        rows = self.repository.list_integrations()
        return AgentReadiness(
            prepared=True,
            execution_enabled=False,
            safety=SafetyFlags(
                camara_enabled=self.settings.camara_enabled,
                notifications_enabled=self.settings.real_notifications_enabled,
                physical_commands_enabled=self.settings.physical_commands_enabled,
                agent_execution_enabled=False,
                result_ingest_enabled=self.settings.agent_result_ingest_enabled,
            ),
            agents=[self._to_summary(row) for row in rows],
            mapping_coverage=MappingCoverage(
                enabled_mappings=self.repository.mapping_count(),
                unmapped_findings=self.repository.unmapped_finding_count(),
            ),
            last_runs=[self._to_run_summary(run) for run in self.repository.list_runs()[:8]],
            contract_docs={
                "investigation": "/api/integrations/agents/contracts/investigation/v1",
                "response": "/api/integrations/agents/contracts/response/v1",
                "guide": "/integrations",
            },
        )

    def list_agents(self) -> list[AgentSummary]:
        return [self._to_summary(row) for row in self.repository.list_integrations()]

    def get_agent(self, agent_code: str) -> AgentIntegrationDetail:
        row = self.repository.get_integration(agent_code)
        if row is None:
            raise AgentIntegrationError("The agent is not configured.", code="agent_not_configured", status_code=404)
        summary = self._to_summary(row)
        return AgentIntegrationDetail(**summary.model_dump(), metadata={"contract_version": row.contract_version})

    def health(self, agent_code: str) -> AgentHealth:
        row = self.repository.get_integration(agent_code)
        if row is None:
            raise AgentIntegrationError("The agent is not configured.", code="agent_not_configured", status_code=404)
        if agent_code == INVESTIGATION_AGENT:
            client = investigation_client(self.settings)
            result = _run_async(client.health())
        elif agent_code == RESPONSE_AGENT:
            client = response_client(self.settings)
            result = _run_async(client.health())
        else:
            raise AgentIntegrationError("The agent is not configured.", code="agent_not_configured", status_code=404)
        row.health_status = result.status
        row.last_health_check_at = result.checked_at or utc_now()
        self.session.commit()
        return result

    def contract_metadata(self, agent: str) -> ContractMetadata:
        if agent == "investigation":
            return ContractMetadata(
                agent_code=INVESTIGATION_AGENT,
                schema_version=CONTRACT_VERSION,
                request_schema="backend/contracts/agents/investigation/v1/request.schema.json",
                response_schema="backend/contracts/agents/investigation/v1/response.schema.json",
                endpoints=["GET /health", "GET /v1/contract", "POST /v1/investigate"],
                notes=[
                    "Investigation results are advisory evidence.",
                    "confirmed_* is an agent assessment, not human confirmation.",
                    "Results never create incidents or promote detections.",
                ],
            )
        if agent == "response":
            return ContractMetadata(
                agent_code=RESPONSE_AGENT,
                schema_version=CONTRACT_VERSION,
                request_schema="backend/contracts/agents/response/v1/request.schema.json",
                response_schema="backend/contracts/agents/response/v1/response.schema.json",
                endpoints=["GET /health", "GET /v1/contract", "POST /v1/recommend-response"],
                notes=[
                    "Response results are recommendations.",
                    "AquaPulse owns authorization and execution.",
                    "AUTONOMOUS_ISOLATE does not actuate a valve.",
                ],
            )
        raise AgentIntegrationError("The agent is not configured.", code="agent_not_configured", status_code=404)

    def validate_investigation_request(self, payload: dict[str, Any]) -> ValidationResult:
        _unsupported_version(payload)
        try:
            model = InvestigationRequestV1.model_validate(payload)
        except ValidationError as exc:
            raise AgentIntegrationError(
                "The investigation request did not match contract 1.0.",
                code="agent_contract_mismatch",
                status_code=422,
            ) from exc
        return ValidationResult(
            valid=True,
            schema_version=model.schema_version,
            side_effects=_side_effects_none(),
        )

    def validate_investigation_response(self, payload: dict[str, Any]) -> ValidationResult:
        _unsupported_version(payload)
        try:
            parse_investigation_response(payload)
        except ValidationError as exc:
            raise AgentIntegrationError(
                "The investigation response did not match contract 1.0.",
                code="agent_contract_mismatch",
                status_code=422,
            ) from exc
        except ValueError as exc:
            raise AgentIntegrationError(str(exc), code="agent_invalid_response", status_code=422) from exc
        return ValidationResult(valid=True, schema_version=CONTRACT_VERSION, side_effects=_side_effects_none())

    def validate_response_request(self, payload: dict[str, Any]) -> ValidationResult:
        _unsupported_version(payload)
        try:
            model = ResponseRequestV1.model_validate(payload)
        except ValidationError as exc:
            raise AgentIntegrationError(
                "The response request did not match contract 1.0.",
                code="agent_contract_mismatch",
                status_code=422,
            ) from exc
        return ValidationResult(valid=True, schema_version=model.schema_version, side_effects=_side_effects_none())

    def validate_response_result(self, payload: dict[str, Any]) -> ValidationResult:
        _unsupported_version(payload)
        try:
            parse_response_result(payload)
        except ValidationError as exc:
            raise AgentIntegrationError(
                "The response result did not match contract 1.0.",
                code="agent_contract_mismatch",
                status_code=422,
            ) from exc
        except ValueError as exc:
            raise AgentIntegrationError(str(exc), code="agent_invalid_response", status_code=422) from exc
        return ValidationResult(valid=True, schema_version=CONTRACT_VERSION, side_effects=_side_effects_none())

    def refuse_execution(self) -> None:
        raise AgentIntegrationError(EXECUTION_DISABLED_MESSAGE, code="agent_execution_disabled", status_code=503)

    def start_investigation_run(self, *_args: Any, **_kwargs: Any) -> None:
        self.refuse_execution()

    def start_response_run(self, *_args: Any, **_kwargs: Any) -> None:
        self.refuse_execution()

    def list_runs(self, agent_type: str | None = None) -> list[AgentRunSummary]:
        return [self._to_run_summary(run) for run in self.repository.list_runs(agent_type=agent_type)]

    def get_run(self, run_id: str) -> AgentRunDetail:
        run = self.repository.get_run(run_id)
        if run is None:
            raise AgentIntegrationError("Agent run not found.", code="agent_invalid_response", status_code=404)
        summary = self._to_run_summary(run)
        return AgentRunDetail(
            **summary.model_dump(),
            correlation_id=run.correlation_id,
            idempotency_key=run.idempotency_key,
            contract_version=run.contract_version,
            request_payload=redact_payload(run.request_payload or {}),
            response_payload=redact_payload(run.response_payload) if run.response_payload else None,
            validation_errors=run.validation_errors or [],
            mapping_warnings=run.mapping_warnings or [],
            error_message=run.error_message,
        )

    def list_findings(self) -> list[AgentFindingRecord]:
        return [self._to_finding(row) for row in self.repository.list_findings()]

    def get_finding(self, finding_id: UUID) -> AgentFindingRecord:
        row = self.repository.get_finding(finding_id)
        if row is None:
            raise AgentIntegrationError("Agent finding not found.", code="agent_invalid_response", status_code=404)
        return self._to_finding(row)

    def list_recommendations(self) -> list[AgentRecommendationRecord]:
        return [self._to_recommendation(row) for row in self.repository.list_recommendations()]

    def get_recommendation(self, recommendation_id: UUID) -> AgentRecommendationRecord:
        row = self.repository.get_recommendation(recommendation_id)
        if row is None:
            raise AgentIntegrationError("Agent recommendation not found.", code="agent_invalid_response", status_code=404)
        return self._to_recommendation(row)

    def _to_finding(self, row: AgentFinding) -> AgentFindingRecord:
        return AgentFindingRecord(
            id=row.id,
            run_id=row.run.public_id if row.run else "",
            provider=row.provider,
            external_anomaly_id=row.external_anomaly_id,
            classification=row.classification,
            classification_label=CLASSIFICATION_LABELS.get(row.classification, row.classification),
            severity_tier=row.severity_tier,
            severity_label=SEVERITY_LABELS.get(row.severity_tier, f"Tier {row.severity_tier}"),
            confidence_score=row.confidence_score,
            external_cluster_id=row.external_cluster_id,
            external_segment_id=row.external_segment_id,
            external_valve_id=row.external_valve_id,
            mapped_detection_id=row.mapped_detection_id,
            mapped_sensor_id=row.mapped_sensor_id,
            mapped_segment_id=row.mapped_segment_id,
            mapped_valve_id=row.mapped_valve_id,
            mapping_status=row.mapping_status,
            review_status=row.review_status,
            network_status=row.network_status,
            physical_deviations=row.physical_deviations,
            criticality_metrics=row.criticality_metrics,
            operator_justification=row.operator_justification,
            data_mode=row.run.data_mode if row.run is not None else "simulated",
            created_at=row.created_at,
        )

    def _to_recommendation(self, row: AgentResponseRecommendation) -> AgentRecommendationRecord:
        return AgentRecommendationRecord(
            id=row.id,
            run_id=row.run.public_id if row.run else "",
            provider=row.provider,
            external_result_id=row.external_result_id,
            external_incident_id=row.external_incident_id,
            external_cluster_id=row.external_cluster_id,
            external_device_id=row.external_device_id,
            mapped_incident_number=row.mapped_incident_number,
            mapped_device_id=row.mapped_device_id,
            incident_attached=row.incident_id is not None,
            severity_tier=row.severity_tier,
            severity_label=SEVERITY_LABELS.get(row.severity_tier, f"Tier {row.severity_tier}"),
            decision=row.decision,
            reachability=row.reachability,
            notification_sent=False,
            notification_verified=False,
            valve_command_sent=row.valve_command_sent,
            valve_command_confirmed=row.valve_command_confirmed,
            valve_command_verified=False,
            human_override_requested=row.human_override_requested,
            human_override_response=row.human_override_response,
            reasoning_trace=row.reasoning_trace,
            safety_status=row.safety_status,
            created_at=row.created_at,
        )

    def _require_ingest(self) -> None:
        if not self.settings.agent_result_ingest_enabled:
            raise AgentIntegrationError(
                "Agent result ingest is disabled.",
                code="agent_ingest_disabled",
                status_code=503,
            )

    def _resolve_detection(self, mapper, anomaly_id: str) -> MappingLookup:
        lookup = mapper.resolve("detection", anomaly_id)
        if anomaly_id.startswith("DET-"):
            detection = self.session.scalar(
                select(AnomalyDetection).where(AnomalyDetection.detection_number == anomaly_id)
            )
            if detection is not None:
                return MappingLookup(anomaly_id, "detection", anomaly_id, True, None)
        return lookup

    def _detection_row(self, public_id: str | None) -> AnomalyDetection | None:
        if not public_id:
            return None
        return self.session.scalar(select(AnomalyDetection).where(AnomalyDetection.detection_number == public_id))

    def _accepted(self, *, agent: str, run: AgentRunDetail, created: int, duplicates: int) -> AgentIngestAccepted:
        unmapped = sorted(
            {
                str(item.get("external_id"))
                for item in run.mapping_warnings
                if isinstance(item, dict) and item.get("external_id")
            }
        )
        return AgentIngestAccepted(
            status="accepted",
            agent=agent,
            run_id=run.run_id,
            created=created,
            duplicates=duplicates,
            unmapped_ids=unmapped,
        )

    def accept_investigation_result(
        self,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> AgentIngestAccepted:
        self._require_ingest()
        try:
            parsed = parse_investigation_response(payload)
        except (ValidationError, ValueError) as exc:
            raise AgentIntegrationError(
                "The investigation response was rejected.",
                code="agent_result_rejected",
                status_code=422,
            ) from exc
        key = idempotency_key or f"investigation:{parsed.batch.batch_id}"
        existing = self.repository.get_run_by_idempotency(key)
        run = self.ingest_investigation_result(payload, idempotency_key=key)
        count = len(parsed.batch.investigated_threats)
        return self._accepted(
            agent=INVESTIGATION_AGENT,
            run=run,
            created=0 if existing else count,
            duplicates=count if existing else 0,
        )

    def accept_response_result(
        self,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> AgentIngestAccepted:
        self._require_ingest()
        try:
            parsed = parse_response_result(payload)
        except (ValidationError, ValueError) as exc:
            raise AgentIntegrationError(
                "The response result was rejected.",
                code="agent_result_rejected",
                status_code=422,
            ) from exc
        key = idempotency_key or f"response:{parsed.result_id}"
        existing = self.repository.get_run_by_idempotency(key)
        run = self.ingest_response_result(payload, idempotency_key=key)
        return self._accepted(
            agent=RESPONSE_AGENT,
            run=run,
            created=0 if existing else 1,
            duplicates=1 if existing else 0,
        )

    def ingest_investigation_result(
        self,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        source_public_id: str | None = None,
    ) -> AgentRunDetail:
        try:
            parsed = parse_investigation_response(payload)
        except (ValidationError, ValueError) as exc:
            self.session.rollback()
            raise AgentIntegrationError(
                "The investigation response was rejected.",
                code="agent_result_rejected",
                status_code=422,
            ) from exc

        batch_id = parsed.batch.batch_id
        key = idempotency_key or f"investigation:{batch_id}"
        existing = self.repository.get_run_by_idempotency(key)
        if existing is not None:
            return self.get_run(existing.public_id)

        for threat in parsed.batch.investigated_threats:
            found = self.repository.get_finding_by_anomaly(INVESTIGATION_AGENT, threat.anomaly_id)
            if found is not None:
                raise AgentIntegrationError(
                    "An investigation finding with this anomaly_id already exists.",
                    code="agent_result_duplicate",
                    status_code=409,
                )

        integration = self.repository.get_integration(INVESTIGATION_AGENT)
        if integration is None:
            raise AgentIntegrationError("The agent is not configured.", code="agent_not_configured", status_code=503)

        started = utc_now()
        run = AgentRun(
            public_id=self.repository.next_run_public_id(),
            agent_integration_id=integration.id,
            agent_type=INVESTIGATION_AGENT,
            contract_version=CONTRACT_VERSION,
            status="validating",
            correlation_id=str(uuid4()),
            idempotency_key=key,
            source_type="investigation_batch",
            source_public_id=source_public_id or batch_id,
            request_payload=redact_payload({"batch_id": batch_id}),
            response_payload=redact_payload(parsed.model_dump(mode="json")),
            started_at=started,
            data_mode=parsed.data_mode,
        )
        self.repository.add_run(run)
        self.session.flush()

        mapper = investigation_mapper(self.session)
        warnings: list[dict[str, Any]] = []
        try:
            for threat in parsed.batch.investigated_threats:
                cluster = mapper.resolve("sensor_cluster", threat.sensor_cluster_id)
                segment = mapper.resolve("segment", threat.segment_id)
                valve = mapper.resolve("valve", threat.criticality_metrics.associated_valve_id)
                detection = self._resolve_detection(mapper, threat.anomaly_id)
                detection_row = self._detection_row(detection.internal_public_id)
                for lookup in (cluster, segment, valve, detection):
                    if lookup.warning:
                        warnings.append(lookup.warning)
                mapped_ids = [cluster.internal_public_id, segment.internal_public_id, valve.internal_public_id]
                present = [item for item in mapped_ids if item]
                if present and len(present) == 3:
                    mapping_status = "mapped"
                elif present or detection.mapped:
                    mapping_status = "partial"
                else:
                    mapping_status = "unmapped"
                self.repository.add_finding(
                    AgentFinding(
                        provider=INVESTIGATION_AGENT,
                        external_anomaly_id=threat.anomaly_id,
                        agent_run_id=run.id,
                        classification=threat.classification,
                        severity_tier=threat.severity_tier,
                        confidence_score=threat.confidence_score,
                        external_cluster_id=threat.sensor_cluster_id,
                        external_segment_id=threat.segment_id,
                        external_valve_id=threat.criticality_metrics.associated_valve_id,
                        anomaly_detection_id=detection_row.id if detection_row is not None else None,
                        mapped_detection_id=detection.internal_public_id,
                        mapped_segment_id=segment.internal_public_id,
                        mapped_valve_id=valve.internal_public_id,
                        network_status=threat.network_status.model_dump(mode="json"),
                        physical_deviations=threat.physical_deviations.model_dump(mode="json"),
                        criticality_metrics=threat.criticality_metrics.model_dump(mode="json"),
                        operator_justification=threat.operator_justification,
                        mapping_status=mapping_status,
                        raw_finding=redact_payload(threat.model_dump(mode="json")),
                    )
                )
            run.status = "succeeded"
            run.mapping_warnings = warnings
            run.completed_at = utc_now()
            run.duration_ms = int((run.completed_at - started).total_seconds() * 1000)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return self.get_run(run.public_id)

    def ingest_response_result(
        self,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> AgentRunDetail:
        try:
            parsed = parse_response_result(payload)
        except (ValidationError, ValueError) as exc:
            self.session.rollback()
            raise AgentIntegrationError(
                "The response result was rejected.",
                code="agent_result_rejected",
                status_code=422,
            ) from exc

        key = idempotency_key or f"response:{parsed.result_id}"
        existing = self.repository.get_run_by_idempotency(key)
        if existing is not None:
            return self.get_run(existing.public_id)
        duplicate = self.repository.get_recommendation_by_result(RESPONSE_AGENT, parsed.result_id)
        if duplicate is not None:
            raise AgentIntegrationError(
                "A response recommendation with this result_id already exists.",
                code="agent_result_duplicate",
                status_code=409,
            )

        integration = self.repository.get_integration(RESPONSE_AGENT)
        if integration is None:
            raise AgentIntegrationError("The agent is not configured.", code="agent_not_configured", status_code=503)

        started = utc_now()
        run = AgentRun(
            public_id=self.repository.next_run_public_id(),
            agent_integration_id=integration.id,
            agent_type=RESPONSE_AGENT,
            contract_version=CONTRACT_VERSION,
            status="validating",
            correlation_id=str(uuid4()),
            idempotency_key=key,
            source_type="response_recommendation",
            source_public_id=parsed.incident_id,
            request_payload=redact_payload({"result_id": parsed.result_id}),
            response_payload=redact_payload(parsed.model_dump(mode="json")),
            started_at=started,
            data_mode="simulated",
        )
        self.repository.add_run(run)
        self.session.flush()

        mapper = response_mapper(self.session)
        warnings: list[dict[str, Any]] = []
        incident_lookup = mapper.resolve("incident", parsed.incident_id)
        cluster_lookup = mapper.resolve("sensor_cluster", parsed.cluster_id)
        device_lookup = mapper.resolve("device", parsed.device_id)
        if not device_lookup.mapped:
            device_lookup = mapper.resolve("valve", parsed.device_id)
        for lookup in (incident_lookup, cluster_lookup, device_lookup):
            if lookup.warning:
                warnings.append(lookup.warning)

        incident_pk = None
        if incident_lookup.mapped and incident_lookup.internal_public_id:
            incident = self.session.scalar(
                select(Incident).where(Incident.incident_number == incident_lookup.internal_public_id)
            )
            incident_pk = incident.id if incident else None

        safety = evaluate_response_safety(parsed)
        _ = never_infer_human_approval(parsed)

        try:
            self.repository.add_recommendation(
                AgentResponseRecommendation(
                    provider=RESPONSE_AGENT,
                    external_result_id=parsed.result_id,
                    agent_run_id=run.id,
                    incident_id=incident_pk,
                    external_incident_id=parsed.incident_id,
                    external_cluster_id=parsed.cluster_id,
                    external_device_id=parsed.device_id,
                    mapped_incident_number=incident_lookup.internal_public_id,
                    mapped_device_id=device_lookup.internal_public_id,
                    severity_tier=parsed.severity_tier,
                    decision=parsed.decision,
                    reachability=parsed.reachability,
                    notification_sent=False,
                    valve_command_sent=parsed.valve_command_sent,
                    valve_command_confirmed=parsed.valve_command_confirmed,
                    human_override_requested=parsed.human_override_requested,
                    human_override_response=parsed.human_override_response,
                    reasoning_trace=parsed.reasoning_trace,
                    safety_status=safety["safety_status"],
                    raw_result=redact_payload(parsed.model_dump(mode="json")),
                )
            )
            run.status = "succeeded"
            run.mapping_warnings = warnings
            run.completed_at = utc_now()
            run.duration_ms = int((run.completed_at - started).total_seconds() * 1000)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise AgentIntegrationError(
                "A response recommendation with this result_id already exists.",
                code="agent_result_duplicate",
                status_code=409,
            )
        except Exception:
            self.session.rollback()
            raise
        return self.get_run(run.public_id)
