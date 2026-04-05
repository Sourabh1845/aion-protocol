from locust import HttpUser, task, between
import json

class AIONUser(HttpUser):
    wait_time = between(0.1, 0.5)
    headers = {
        "Content-Type": "application/json",
        "X-AION-API-Key": "aion-dev-key-local"
    }

    @task(3)
    def issue_authority(self):
        self.client.post(
            "/issue",
            data=json.dumps({"scope": "ops.read"}),
            headers=self.headers
        )

    @task(1)
    def health_check(self):
        self.client.get("/health")