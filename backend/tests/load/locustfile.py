"""
Load testing with Locust for AI Memory Assistant API.

Usage:
    locust -f tests/load/locustfile.py --host=http://localhost:8000
    locust -f tests/load/locustfile.py --host=http://localhost:8000 --headless -u 50 -r 5 --run-time 2m
"""
from locust import HttpUser, task, between, constant_throughput
import json
import random

DEMO_EMAIL = "loadtest@example.com"
DEMO_PASSWORD = "loadtest123"
DEMO_MESSAGES = [
    "What are my favorite programming languages?",
    "Summarize my recent Python projects",
    "What frameworks do I prefer for backend development?",
    "Tell me about my goals we discussed before",
    "What was the last React project I mentioned?",
    "What are my thoughts on TypeScript vs JavaScript?",
]


class AnonymousUser(HttpUser):
    """Tests public endpoints."""
    wait_time = between(1, 3)
    weight = 1

    @task
    def health_check(self):
        with self.client.get("/api/v1/health/live", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"Health check failed: {resp.status_code}")


class AuthenticatedUser(HttpUser):
    """Tests authenticated chat and memory endpoints."""
    wait_time = between(2, 5)
    weight = 3
    token: str = ""
    conversation_id: str | None = None

    def on_start(self):
        """Login and store token."""
        # Try to register first
        self.client.post("/api/v1/auth/register", json={
            "username": f"loaduser_{random.randint(1000, 9999)}",
            "email": f"load_{random.randint(1000, 9999)}@test.com",
            "password": DEMO_PASSWORD,
        })

        # Login
        resp = self.client.post("/api/v1/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD,
        })
        if resp.status_code == 200:
            self.token = resp.json()["access_token"]
        else:
            # Register fresh user
            u = f"l{random.randint(100000, 999999)}"
            reg = self.client.post("/api/v1/auth/register", json={
                "username": u,
                "email": f"{u}@test.com",
                "password": DEMO_PASSWORD,
            })
            if reg.status_code == 201:
                self.token = reg.json()["access_token"]

    def get_headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def list_conversations(self):
        with self.client.get(
            "/api/v1/chat/conversations",
            headers=self.get_headers(),
            catch_response=True,
            name="GET /conversations",
        ) as resp:
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                if items:
                    self.conversation_id = random.choice(items)["id"]
            elif resp.status_code != 401:
                resp.failure(f"Unexpected: {resp.status_code}")

    @task(2)
    def search_memory(self):
        query = random.choice(["python", "react", "projects", "goals", "preferences"])
        with self.client.get(
            f"/api/v1/memory/search?query={query}&limit=5",
            headers=self.get_headers(),
            catch_response=True,
            name="GET /memory/search",
        ) as resp:
            if resp.status_code not in (200, 401):
                resp.failure(f"Memory search failed: {resp.status_code}")

    @task(2)
    def get_memory_stats(self):
        with self.client.get(
            "/api/v1/memory/stats",
            headers=self.get_headers(),
            catch_response=True,
            name="GET /memory/stats",
        ) as resp:
            if resp.status_code not in (200, 401):
                resp.failure(f"Stats failed: {resp.status_code}")

    @task(1)
    def create_conversation(self):
        with self.client.post(
            "/api/v1/chat/conversations",
            json={"title": f"Load test conv {random.randint(1, 100)}"},
            headers=self.get_headers(),
            catch_response=True,
            name="POST /conversations",
        ) as resp:
            if resp.status_code == 201:
                self.conversation_id = resp.json()["id"]
            elif resp.status_code not in (401, 422):
                resp.failure(f"Create conv failed: {resp.status_code}")
