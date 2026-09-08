"""Seed-source incident catalog.

Runtime API routes must not query this module. Values here are frozen so
database seeds stay identical across runs.
"""

from datetime import datetime, timedelta, timezone

from app.schemas.incidents import (
    Classification,
    IncidentDetail,
    IncidentStatus,
    IncidentTelemetryPoint,
    SeverityTier,
    TimelineEvent,
    TimelineSource,
)

SEED_NOW = datetime(2026, 9, 1, 7, 45, tzinfo=timezone.utc)


def _now() -> datetime:
    return SEED_NOW


def _ago(*, hours: float = 0, minutes: int = 0) -> datetime:
    return _now() - timedelta(hours=hours, minutes=minutes)


def _telemetry(
    detected_at: datetime,
    *,
    base_pressure: float,
    pressure_delta: float,
    base_flow: float,
    flow_delta: float,
    base_loss: float,
    loss_delta: float,
) -> list[IncidentTelemetryPoint]:
    points: list[IncidentTelemetryPoint] = []
    for index in range(16):
        offset = index - 10
        timestamp = detected_at + timedelta(minutes=5 * offset)
        progressed = 0.0 if index < 10 else min(1.0, (index - 9) / 4)
        points.append(
            IncidentTelemetryPoint(
                timestamp=timestamp,
                pressure=round(base_pressure + pressure_delta * progressed, 2),
                flow_rate=round(base_flow + flow_delta * progressed, 1),
                packet_loss=round(base_loss + loss_delta * progressed, 2),
                is_detection=index == 10,
            )
        )
    return points


def _evidence(*items: tuple[str, str, str, str]) -> list[dict[str, str]]:
    return [
        {"id": item_id, "kind": kind, "title": title, "detail": detail}
        for item_id, kind, title, detail in items
    ]


