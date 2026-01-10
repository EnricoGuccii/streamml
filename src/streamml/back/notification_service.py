import json
import requests
from pathlib import Path

CONFIG_FILE = Path("data/global_config.json")

class NotificationService:
    def __init__(self):
        self.webhook_url = ""
        self.load_config()

    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.webhook_url = data.get("discord_webhook_url", "")
            except Exception as e:
                print(f"Error loading notification config: {e}")

    def save_config(self, webhook_url: str):
        self.webhook_url = webhook_url
        
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({
                    "discord_webhook_url": self.webhook_url
                }, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def send_message(self, message: str) -> bool:
        if not self.webhook_url:
            return False

        payload = {
            "content": message
        }
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=5)
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"Discord send error: {e}")
            return False

notification_service = NotificationService()
