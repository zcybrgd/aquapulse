from agents.network_agent.nodes.rank_requests import rank_requests

requests = [
    {
        "id": "R1",
        "severity_tier": 2,
        "asset_criticality": 0.9,
        "confidence": 0.95,
    },
    {
        "id": "R2",
        "severity_tier": 3,
        "asset_criticality": 0.5,
        "confidence": 0.70,
    },
    {
        "id": "R3",
        "severity_tier": 2,
        "asset_criticality": 1.0,
        "confidence": 0.80,
    },
    {
        "id": "R4",
        "severity_tier": 1,
        "asset_criticality": 1.0,
        "confidence": 0.99,
    },
    {
        "id": "R5",
        "severity_tier": 2,
        "asset_criticality": 1.0,
        "confidence": 0.95,
    },
]


ranked = rank_requests(requests)

print("Ranking:")
for i, request in enumerate(ranked, start=1):
    print(
        f"{i}. {request['id']} "
        f"(Tier={request['severity_tier']}, "
        f"Criticality={request['asset_criticality']}, "
        f"Confidence={request['confidence']})"
    )