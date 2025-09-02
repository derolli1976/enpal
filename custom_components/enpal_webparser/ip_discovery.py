import asyncio
import aiohttp
import psutil
import ipaddress
from bs4 import BeautifulSoup

DEVICE_MESSAGES_PATH = "/deviceMessages"
IDENTIFY_TEXT = "Device Messages"
IDENTIFY_CLASS = "m-3"

import psutil
import ipaddress

def get_local_subnet() -> ipaddress.IPv4Network:
    for iface, snics in psutil.net_if_addrs().items():
        for snic in snics:
            if snic.family.name == 'AF_INET' and not snic.address.startswith("127."):
                local_ip = snic.address
                netmask = snic.netmask
                return ipaddress.ip_network(f"{local_ip}/{netmask}", strict=False)
    raise RuntimeError("Kein gültiges Subnetz gefunden.")


async def check_ip(session: aiohttp.ClientSession, ip: str) -> str | None:
    url = f"http://{ip}{DEVICE_MESSAGES_PATH}"
    try:
        async with session.get(url, timeout=2) as response:
            if response.status != 200:
                return None
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")
            h1 = soup.find("h1", class_=IDENTIFY_CLASS)
            if h1 and h1.text.strip() == IDENTIFY_TEXT:
                return ip
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return None
    return None

async def scan_for_enpal_box() -> list[str]:
    subnet = get_local_subnet()
    ips = [str(ip) for ip in subnet.hosts()]
    found_ips = []

    async with aiohttp.ClientSession() as session:
        tasks = [check_ip(session, ip) for ip in ips]
        results = await asyncio.gather(*tasks)

    return [ip for ip in results if ip]
