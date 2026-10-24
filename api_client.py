"""Call the support-ticket REST API directly, without MCP."""

import os

import requests
from dotenv import load_dotenv

load_dotenv()
BASE_URL = os.getenv("TICKET_API_URL", os.getenv("TASK_API_URL", "http://127.0.0.1:8000"))


def create_ticket(customer_name: str, subject: str, description: str, priority: str = "normal") -> dict:
    response = requests.post(
        f"{BASE_URL}/tickets",
        json={
            "customer_name": customer_name,
            "subject": subject,
            "description": description,
            "priority": priority,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    created = create_ticket(
        customer_name="Asha Kumar",
        subject="Cannot sign in",
        description="The password reset link expires immediately.",
        priority="high",
    )
    print("Created by calling POST /tickets directly:")
    print(created)
