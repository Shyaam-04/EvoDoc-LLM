import time
import hashlib
import json

cache_store = {}
TTL = 3600

def make_cache_key(medicines: list[str], current_medications: list[str])-> str:
    sorted_medicines = sorted([m.lower() for m in medicines])
    sorted_medications = sorted([m.lower() for m in current_medications])
    combined = {"medicines": sorted_medicines, "current_medications": sorted_medications}
    key = hashlib.md5(json.dumps(combined).encode()).hexdigest()
    return key

def get_from_cache(key: str):
    if key in cache_store and (time.time() - cache_store[key]["timestamp"])<TTL:
        return cache_store[key]["data"]
    else:
        del cache_store[key]
        return None


def save_to_cache(key: str, value: dict):
    cache_store[key] = {"data": value, "timestamp": time.time()}