def _build_incidents() -> list[IncidentDetail]:
    leak_harbour = _ago(hours=3, minutes=18)
    leak_corniche = _ago(hours=2, minutes=8)
    connectivity_alain = _ago(hours=1, minutes=42)
    pressure_jeddah = _ago(hours=1, minutes=14)
    sensor_doha = _ago(minutes=58)
    pressure_muscat = _ago(minutes=41)
    insufficient_casa = _ago(minutes=33)
    demand_riyadh = _ago(hours=4, minutes=10)
    connectivity_amman = _ago(hours=5, minutes=20)

    return [
        IncidentDetail(
            id="INC-1842",
            incident_number="INC-1842",
            title="Confirmed leak on Corniche trunk main",
            classification=Classification.confirmed_leak,
            severity=SeverityTier.tier_3,
            status=IncidentStatus.investigating,
            zone="Corniche DMA",
            pipeline_segment="Corniche Trunk Main · KM 4.2",
            location="Corniche DMA · Corniche Trunk Main",
            detected_at=leak_corniche,
            updated_at=_ago(minutes=12),
            estimated_water_loss_m3=28.4,
            assigned_operator="Layla Al Mansoori",
            confidence=92.0,
            sensor="SNS-CRN-014",
            associated_valve="VLV-CRN-014",
            latitude=24.4762,
            longitude=54.3371,
            population_affected=18400,
            current_summary=(
                "A sustained night-time pressure drop with a matching flow increase on the "
                "Corniche trunk indicates a confirmed burst downstream of valve VLV-CRN-014."
            ),
            pressure_change_bar=-0.62,
            flow_change_m3h=38.5,
            network_condition="Local isolation in progress; adjacent DMAs stable",
            signal_strength_dbm=-71,
            packet_loss_percent=0.8,
            device_reachability="Unavailable",
            network_priority_status="Unavailable",
            agent_investigation_summary="Awaiting Investigation Agent result",
            recommended_action=(
                "Keep the isolation valve closed, dispatch the Corniche repair crew, and "
                "maintain CAMARA network priority until pressure recovers."
            ),
            evidence=_evidence(
                ("ev-1842-1", "telemetry_window", "Telemetry window", "05:20–06:20 UTC pressure and flow series"),
                ("ev-1842-2", "threshold_trigger", "Threshold trigger", "Pressure fell 0.62 bar below night envelope"),
                ("ev-1842-3", "connectivity_check", "Connectivity check", "SNS-CRN-014 reachable with 0.8% packet loss"),
                ("ev-1842-4", "historical_baseline", "Historical baseline", "Same hour last 14 days: 4.18 bar, 186 m³/h"),
                ("ev-1842-5", "topology", "Topology / criticality", "Trunk feeds two coastal districts; criticality high"),
            ),
            telemetry=_telemetry(
                leak_corniche,
                base_pressure=4.18,
                pressure_delta=-0.62,
                base_flow=186.0,
                flow_delta=38.5,
                base_loss=0.4,
                loss_delta=0.4,
            ),
        ),
        IncidentDetail(
            id="INC-1835",
            incident_number="INC-1835",
            title="Confirmed leak on Harbour transfer main",
            classification=Classification.confirmed_leak,
            severity=SeverityTier.tier_3,
            status=IncidentStatus.awaiting_approval,
            zone="Dubai Harbour",
            pipeline_segment="Harbour Transfer Main · Segment 7",
            location="Dubai Harbour · Harbour Transfer Main",
            detected_at=leak_harbour,
            updated_at=_ago(minutes=7),
            estimated_water_loss_m3=41.2,
            assigned_operator="Omar Haddad",
            confidence=88.0,
            sensor="SNS-HBR-007",
            associated_valve="VLV-HBR-007",
            latitude=25.0894,
            longitude=55.1392,
            population_affected=22600,
            current_summary=(
                "A sharp pressure collapse on the Harbour transfer main is consistent with a "
                "confirmed leak. Isolation is recommended and waiting for operator approval."
            ),
            pressure_change_bar=-0.84,
            flow_change_m3h=52.1,
            network_condition="Priority requested; valve still open",
            signal_strength_dbm=-74,
            packet_loss_percent=1.1,
            device_reachability="Unavailable",
            network_priority_status="Unavailable",
            agent_investigation_summary="Awaiting Investigation Agent result",
            recommended_action=(
                "Approve isolation of VLV-HBR-007 and notify the Harbour DMA duty crew. "
                "Hold network priority until the valve is confirmed closed."
            ),
            evidence=_evidence(
                ("ev-1835-1", "telemetry_window", "Telemetry window", "03:40–04:40 UTC dual-sensor series"),
                ("ev-1835-2", "threshold_trigger", "Threshold trigger", "Rate-of-change exceeded 0.20 bar / 5 min"),
                ("ev-1835-3", "connectivity_check", "Connectivity check", "SNS-HBR-007 and gateway HBR-GW-02 online"),
                ("ev-1835-4", "historical_baseline", "Historical baseline", "No similar night drop in 30-day baseline"),
                ("ev-1835-5", "topology", "Topology / criticality", "Transfer main supplies Harbour and Jebel Ali fringe"),
            ),
            telemetry=_telemetry(
                leak_harbour,
                base_pressure=4.32,
                pressure_delta=-0.84,
                base_flow=214.0,
                flow_delta=52.1,
                base_loss=0.5,
                loss_delta=0.6,
            ),
        ),
        IncidentDetail(
            id="INC-1841",
            incident_number="INC-1841",
            title="Sensor connectivity degradation in Al Ain North",
            classification=Classification.connectivity_degradation,
            severity=SeverityTier.tier_2,
            status=IncidentStatus.investigating,
            zone="Al Ain North",
            pipeline_segment="Al Ain Feeder 3",
            location="Al Ain North · Al Ain Feeder 3",
            detected_at=connectivity_alain,
            updated_at=_ago(minutes=9),
            estimated_water_loss_m3=0.0,
            assigned_operator="Noura Al Kaabi",
            confidence=81.0,
            sensor="SNS-AIN-221",
            associated_valve="VLV-AIN-018",
            latitude=24.2321,
            longitude=55.7614,
            population_affected=0,
            current_summary=(
                "A cluster of Al Ain North sensors is retrying packets. Hydraulic values still "
                "look healthy, so this is being treated as a connectivity incident."
            ),
            pressure_change_bar=-0.04,
            flow_change_m3h=2.1,
            network_condition="Gateway reachable; field radios degrading",
            signal_strength_dbm=-91,
            packet_loss_percent=6.8,
            device_reachability="Unavailable",
            network_priority_status="Unavailable",
            agent_investigation_summary="Awaiting Investigation Agent result",
            recommended_action=(
                "Request a CAMARA quality boost for the Al Ain North cluster and schedule a "
                "radio check at feeder chamber 3. Do not isolate the valve."
            ),
            evidence=_evidence(
                ("ev-1841-1", "telemetry_window", "Telemetry window", "Packet-loss series for SNS-AIN-221"),
                ("ev-1841-2", "threshold_trigger", "Threshold trigger", "Packet loss crossed 5% for 15 minutes"),
                ("ev-1841-3", "connectivity_check", "Connectivity check", "Gateway AIN-GW-01 reachable; last hop weak"),
                ("ev-1841-4", "historical_baseline", "Historical baseline", "Typical packet loss 0.6% at this hour"),
                ("ev-1841-5", "topology", "Topology / criticality", "Feeder 3 is monitored by four redundant sensors"),
            ),
            telemetry=_telemetry(
                connectivity_alain,
                base_pressure=4.05,
                pressure_delta=-0.04,
                base_flow=142.0,
                flow_delta=2.1,
                base_loss=0.8,
                loss_delta=6.0,
            ),
        ),
        IncidentDetail(
            id="INC-1833",
            incident_number="INC-1833",
            title="Pressure anomaly on Jeddah North feeder",
            classification=Classification.pressure_anomaly,
            severity=SeverityTier.tier_2,
            status=IncidentStatus.investigating,
            zone="Jeddah North",
            pipeline_segment="Obhur Feeder · Node 12",
            location="Jeddah North · Obhur Feeder",
            detected_at=pressure_jeddah,
            updated_at=_ago(minutes=18),
            estimated_water_loss_m3=4.6,
            assigned_operator="Hassan Farouk",
            confidence=74.0,
            sensor="SNS-JED-112",
            associated_valve="VLV-JED-112",
            latitude=21.7536,
            longitude=39.1268,
            population_affected=6200,
            current_summary=(
                "Obhur Feeder pressure dipped below the morning envelope without a matching "
                "step-change in billed demand. Investigation is still open."
            ),
            pressure_change_bar=-0.31,
            flow_change_m3h=9.4,
            network_condition="Stable connectivity; hydraulic deviation local",
            signal_strength_dbm=-69,
            packet_loss_percent=0.5,
            device_reachability="Unavailable",
            network_priority_status="Unavailable",
            agent_investigation_summary="Awaiting Investigation Agent result",
            recommended_action=(
                "Keep VLV-JED-112 under watch, compare with the next two downstream sensors, "
                "and escalate to leak only if the drop persists for another 20 minutes."
            ),
            evidence=_evidence(
                ("ev-1833-1", "telemetry_window", "Telemetry window", "Morning ramp on Obhur Feeder"),
                ("ev-1833-2", "threshold_trigger", "Threshold trigger", "Pressure 0.31 bar below expected ramp"),
                ("ev-1833-3", "connectivity_check", "Connectivity check", "SNS-JED-112 healthy, RSSI -69 dBm"),
                ("ev-1833-4", "historical_baseline", "Historical baseline", "Weekday morning ramp usually +0.22 bar"),
                ("ev-1833-5", "topology", "Topology / criticality", "Feeder supplies Obhur and a hospital campus"),
            ),
            telemetry=_telemetry(
                pressure_jeddah,
                base_pressure=3.96,
                pressure_delta=-0.31,
                base_flow=168.0,
                flow_delta=9.4,
                base_loss=0.3,
                loss_delta=0.2,
            ),
        ),
        IncidentDetail(
            id="INC-1838",
            incident_number="INC-1838",
            title="Sensor fault on Lusail district meter",
            classification=Classification.sensor_fault,
            severity=SeverityTier.tier_2,
            status=IncidentStatus.investigating,
            zone="Doha West",
            pipeline_segment="Lusail Distributor 2",
            location="Doha West · Lusail Distributor 2",
            detected_at=sensor_doha,
            updated_at=_ago(minutes=21),
            estimated_water_loss_m3=0.0,
            assigned_operator=None,
            confidence=79.0,
            sensor="SNS-DOH-044",
            associated_valve="VLV-DOH-044",
            latitude=25.3742,
            longitude=51.4906,
            population_affected=0,
            current_summary=(
                "SNS-DOH-044 is reporting physically impossible pressure spikes while neighbour "
                "sensors stay flat. The likely cause is a faulty transducer, not a network event."
            ),
            pressure_change_bar=1.84,
            flow_change_m3h=-1.2,
            network_condition="Device online; measurement integrity failed",
            signal_strength_dbm=-66,
            packet_loss_percent=0.3,
            device_reachability="Unavailable",
            network_priority_status="Unavailable",
            agent_investigation_summary="Awaiting Investigation Agent result",
            recommended_action=(
                "Flag SNS-DOH-044 for field replacement and exclude it from leak detection "
                "until the spare is commissioned. No valve movement is required."
            ),
            evidence=_evidence(
                ("ev-1838-1", "telemetry_window", "Telemetry window", "Impossible 1.8 bar spikes on a single node"),
                ("ev-1838-2", "threshold_trigger", "Threshold trigger", "Sensor integrity score fell below 0.4"),
                ("ev-1838-3", "connectivity_check", "Connectivity check", "Radio path healthy; issue is measurement"),
                ("ev-1838-4", "historical_baseline", "Historical baseline", "Device drifted 0.3 bar over seven days"),
                ("ev-1838-5", "topology", "Topology / criticality", "Distributor 2 still covered by SNS-DOH-043"),
            ),
            telemetry=_telemetry(
                sensor_doha,
                base_pressure=4.11,
                pressure_delta=1.84,
                base_flow=121.0,
                flow_delta=-1.2,
                base_loss=0.3,
                loss_delta=0.0,
            ),
        ),
        IncidentDetail(
            id="INC-1840",
            incident_number="INC-1840",
            title="Pressure anomaly on Mutrah distributor",
            classification=Classification.pressure_anomaly,
            severity=SeverityTier.tier_1,
            status=IncidentStatus.investigating,
            zone="Muscat Old Town",
            pipeline_segment="Mutrah Distributor",
            location="Muscat Old Town · Mutrah Distributor",
            detected_at=pressure_muscat,
            updated_at=_ago(minutes=6),
            estimated_water_loss_m3=1.2,
            assigned_operator="Fatima Al Lawati",
            confidence=64.0,
            sensor="SNS-MCT-009",
            associated_valve="VLV-MCT-009",
            latitude=23.6164,
            longitude=58.5662,
            population_affected=2100,
            current_summary=(
                "A modest pressure dip appeared on the Mutrah distributor during the morning "
                "fill. Neighbouring sensors recovered, so the incident is being monitored."
            ),
            pressure_change_bar=-0.18,
            flow_change_m3h=5.2,
            network_condition="Within operating range after recovery",
            signal_strength_dbm=-72,
            packet_loss_percent=0.4,
            device_reachability="Unavailable",
            network_priority_status="Unavailable",
            agent_investigation_summary="Awaiting Investigation Agent result",
            recommended_action=(
                "Monitor for one more fill cycle. Escalate only if pressure fails to recover "
                "or if Mutrah tank outflow diverges from the model."
            ),
            evidence=_evidence(
                ("ev-1840-1", "telemetry_window", "Telemetry window", "Morning fill on Mutrah Distributor"),
                ("ev-1840-2", "threshold_trigger", "Threshold trigger", "Soft envelope breach of 0.18 bar"),
                ("ev-1840-3", "connectivity_check", "Connectivity check", "All Mutrah nodes reachable"),
                ("ev-1840-4", "historical_baseline", "Historical baseline", "Similar dips on 3 of last 10 weekdays"),
                ("ev-1840-5", "topology", "Topology / criticality", "Old Town mesh has alternate feed from Ruwi"),
            ),
            telemetry=_telemetry(
                pressure_muscat,
                base_pressure=3.88,
                pressure_delta=-0.18,
                base_flow=96.0,
                flow_delta=5.2,
                base_loss=0.4,
                loss_delta=0.0,
            ),
        ),
        IncidentDetail(
            id="INC-1836",
            incident_number="INC-1836",
            title="Insufficient data on Medina ring main",
            classification=Classification.insufficient_data,
            severity=SeverityTier.tier_1,
            status=IncidentStatus.investigating,
            zone="Casablanca Medina",
            pipeline_segment="Medina Ring Main · Arc B",
            location="Casablanca Medina · Medina Ring Main",
            detected_at=insufficient_casa,
            updated_at=_ago(minutes=14),
            estimated_water_loss_m3=0.0,
            assigned_operator=None,
            confidence=41.0,
            sensor="SNS-CAS-031",
            associated_valve="VLV-CAS-031",
            latitude=33.5993,
            longitude=-7.6164,
            population_affected=0,
            current_summary=(
                "The detector received an incomplete 20-minute window from Arc B. There is not "
                "enough clean telemetry to classify a hydraulic event."
            ),
            pressure_change_bar=0.0,
            flow_change_m3h=0.0,
            network_condition="Intermittent payload gaps on Arc B",
            signal_strength_dbm=-88,
            packet_loss_percent=4.2,
            device_reachability="Unavailable",
            network_priority_status="Unavailable",
            agent_investigation_summary="Awaiting Investigation Agent result",
            recommended_action=(
                "Wait for the next complete telemetry window and keep the incident open. Do not "
                "operate VLV-CAS-031 on incomplete evidence."
            ),
            evidence=_evidence(
                ("ev-1836-1", "telemetry_window", "Telemetry window", "Only 5 of 12 frames received"),
                ("ev-1836-2", "threshold_trigger", "Threshold trigger", "Completeness score 0.42, below 0.80"),
                ("ev-1836-3", "connectivity_check", "Connectivity check", "Gateway CAS-GW-04 reports retries"),
                ("ev-1836-4", "historical_baseline", "Historical baseline", "Baseline cannot be compared this hour"),
                ("ev-1836-5", "topology", "Topology / criticality", "Ring main still observed from Arc A and Arc C"),
            ),
            telemetry=_telemetry(
                insufficient_casa,
                base_pressure=3.72,
                pressure_delta=0.0,
                base_flow=88.0,
                flow_delta=0.0,
                base_loss=1.2,
                loss_delta=3.0,
            ),
        ),
        IncidentDetail(
            id="INC-1837",
            incident_number="INC-1837",
            title="Normal demand spike in Riyadh Industrial",
            classification=Classification.normal_demand_spike,
            severity=SeverityTier.tier_1,
            status=IncidentStatus.resolved,
            zone="Riyadh Industrial",
            pipeline_segment="Second Industrial Ring",
            location="Riyadh Industrial · Second Industrial Ring",
            detected_at=demand_riyadh,
            updated_at=_ago(hours=3, minutes=40),
            estimated_water_loss_m3=0.0,
            assigned_operator="Yousef Al Qahtani",
            confidence=90.0,
            sensor="SNS-RUH-078",
            associated_valve="VLV-RUH-078",
            latitude=24.5348,
            longitude=46.9051,
            population_affected=0,
            current_summary=(
                "An early-shift demand pulse looked like a leak at first glance. Billing and "
                "process-water schedules confirmed a normal industrial start-up."
            ),
            pressure_change_bar=-0.22,
            flow_change_m3h=64.0,
            network_condition="Returned to envelope after shift start",
            signal_strength_dbm=-67,
            packet_loss_percent=0.2,
            device_reachability="Unavailable",
            network_priority_status="Unavailable",
            agent_investigation_summary="Awaiting Investigation Agent result",
            recommended_action="No field action. Keep the start-up profile in the baseline model.",
            evidence=_evidence(
                ("ev-1837-1", "telemetry_window", "Telemetry window", "05:00 industrial start-up pulse"),
                ("ev-1837-2", "threshold_trigger", "Threshold trigger", "Flow step +64 m³/h with modest pressure dip"),
                ("ev-1837-3", "connectivity_check", "Connectivity check", "All industrial ring sensors healthy"),
                ("ev-1837-4", "historical_baseline", "Historical baseline", "Same shape on 11 of last 12 weekdays"),
                ("ev-1837-5", "topology", "Topology / criticality", "Ring serves process-water customers only"),
            ),
            telemetry=_telemetry(
                demand_riyadh,
                base_pressure=4.28,
                pressure_delta=-0.22,
                base_flow=240.0,
                flow_delta=64.0,
                base_loss=0.2,
                loss_delta=0.0,
            ),
        ),
        IncidentDetail(
            id="INC-1834",
            incident_number="INC-1834",
            title="Connectivity degradation on Abdali trunk",
            classification=Classification.connectivity_degradation,
            severity=SeverityTier.tier_2,
            status=IncidentStatus.resolved,
            zone="Amman Heights",
            pipeline_segment="Abdali Trunk",
            location="Amman Heights · Abdali Trunk",
            detected_at=connectivity_amman,
            updated_at=_ago(hours=1, minutes=5),
            estimated_water_loss_m3=0.0,
            assigned_operator="Rania Nasser",
            confidence=86.0,
            sensor="SNS-AMM-015",
            associated_valve="VLV-AMM-015",
            latitude=31.9634,
            longitude=35.9106,
            population_affected=0,
            current_summary=(
                "Packet loss on the Abdali trunk radios recovered after a gateway restart. The "
                "incident is resolved with no hydraulic impact."
            ),
            pressure_change_bar=0.03,
            flow_change_m3h=-1.4,
            network_condition="Restored; packet delivery back above 99%",
            signal_strength_dbm=-70,
            packet_loss_percent=0.6,
            device_reachability="Unavailable",
            network_priority_status="Unavailable",
            agent_investigation_summary="Awaiting Investigation Agent result",
            recommended_action="No further action. Record the gateway restart in the asset log.",
            evidence=_evidence(
                ("ev-1834-1", "telemetry_window", "Telemetry window", "Radio retry storm then recovery"),
                ("ev-1834-2", "threshold_trigger", "Threshold trigger", "Packet loss peaked at 9.4%"),
                ("ev-1834-3", "connectivity_check", "Connectivity check", "AMM-GW-03 restarted at 04:12 UTC"),
                ("ev-1834-4", "historical_baseline", "Historical baseline", "Pressure stayed within 0.05 bar"),
                ("ev-1834-5", "topology", "Topology / criticality", "Abdali trunk has dual radio paths"),
            ),
            telemetry=_telemetry(
                connectivity_amman,
                base_pressure=4.02,
                pressure_delta=0.03,
                base_flow=133.0,
                flow_delta=-1.4,
                base_loss=0.5,
                loss_delta=0.1,
            ),
        ),
    ]


