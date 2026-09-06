import os
import time
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_core.tools import tool
from network_as_code import NetworkAsCodeApi
import json

load_dotenv()

nac_client = NetworkAsCodeApi(
    rapidapi_host=os.getenv("RAPIDAPI_HOST"),
    api_key=os.getenv("NOKIA_API_KEY")
)

def _get_slice_state(slice_obj: Any) -> str:
    """Helper to safely extract slice state from SDK object or dict."""
    if isinstance(slice_obj, dict):
        return slice_obj.get("state", "UNKNOWN")
    return getattr(slice_obj, "state", "UNKNOWN")

@tool
def delete_network_slice(slice_id: str, max_poll_seconds: int = 180) -> Dict[str, Any]:
    """
    Deallocates and deletes a 5G network slice.
    If the slice is currently OPERATING, it safely deactivates it first,
    polls until it transitions back to AVAILABLE, and then removes it.

    Args:
        slice_id (str): Name or ID of the network slice to delete.
        max_poll_seconds (int): Maximum time in seconds to wait for deactivation (default: 180s).
    """
    try:
        print(f"Deleting slice '{slice_id}'...")
        try:
            my_slice = nac_client.slice.get_slice(slice_id)
            current_state = _get_slice_state(my_slice)
        except Exception as e:
            return {
                "status": "FAILED",
                "slice_id": slice_id,
                "error": f"Slice '{slice_id}' not found or inaccessible: {str(e)}"
            }

        if current_state == "OPERATING":
            print(f"Deactivating operating slice '{slice_id}'...")
            try:
                nac_client.slice.deactivate(slice_id)
            except Exception as deact_err:
                print(f"Deactivation call note: {deact_err}")

            start_time = time.time()
            print(f"Waiting for slice '{slice_id}' to become AVAILABLE for deletion...")

            while current_state != "AVAILABLE" and (time.time() - start_time) < max_poll_seconds:
                time.sleep(5)
                elapsed = int(time.time() - start_time)

                try:
                    my_slice = nac_client.slice.get_slice(slice_id)
                    current_state = _get_slice_state(my_slice)
                except Exception:
                    pass

                print(f"   [Deactivating {elapsed}s] State: {current_state}")

                if current_state == "AVAILABLE":
                    break

            if current_state != "AVAILABLE":
                return {
                    "status": "FAILED",
                    "slice_id": slice_id,
                    "error": f"Slice failed to reach AVAILABLE state for deletion after {max_poll_seconds}s (Current state: {current_state})."
                }
        nac_client.slice.delete_slice(slice_id)
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

if __name__ == "__main__":
    print(f"Deleting slice ...\n")
    result = delete_network_slice.invoke("slice-z47-1788652213")
    print("\nFinal Result:")
    print(json.dumps(result, indent=2))