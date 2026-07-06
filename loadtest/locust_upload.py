from locust import HttpUser, task, between
import os

API_KEY = os.getenv("SMARTRFP_API_KEY", "")

headers = {}
if API_KEY:
    headers["X-API-Key"] = API_KEY


class UploadUser(HttpUser):

    wait_time = between(30, 60)

    @task
    def upload_rfp(self):

        with open("sample_rfp.pdf", "rb") as f:

            files = {
                "file": (
                    "sample_rfp.pdf",
                    f,
                    "application/pdf"
                )
            }

            data = {
                "deal_name": "Load Test",
                "client_name": "ABC",
                "region": "US",
                "deadline": "",
                "assigned_role": "Architect",
                "use_web_search": "false"
            }

            self.client.post(
                "/upload-rfp",
                files=files,
                data=data,
                headers=headers,
                timeout=600
            )