def _build_timelines() -> dict[str, list[TimelineEvent]]:
    incidents = {incident.id: incident for incident in get_incidents()}

    def events_for(
        incident_id: str,
        rows: list[tuple[int, str, str, str, TimelineSource, str]],
    ) -> list[TimelineEvent]:
        detected = incidents[incident_id].detected_at
        return [
            TimelineEvent(
                id=f"{incident_id}-evt-{index + 1}",
                timestamp=detected + timedelta(minutes=offset),
                event_type=event_type,
                title=title,
                description=description,
                source=source,
                status=status,
            )
            for index, (offset, event_type, title, description, source, status) in enumerate(rows)
        ]

    return {
        "INC-1842": events_for(
            "INC-1842",
            [
                (0, "anomaly_detected", "Anomaly detected", "Night envelope breach on SNS-CRN-014.", TimelineSource.detector, "Complete"),
                (4, "investigation_started", "Investigation started", "Operator opened a leak investigation.", TimelineSource.system, "Complete"),
                (7, "reachability_checked", "Device reachability checked", "Sensor and Corniche gateway both reachable.", TimelineSource.network, "Complete"),
                (11, "incident_classified", "Incident classified", "Operator classified this as a confirmed leak on the trunk main.", TimelineSource.system, "Complete"),
                (13, "severity_assigned", "Severity assigned", "Severity set to Tier 3 because of coastal DMA impact.", TimelineSource.system, "Complete"),
                (16, "network_priority_requested", "Network priority requested", "CAMARA quality-on-demand requested for field telemetry.", TimelineSource.network, "Complete"),
                (21, "operator_notified", "Operator notified", "Layla Al Mansoori acknowledged the recommended isolation.", TimelineSource.operator, "Complete"),
            ],
        ),
        "INC-1835": events_for(
            "INC-1835",
            [
                (0, "anomaly_detected", "Anomaly detected", "Rapid pressure collapse on Harbour Segment 7.", TimelineSource.detector, "Complete"),
                (3, "investigation_started", "Investigation started", "Harbour and Jebel Ali fringe sensors were compared.", TimelineSource.system, "Complete"),
                (8, "reachability_checked", "Device reachability checked", "SNS-HBR-007 reachable with mild packet loss.", TimelineSource.network, "Complete"),
                (12, "incident_classified", "Incident classified", "Operator confirmed a leak; demand spike rejected.", TimelineSource.system, "Complete"),
                (14, "severity_assigned", "Severity assigned", "Severity set to Tier 3 due to transfer-main criticality.", TimelineSource.system, "Complete"),
                (18, "network_priority_requested", "Network priority requested", "Priority requested ahead of isolation.", TimelineSource.network, "Complete"),
                (24, "operator_notified", "Operator notified", "Omar Haddad asked to approve isolation of VLV-HBR-007.", TimelineSource.operator, "Waiting"),
            ],
        ),
        "INC-1841": events_for(
            "INC-1841",
            [
                (0, "anomaly_detected", "Anomaly detected", "Packet loss on Al Ain Feeder 3 crossed 5%.", TimelineSource.detector, "Complete"),
                (5, "investigation_started", "Investigation started", "Connectivity-first investigation started.", TimelineSource.system, "Complete"),
                (8, "reachability_checked", "Device reachability checked", "Gateway healthy; last-hop radio weak.", TimelineSource.network, "Complete"),
                (15, "incident_classified", "Incident classified", "Recorded as connectivity degradation; hydraulics remain stable.", TimelineSource.system, "Complete"),
                (17, "severity_assigned", "Severity assigned", "Severity set to Tier 2 because monitoring coverage is reduced.", TimelineSource.system, "Complete"),
                (22, "network_priority_requested", "Network priority requested", "Quality boost requested for the Al Ain cluster.", TimelineSource.network, "Complete"),
                (28, "operator_notified", "Operator notified", "Noura Al Kaabi is coordinating a radio check.", TimelineSource.operator, "Complete"),
            ],
        ),
        "INC-1833": events_for(
            "INC-1833",
            [
                (0, "anomaly_detected", "Anomaly detected", "Obhur Feeder missed the expected morning ramp.", TimelineSource.detector, "Complete"),
                (6, "investigation_started", "Investigation started", "Downstream hospital sensors are being compared.", TimelineSource.system, "Complete"),
                (9, "reachability_checked", "Device reachability checked", "Jeddah North radios are healthy.", TimelineSource.network, "Complete"),
                (14, "incident_classified", "Incident classified", "Recorded as a pressure anomaly; leak not yet confirmed.", TimelineSource.system, "Complete"),
                (16, "severity_assigned", "Severity assigned", "Severity set to Tier 2 while the hospital campus is in the feed path.", TimelineSource.system, "Complete"),
                (20, "network_priority_requested", "Network priority requested", "No CAMARA boost required yet.", TimelineSource.system, "Skipped"),
                (25, "operator_notified", "Operator notified", "Hassan Farouk is watching the next 20 minutes.", TimelineSource.operator, "Complete"),
            ],
        ),
        "INC-1838": events_for(
            "INC-1838",
            [
                (0, "anomaly_detected", "Anomaly detected", "Impossible pressure spikes on SNS-DOH-044.", TimelineSource.detector, "Complete"),
                (4, "investigation_started", "Investigation started", "Neighbour comparison started.", TimelineSource.system, "Complete"),
                (6, "reachability_checked", "Device reachability checked", "Radio path is healthy; values are not.", TimelineSource.network, "Complete"),
                (10, "incident_classified", "Incident classified", "Recorded as a sensor fault rather than a hydraulic event.", TimelineSource.system, "Complete"),
                (12, "severity_assigned", "Severity assigned", "Severity set to Tier 2 until a spare meter is in place.", TimelineSource.system, "Complete"),
                (15, "network_priority_requested", "Network priority requested", "Not required for a measurement fault.", TimelineSource.system, "Skipped"),
                (18, "operator_notified", "Operator notified", "Unassigned; waiting for a Doha West operator.", TimelineSource.system, "Waiting"),
            ],
        ),
        "INC-1840": events_for(
            "INC-1840",
            [
                (0, "anomaly_detected", "Anomaly detected", "Soft envelope breach during Mutrah fill.", TimelineSource.detector, "Complete"),
                (5, "investigation_started", "Investigation started", "Ruwi alternate feed was compared.", TimelineSource.system, "Complete"),
                (8, "reachability_checked", "Device reachability checked", "Old Town mesh reachable.", TimelineSource.network, "Complete"),
                (12, "incident_classified", "Incident classified", "Recorded as a pressure anomaly with a likely filling transient.", TimelineSource.system, "Complete"),
                (13, "severity_assigned", "Severity assigned", "Severity set to Tier 1 watch only.", TimelineSource.system, "Complete"),
                (16, "network_priority_requested", "Network priority requested", "Not requested.", TimelineSource.system, "Skipped"),
                (19, "operator_notified", "Operator notified", "Fatima Al Lawati set a one-cycle monitor.", TimelineSource.operator, "Complete"),
            ],
        ),
        "INC-1836": events_for(
            "INC-1836",
            [
                (0, "anomaly_detected", "Anomaly detected", "Incomplete telemetry window on Medina Arc B.", TimelineSource.detector, "Complete"),
                (3, "investigation_started", "Investigation started", "Classification paused pending more frames.", TimelineSource.system, "Complete"),
                (6, "reachability_checked", "Device reachability checked", "Gateway retries elevated on Arc B.", TimelineSource.network, "Complete"),
                (9, "incident_classified", "Incident classified", "Insufficient data; no hydraulic class assigned.", TimelineSource.system, "Complete"),
                (10, "severity_assigned", "Severity assigned", "Severity set to Tier 1 until a complete window arrives.", TimelineSource.system, "Complete"),
                (12, "network_priority_requested", "Network priority requested", "Held until completeness recovers.", TimelineSource.system, "Skipped"),
                (14, "operator_notified", "Operator notified", "Unassigned; system is waiting for the next window.", TimelineSource.system, "Waiting"),
            ],
        ),
        "INC-1837": events_for(
            "INC-1837",
            [
                (0, "anomaly_detected", "Anomaly detected", "Industrial ring flow jumped at shift start.", TimelineSource.detector, "Complete"),
                (6, "investigation_started", "Investigation started", "Weekday start-up profiles were compared.", TimelineSource.system, "Complete"),
                (8, "reachability_checked", "Device reachability checked", "Industrial ring radios healthy.", TimelineSource.network, "Complete"),
                (14, "incident_classified", "Incident classified", "Recorded as a normal demand spike, not a leak.", TimelineSource.system, "Complete"),
                (15, "severity_assigned", "Severity assigned", "Severity remained Tier 1 after reclassification.", TimelineSource.system, "Complete"),
                (18, "network_priority_requested", "Network priority requested", "Not required.", TimelineSource.system, "Skipped"),
                (22, "operator_notified", "Operator notified", "Yousef Al Qahtani closed the event as a false alarm.", TimelineSource.operator, "Complete"),
            ],
        ),
        "INC-1834": events_for(
            "INC-1834",
            [
                (0, "anomaly_detected", "Anomaly detected", "Abdali trunk packet loss climbed above 8%.", TimelineSource.detector, "Complete"),
                (4, "investigation_started", "Investigation started", "Hydraulics and radio health were checked together.", TimelineSource.system, "Complete"),
                (7, "reachability_checked", "Device reachability checked", "AMM-GW-03 was restarting.", TimelineSource.network, "Complete"),
                (20, "incident_classified", "Incident classified", "Recorded as connectivity degradation with no leak signature.", TimelineSource.system, "Complete"),
                (21, "severity_assigned", "Severity assigned", "Severity set to Tier 2 while coverage was reduced.", TimelineSource.system, "Complete"),
                (36, "network_priority_requested", "Network priority requested", "Not needed after gateway recovery.", TimelineSource.system, "Skipped"),
                (48, "operator_notified", "Operator notified", "Rania Nasser marked the incident resolved.", TimelineSource.operator, "Complete"),
            ],
        ),
    }


_INCIDENTS: list[IncidentDetail] | None = None
_TIMELINES: dict[str, list[TimelineEvent]] | None = None


def get_incidents() -> list[IncidentDetail]:
    global _INCIDENTS
    if _INCIDENTS is None:
        _INCIDENTS = _build_incidents()
    return _INCIDENTS


def get_incident(incident_id: str) -> IncidentDetail | None:
    needle = incident_id.strip().upper()
    for incident in get_incidents():
        if incident.id.upper() == needle:
            return incident
    return None


def get_timeline(incident_id: str) -> list[TimelineEvent] | None:
    if get_incident(incident_id) is None:
        return None
    global _TIMELINES
    if _TIMELINES is None:
        _TIMELINES = _build_timelines()
    return _TIMELINES.get(incident_id.strip().upper(), [])
