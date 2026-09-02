from __future__ import annotations
import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv
load_dotenv()
def get_groq_llm():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set.")
    return ChatGroq(model=os.getenv("RESPONSE_AGENT_MODEL","llama-3.3-70b-versatile",),temperature=0,api_key=api_key,)