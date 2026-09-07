import os
import time
from dotenv import load_dotenv
from network_as_code import NetworkAsCodeApi

load_dotenv()

nac_client = NetworkAsCodeApi(
    rapidapi_host=os.getenv("RAPIDAPI_HOST"),
    api_key=os.getenv("NOKIA_API_KEY")
)

def _get_state(slice_obj):
    if isinstance(slice_obj, dict):
        return slice_obj.get("state", "UNKNOWN")
    return getattr(slice_obj, "state", "UNKNOWN")

def _get_name(slice_obj):
    if isinstance(slice_obj, dict):
        return slice_obj.get("name")
    return getattr(slice_obj, "name", None)

def cleanup_all_slices(poll_interval=5, max_poll_seconds=180):
    print("🔎 Fetching all slices...")
    all_slices = nac_client.slice.list_slices()
    print(f"Found {len(all_slices)} slice(s).\n")

    try:
        all_attachments = nac_client.slice.get_device_attachments()
    except Exception as e:
        print(f"⚠️ Could not fetch attachments: {e}")
        all_attachments = []

    def _attachments_for(slice_name):
        result = []
        for a in all_attachments:
            sid = getattr(a.resource, "slice_id", None)
            if sid == slice_name:
                result.append(a)
        return result

    for s in all_slices:
        name = _get_name(s)
        state = _get_state(s)
        print(f"--- Processing '{name}' (state: {state}) ---")

        if state == "DELETED":
            print("   Already deleted, skipping.\n")
            continue

        if state == "OPERATING":
            attachments = _attachments_for(name)
            for att in attachments:
                res_id = att.nac_resource_id
                try:
                    print(f"   🔌 Detaching attachment '{res_id}'...")
                    nac_client.slice.delete_device_attachment(resource_id=res_id)
                except Exception as e:
                    print(f"   ⚠️ Detach failed for '{res_id}': {e}")

            try:
                print(f"   ⚡ Deactivating '{name}'...")
                nac_client.slice.deactivate(name)
            except Exception as e:
                print(f"   ⚠️ Deactivate call failed: {e}\n")
                continue

            start = time.time()
            while state != "AVAILABLE" and (time.time() - start) < max_poll_seconds:
                time.sleep(poll_interval)
                try:
                    fresh = nac_client.slice.get_slice(name)
                    state = _get_state(fresh)
                except Exception as e:
                    print(f"   ⚠️ get_slice failed while polling: {e}")
                    break
                print(f"   [waiting] state: {state}")

            if state != "AVAILABLE":
                print(f"   ❌ '{name}' never reached AVAILABLE after {max_poll_seconds}s, attempting direct delete...\n")

        # FIX 3: PENDING, AVAILABLE, and FAILED slices are deleted directly
        try:
            nac_client.slice.delete_slice(name)
            print(f"   🗑️ Deleted '{name}'.\n")
        except Exception as e:
            print(f"   ❌ Failed to delete '{name}': {e}\n")

    print("✅ Cleanup pass complete.")


if __name__ == "__main__":
    cleanup_all_slices()