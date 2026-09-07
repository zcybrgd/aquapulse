from collections import defaultdict
from typing import List, Dict, Any

def group_requests_by_zone(batch_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    zone_groups = defaultdict(list)
    for req in batch_requests:
        zone_id = req.get("sensor_cluster_id", req.get("zone_id", "zone-unknown"))
        zone_groups[zone_id].append(req)  
        
    regional_batches = []
    for zone_id, zone_requests in zone_groups.items():
        regional_batches.append({
            "zone_id": zone_id,
            "representative_device_id": zone_requests[0].get("device_id", "+99999991000"),
            "requests": zone_requests
        })
        
    return regional_batches