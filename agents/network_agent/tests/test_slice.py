import os
import time
from dotenv import load_dotenv
from network_as_code import NetworkAsCodeApi

load_dotenv()

nac_client = NetworkAsCodeApi(
    rapidapi_host=os.getenv("RAPIDAPI_HOST"),
    api_key=os.getenv("NOKIA_API_KEY")
)

slice = nac_client.slice.list_slices()

print(slice)

all_attachments = nac_client.slice.get_device_attachments()
if all_attachments:
    print(all_attachments)