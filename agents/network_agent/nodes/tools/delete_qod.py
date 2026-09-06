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

@tool
def delete_qod_session(session_id: str) -> Dict[str, Any]:
    """
    Deletes an active Quality on Demand (QoD) session by its session ID.

    Args:
        session_id (string): The unique ID of the QoD session to delete.
    """
    try:
        response = nac_client.qod.delete_session_v1(session_id=session_id)
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


if __name__ == "__main__":
    print(f"Deleting QoD session ...\n")
    result = delete_qod_session.invoke("0a02ef56-8305-4457-be8b-a5ae54a169cf")
    print("\nFinal Result:")
    print(json.dumps(result, indent=2))