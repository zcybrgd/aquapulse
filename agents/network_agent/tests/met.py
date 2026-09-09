import os

slice_id = "your_actual_id_here"
os.environ["PREPROVISIONED_SLICE_ID"] = slice_id

# Verify it here, inside the script
print("Inside Python:", os.environ["PREPROVISIONED_SLICE_ID"])