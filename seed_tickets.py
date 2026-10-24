"""Insert a small, repeatable set of support-ticket examples via the REST API."""

import os

import requests
from dotenv import load_dotenv

load_dotenv()
BASE_URL = os.getenv("TICKET_API_URL", os.getenv("TASK_API_URL", "http://127.0.0.1:8000"))

SAMPLES = [
    {
        "customer_name": "Priya Shah",
        "subject": "Duplicate charge on invoice",
        "description": "I see the same charge twice on my latest invoice.",
        "priority": "high",
        "status": "open",
    },
    {
        "customer_name": "Miguel Santos",
        "subject": "Monthly report will not export",
        "description": "The export button spins and never downloads the report.",
        "priority": "normal",
        "status": "in_progress",
    },
    {
        "customer_name": "Sam Taylor",
        "subject": "Update account email address",
        "description": "Please change the email address on my account.",
        "priority": "low",
        "status": "closed",
    },
]


def main() -> None:
    response = requests.get(f"{BASE_URL}/tickets", timeout=10)
    response.raise_for_status()
    existing = response.json()

    for sample in SAMPLES:
        match = next(
            (
                ticket
                for ticket in existing
                if ticket["customer_name"] == sample["customer_name"]
                and ticket["subject"] == sample["subject"]
            ),
            None,
        )

        if match is None:
            payload = {key: value for key, value in sample.items() if key != "status"}
            created_response = requests.post(f"{BASE_URL}/tickets", json=payload, timeout=10)
            created_response.raise_for_status()
            ticket = created_response.json()
            print(f"Created ticket {ticket['id']}: {ticket['subject']}")
        else:
            ticket = match
            print(f"Already exists, reusing ticket {ticket['id']}: {ticket['subject']}")

        if ticket["status"] != sample["status"]:
            update_response = requests.patch(
                f"{BASE_URL}/tickets/{ticket['id']}/status",
                json={"status": sample["status"]},
                timeout=10,
            )
            update_response.raise_for_status()
            ticket = update_response.json()
            print(f"  Set status to {ticket['status']}")
        else:
            print(f"  Status is already {ticket['status']}")


if __name__ == "__main__":
    main()
