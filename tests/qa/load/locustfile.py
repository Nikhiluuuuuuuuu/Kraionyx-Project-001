import json
from locust import HttpUser, task, between

class STTWebsocketLoadTest(HttpUser):
    wait_time = between(1, 3)

    @task
    def simulate_audio_stream(self):
        # Simulate connecting to the gateway for audio streaming
        with self.client.post("/api/v1/audio/stream", json={"patient_id": "12345", "audio_chunk": "base64encodedata"}, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Stream failed: {response.status_code}")
