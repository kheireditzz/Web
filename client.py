"""
WhatsApp Business Cloud API client.
Docs: https://developers.facebook.com/docs/whatsapp/cloud-api
"""

import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WhatsAppClient:
    BASE_URL = "https://graph.facebook.com/v19.0"

    def __init__(self, phone_number_id: str, access_token: str):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        })

    # ------------------------------------------------------------------
    # Send a free-form text message (only within 24-hr customer window)
    # ------------------------------------------------------------------
    def send_text(self, to: str, body: str) -> dict:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
        return self._post(payload)

    # ------------------------------------------------------------------
    # Send a pre-approved template message (works outside 24-hr window)
    # ------------------------------------------------------------------
    def send_template(
        self,
        to: str,
        template_name: str,
        language_code: str = "en_US",
        components: Optional[list] = None,
    ) -> dict:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }
        if components:
            payload["template"]["components"] = components
        return self._post(payload)

    # ------------------------------------------------------------------
    # Internal POST helper
    # ------------------------------------------------------------------
    def _post(self, payload: dict) -> dict:
        url = f"{self.BASE_URL}/{self.phone_number_id}/messages"
        try:
            resp = self.session.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            return {"success": True, "data": resp.json()}
        except requests.exceptions.HTTPError as e:
            error = {}
            try:
                error = e.response.json()
            except Exception:
                pass
            logger.error("HTTP error sending message: %s | %s", e, error)
            return {"success": False, "error": str(e), "detail": error}
        except requests.exceptions.RequestException as e:
            logger.error("Request error: %s", e)
            return {"success": False, "error": str(e)}
