import os
import re
import time
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from dotenv import load_dotenv
from network_as_code import NetworkAsCodeApi

load_dotenv()

class CamaraService:
    def __init__(self):
        self.client = NetworkAsCodeApi(
            rapidapi_host=os.getenv("RAPIDAPI_HOST"),
            api_key=os.getenv("NOKIA_API_KEY")
        )

    def check_congestion(
        self, 
        representative_device_id: str, 
        zone_id: str,
        notification_url: str,
        notification_auth_token: str
    ) -> Dict[str, Any]:
        """Queries network congestion level for a zone using a representative device."""
        try:
            self.client.congestion_insights.create_subscription(
                device={"phone_number": representative_device_id},
                webhook={
                    "notification_url": notification_url,
                    "notification_auth_token": notification_auth_token,
                },
                subscription_expire_time=datetime.now(timezone.utc) + timedelta(days=1)
            )

            congestion_data = self.client.congestion_insights.query(
                device={"phone_number": representative_device_id}
            )

            congestion_level = "None"
            if congestion_data and len(congestion_data) > 0:
                first_event = congestion_data[0]
                congestion_level = getattr(
                    first_event, 
                    "level", 
                    getattr(first_event, "congestion_level", "Unknown")
                )
                
            return {
                "zone_id": zone_id,
                "representative_device_id": representative_device_id,
                "congestion_level": congestion_level
            }
        except Exception as e:
            return {
                "zone_id": zone_id,
                "representative_device_id": representative_device_id,
                "status": "FAILED", 
                "error": str(e)
            }

    def request_qod(
        self,
        device_id: str,
        app_server_ipv4: str,
        qos_profile: str,
        duration_seconds: int = 3600,
        wait_for_allocation: bool = True,
        max_wait_seconds: int = 20
    ) -> Dict[str, Any]:
        """Triggers CAMARA QoD session and optionally polls until active."""
        try:
            response = self.client.qod.create_session_v1(
                device={"phone_number": device_id},
                application_server={"ipv4Address": app_server_ipv4},
                qos_profile=qos_profile,
                duration=duration_seconds
            )

            session_id = getattr(response, "session_id", None)
            if not session_id:
                return {"status": "FAILED", "error": "No session_id returned from API gateway"}

            current_status = getattr(response, "qos_status", getattr(response, "status", "REQUESTED"))
            started_at = getattr(response, "started_at", None)
            expires_at = getattr(response, "expires_at", None)

            if wait_for_allocation and current_status == "REQUESTED":
                start_time = time.time()
                poll_interval = 2

                while (time.time() - start_time) < max_wait_seconds:
                    time.sleep(poll_interval)
                    try:
                        session_update = self.client.qod.get_session_v1(session_id=session_id)
                        current_status = getattr(session_update, "qos_status", getattr(session_update, "status", current_status))
                        started_at = getattr(session_update, "started_at", None) or started_at
                        expires_at = getattr(session_update, "expires_at", None) or expires_at

                        if current_status in ["AVAILABLE", "UNAVAILABLE", "FAILED"]:
                            break
                    except Exception:
                        pass

            return {
                "session_id": session_id,
                "status": current_status,
                "qos_profile": getattr(response, "qos_profile", qos_profile),
                "started_at": str(started_at) if started_at is not None else ("Pending Activation" if current_status == "REQUESTED" else "N/A"),
                "expires_at": str(expires_at) if expires_at is not None else ("Pending Activation" if current_status == "REQUESTED" else "N/A")
            }
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    def delete_qod_session(self, session_id: str) -> Dict[str, Any]:
        """Deletes an active Quality on Demand (QoD) session."""
        try:
            response = self.client.qod.delete_session_v1(session_id=session_id)
            return {
                "status": "DELETED",
                "session_id": session_id,
                "response": str(response)
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "session_id": session_id,
                "error": str(e)
            }

    def create_slice(
        self,
        slice_name: str,
        mcc: str = "236",
        mnc: str = "30",
        service_type: int = 1,
        differentiator: str = "AUTO",
        notification_url: str = "",
        notification_auth_token: str = ""
    ) -> Any:
        """Low-level method to request slice creation via SDK."""
        clean_name = re.sub(r'[^a-zA-Z0-9-]', '', slice_name) or f"slice-{int(time.time())}"
        
        if not differentiator or differentiator.upper() in ["AUTO", "000001", "DEFAULT", "NONE", "NULL", ""]:
            differentiator = secrets.token_hex(3).upper()

        slice_obj = self.client.slice.create_slice(
            name=clean_name,
            network_identifier={"mcc": mcc, "mnc": mnc},
            slice_info={"service_type": service_type, "differentiator": differentiator},
            notification_url=notification_url,
            notification_auth_token=notification_auth_token
        )
        return slice_obj, clean_name, differentiator

    def delete_slice_direct(self, slice_id: str) -> None:
        """Immediately calls delete on a slice without state polling."""
        self.client.slice.delete_slice(slice_id)

    def delete_network_slice(self, slice_id: str, max_poll_seconds: int = 180) -> Dict[str, Any]:
        """Safely deactivates and deletes a 5G network slice with polling."""
        try:
            try:
                my_slice = self.client.slice.get_slice(slice_id)
                current_state = my_slice.get("state", "UNKNOWN") if isinstance(my_slice, dict) else getattr(my_slice, "state", "UNKNOWN")
            except Exception as e:
                return {
                    "status": "FAILED",
                    "slice_id": slice_id,
                    "error": f"Slice '{slice_id}' not found or inaccessible: {str(e)}"
                }

            if current_state == "OPERATING":
                try:
                    self.client.slice.deactivate(slice_id)
                except Exception as deact_err:
                    print(f"Deactivation call note: {deact_err}")

                start_time = time.time()
                while current_state != "AVAILABLE" and (time.time() - start_time) < max_poll_seconds:
                    time.sleep(5)
                    try:
                        my_slice = self.client.slice.get_slice(slice_id)
                        current_state = my_slice.get("state", "UNKNOWN") if isinstance(my_slice, dict) else getattr(my_slice, "state", "UNKNOWN")
                    except Exception:
                        pass

                if current_state != "AVAILABLE":
                    return {
                        "status": "FAILED",
                        "slice_id": slice_id,
                        "error": f"Slice failed to reach AVAILABLE state after {max_poll_seconds}s (Current state: {current_state})."
                    }

            self.client.slice.delete_slice(slice_id)
            return {
                "status": "DELETED",
                "slice_id": slice_id,
                "message": f"Slice '{slice_id}' was successfully deactivated and deleted."
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "slice_id": slice_id,
                "error": str(e)
            }

camara_service = CamaraService()