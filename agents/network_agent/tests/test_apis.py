import os
from dotenv import load_dotenv
from network_as_code import NetworkAsCodeApi

load_dotenv()

print("TEST BEFORE CLIENT")
client = NetworkAsCodeApi(
    rapidapi_host=os.getenv("RAPIDAPI_HOST"),
    api_key=os.getenv("RAPIDAPI_KEY"),
)
print(os.getenv("RAPIDAPI_HOST"))

print("TEST AFTER CLIENT \n")
print(client)

location = client.location.retrieve(
    device={"phone_number": "+999991234567"},
    max_age=3600,
)

print(location)