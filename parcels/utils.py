import requests
import os

NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8002")

def trigger_email_notification(to, template_type, context):
    try:
        response = requests.post(
            f"{NOTIFICATION_SERVICE_URL}/api/send-email/",
            json={
                "to": to,
                "template_type": template_type,
                "context": context
            },
            timeout=5
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"[Notification Error] {e}")
        return False
