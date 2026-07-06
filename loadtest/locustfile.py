from locust import HttpUser, task, between
import os

API_KEY = os.getenv("SMARTRFP_API_KEY", "")

headers = {}
if API_KEY:
    headers["X-API-Key"] = API_KEY


class SmartRFPUser(HttpUser):
    wait_time = between(1, 3)

    @task(5)
    def health(self):
        self.client.get("/health", headers=headers)

    @task(5)
    def ready(self):
        self.client.get("/health/ready", headers=headers)

    @task(3)
    def list_rfps(self):
        self.client.get("/rfps", headers=headers)

    @task(2)
    def kb(self):
        self.client.get("/kb", headers=headers)

    @task(1)
    def metrics(self):
        self.client.get("/metrics")