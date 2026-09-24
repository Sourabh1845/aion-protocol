from locust import HttpUser, task, between
import json
import os

class AIONUser(HttpUser):
    wait_time = between(0.1, 0.5)
    headers = {
        "Content-Type": "application/json",
        # Override with AION_API_KEY when pointing at a real server. The local
        # dev key is only accepted by a server started with AION_ALLOW_DEV_KEY=1.
        "X-AION-API-Key": os.getenv("AION_API_KEY", "aion-dev-key-local"),
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