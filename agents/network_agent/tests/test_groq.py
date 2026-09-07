from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, MessagesState, StateGraph
import os
from dotenv import load_dotenv

load_dotenv()

os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")
api_key = os.getenv("GROQ_API_KEY")

llm = ChatGroq(model=os.getenv("RESPONSE_AGENT_MODEL","openai/gpt-oss-120b",),temperature=0,api_key=api_key,)


def call_model(state: MessagesState):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


builder = StateGraph(MessagesState)

builder.add_node("llm", call_model)
builder.add_edge(START, "llm")
builder.add_edge("llm", END)

app = builder.compile()

input_messages = {
    "messages": [
        HumanMessage(
            content="Explain state management in LangGraph in two sentences."
        )
    ]
}
output = app.invoke(input_messages)

print(output["messages"][-1].content)