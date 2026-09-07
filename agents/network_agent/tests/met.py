import os
import inspect
from dotenv import load_dotenv
from network_as_code import NetworkAsCodeApi

load_dotenv()

nac_client = NetworkAsCodeApi(
    rapidapi_host=os.getenv("RAPIDAPI_HOST"),
    api_key=os.getenv("NOKIA_API_KEY")
)

slice_client = nac_client.slice

print("=" * 70)
print(f"SliceClient class: {type(slice_client)}")
print(f"Module: {type(slice_client).__module__}")
print("=" * 70)

print("\n--- All public attributes/methods ---")
members = [m for m in dir(slice_client) if not m.startswith("_")]
for m in members:
    print(f"  {m}")

print("\n--- Signatures + docstrings for attachment/device-related methods ---")
keywords = ["attach", "device", "detach"]
for m in members:
    if any(k in m.lower() for k in keywords):
        attr = getattr(slice_client, m)
        if callable(attr):
            try:
                sig = inspect.signature(attr)
            except (ValueError, TypeError):
                sig = "(signature unavailable)"
            print(f"\n>>> {m}{sig}")
            doc = inspect.getdoc(attr)
            print(doc if doc else "   (no docstring)")

print("\n--- Full source location of SliceClient (in case docstrings are thin) ---")
try:
    print(inspect.getfile(type(slice_client)))
except TypeError:
    print("Could not resolve source file (may be compiled/C extension).")