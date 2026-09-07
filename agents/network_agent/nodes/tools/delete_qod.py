from typing import Dict, Any
from langchain_core.tools import tool
from agents.network_agent.camara_api import camara_service

@tool
def delete_qod_session(session_id: str) -> Dict[str, Any]:
    """
    Deletes an active Quality on Demand (QoD) session by its session ID.

    Args:
        session_id (str): The unique ID of the QoD session to delete.
    """
    return camara_service.delete_qod_session(session_id=session_id)