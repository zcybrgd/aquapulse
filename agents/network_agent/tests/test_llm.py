from mistralai.client import Mistral
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("LLM_API_KEY")

client = Mistral(api_key=api_key)

response = client.chat.complete(
    model="mistral-small-latest",  
    messages=[
        {"role": "user", "content": "Hello! Confirm that you are operational."}
    ]
)

print(response.choices[0].message.content)