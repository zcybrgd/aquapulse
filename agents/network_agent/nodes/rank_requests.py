
def rank_requests(requests):
    return sorted(requests, key=lambda r: (
            -r.get("severity_tier", 0),
            -r.get("criticality_metrics", {}).get("criticality_score", 0),
            -r.get("confidence_score", 0.0),
        )
    )