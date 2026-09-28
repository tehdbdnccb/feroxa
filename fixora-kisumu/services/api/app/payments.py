import base64
from datetime import datetime

import httpx

from .config import settings


class MpesaConfigurationError(RuntimeError):
    pass


class MpesaGateway:
    def __init__(self) -> None:
        self.base_url = "https://sandbox.safaricom.co.ke" if settings.mpesa_env == "sandbox" else "https://api.safaricom.co.ke"

    def _require_config(self) -> None:
        required = [
            settings.mpesa_consumer_key,
            settings.mpesa_consumer_secret,
            settings.mpesa_shortcode,
            settings.mpesa_passkey,
            settings.mpesa_callback_url,
            settings.mpesa_callback_token,
        ]
        if not all(required):
            raise MpesaConfigurationError("M-Pesa Daraja credentials, callback URL and callback token are required")

    async def stk_push(self, phone: str, amount: int, account_reference: str, transaction_desc: str) -> dict:
        self._require_config()
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=10.0)) as client:
            token_response = await client.get(
                self.base_url + "/oauth/v1/generate",
                params={"grant_type": "client_credentials"},
                auth=(settings.mpesa_consumer_key, settings.mpesa_consumer_secret),
            )
            token_response.raise_for_status()
            token = token_response.json()["access_token"]
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            password = base64.b64encode(
                f"{settings.mpesa_shortcode}{settings.mpesa_passkey}{timestamp}".encode()
            ).decode()
            payload = {
                "BusinessShortCode": settings.mpesa_shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": amount,
                "PartyA": phone,
                "PartyB": settings.mpesa_shortcode,
                "PhoneNumber": phone,
                "CallBackURL": settings.mpesa_callback_url,
                "AccountReference": account_reference,
                "TransactionDesc": transaction_desc,
            }
            response = await client.post(
                self.base_url + "/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.json()


mpesa_gateway = MpesaGateway()
