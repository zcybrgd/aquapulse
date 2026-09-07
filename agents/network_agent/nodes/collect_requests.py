import time

# Mechanisms to be changed according to how the requests are gonna be collected and stored
# Could be that this mechanism wouldn't even be managed here, but we just collect the requests
class RequestCollector:
    def __init__(self, max_batch_size: int = 10, max_wait_time: float = 2.0):
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        self.pending_requests = []
        self.batch_start_time = None

    def add_request(self, request):
        # to verify the max_time_wait
        if not self.pending_requests:
            self.batch_start_time = time.monotonic()

        self.pending_requests.append(request)

    def should_flush(self):
        if not self.pending_requests:
            return False

        if len(self.pending_requests) >= self.max_batch_size:
            return True

        # if any request has a severity tier of 3 we should flush immediately
        if any(r["severity_tier"] == 3 for r in self.pending_requests):
            return True

        elapsed_time = time.monotonic() - self.batch_start_time
        if elapsed_time >= self.max_wait_time:
            return True

        return False

    def get_batch(self):
        batch = self.pending_requests[:self.max_batch_size]
        self.pending_requests = self.pending_requests[self.max_batch_size:]
        # if there there are still pending requests (in the case of reaching max_batch_size)
        if self.pending_requests:
            self.batch_start_time = time.monotonic()
        else:
            self.batch_start_time = None

        return batch