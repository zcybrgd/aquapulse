from __future__ import annotations
import os
from typing import Literal, Optional
from fastapi import FastAPI
from pydantic import BaseModel
app = FastAPI(title="notification-service")
TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.environ.get("TWILIO_FROM_NUMBER")
_twilio_client = None
if TWILIO_SID and TWILIO_TOKEN:
    from twilio.rest import Client as TwilioClient
    _twilio_client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)

class NotifyRequest(BaseModel):
    recipient: str
    message: str
    channel: Literal["sms", "email", "push"] = "sms"
    incident_id: Optional[str] = None

@app.post("/v1/notify")
def notify(body: NotifyRequest) -> dict:
    print(f"[NOTIFY:{body.channel}] incident={body.incident_id} to={body.recipient} -> {body.message}")
    if _twilio_client is not None and body.channel == "sms":
        _twilio_client.messages.create(to=body.recipient, from_=TWILIO_FROM, body=body.message)
    return {"sent": True}



"""
an actual running HTTP server the agent calls, 
By default it logs and prints (so the demo is visible without any paid
service). If TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER
are set as environment variables, it sends a real SMS via Twilio instead
"""