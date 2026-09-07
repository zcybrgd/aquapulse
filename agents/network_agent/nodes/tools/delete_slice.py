import json
from typing import Dict, Any
from langchain_core.tools import tool
from agents.network_agent.camara_api import camara_service

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
    return camara_service.delete_network_slice(
        slice_id=slice_id, 
        max_poll_seconds=max_poll_seconds
    )


if __name__ == "__main__":
    print("Deleting slice ...\n")
    result = delete_network_slice.invoke({"slice_id": "zone-47491908-critical"})
    print("\nFinal Result:")
    print(json.dumps(result, indent=2))