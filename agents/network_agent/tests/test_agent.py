from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage
import os
from dotenv import load_dotenv

load_dotenv()

os.environ["MISTRAL_API_KEY"] = os.getenv("LLM_API_KEY")

llm = ChatMistralAI(
    model="mistral-medium-latest",
    temperature=0
)

response = llm.invoke([HumanMessage(content="Hello! Are you ready to act as an agent brain? It's a project about network management and optimization using congestion insights, network slicing, and QOD. Confirm that you are operational and that you can do those tasks.")])

print(response.content)