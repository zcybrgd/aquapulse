import time
from agents.network_agent.nodes.collect_requests import RequestCollector

collector = RequestCollector(
    max_batch_size=10,
    max_wait_time=2.0
)

requests = [
    {"id": "R1", "severity_tier": 1},
    {"id": "R3", "severity_tier": 3},
    {"id": "R2", "severity_tier": 2},
]


for request in requests:

    collector.add_request(request)

    print(f"Added {request['id']}")

    if collector.should_flush():
        batch = collector.get_batch()
        print("PROCESSING:", batch)

    time.sleep(0.5)


# Keep checking until the waiting time expires
while collector.pending_requests:

    if collector.should_flush():
        batch = collector.get_batch()
        print("PROCESSING:", batch)
        break

    time.sleep(0.1)