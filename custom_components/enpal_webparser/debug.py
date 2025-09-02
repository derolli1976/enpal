import asyncio
import sys
from ip_discovery import scan_for_enpal_box

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if __name__ == "__main__":
    results = asyncio.run(scan_for_enpal_box())
    print("Gefundene Enpal Box IPs:", results)
