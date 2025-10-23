# pyright: reportIncompatibleVariableOverride=false
#
# Home Assistant Custom Component: Enpal Webparser
#
# File: discovery.py
#
# Description:
#   Network discovery utilities for finding Enpal boxes on the local network.
#   Scans subnet for devices responding to /deviceMessages endpoint.
#
# Author:       Oliver Stock (github.com/derolli1976)
# License:      MIT
# Repository:   https://github.com/derolli1976/enpal
#
# Compatible with Home Assistant Core 2024.x and later.
#
# See README.md for setup and usage instructions.
#

import asyncio
import ipaddress
import logging
from typing import List, Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from bs4 import BeautifulSoup
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

# Enpal device identification markers
DEVICE_MESSAGES_PATH = "/deviceMessages"
IDENTIFY_TEXT = "Device Messages"
IDENTIFY_CLASS = "m-3"


def get_local_subnets() -> List[ipaddress.IPv4Network]:
    """Get all local network subnets from the host machine.
    
    Uses psutil if available for cross-platform network detection.
    Only returns 192.168.x.x subnets (consumer/home networks).
    
    Returns:
        List of IPv4Network objects representing local 192.168.x.x subnets
    """
    subnets = []
    
    if HAS_PSUTIL:
        # Use psutil for reliable cross-platform network detection
        try:
            for iface, snics in psutil.net_if_addrs().items():
                for snic in snics:
                    # Check for IPv4 addresses
                    if snic.family.name == 'AF_INET' and not snic.address.startswith("127."):
                        try:
                            # Create network from IP and netmask
                            network = ipaddress.ip_network(
                                f"{snic.address}/{snic.netmask}", 
                                strict=False
                            )
                            
                            # Only include 192.168.x.x subnets (consumer/home networks)
                            if network.network_address.packed[0:2] == b'\xc0\xa8':  # 192.168 in bytes
                                if network not in subnets:
                                    subnets.append(network)
                                    _LOGGER.info("[Enpal] Detected subnet: %s (interface: %s)", network, iface)
                            else:
                                _LOGGER.debug("[Enpal] Skipping non-192.168.x.x subnet: %s", network)
                        except ValueError as e:
                            _LOGGER.debug("[Enpal] Invalid network %s/%s: %s", snic.address, snic.netmask, e)
        except Exception as e:
            _LOGGER.warning("[Enpal] psutil subnet detection failed: %s", e)
    else:
        _LOGGER.warning("[Enpal] psutil not available, using fallback detection")
    
    # Fallback if no subnets found
    if not subnets:
        _LOGGER.warning("[Enpal] No 192.168.x.x subnets detected, using 192.168.1.0/24 as fallback")
        try:
            subnets.append(ipaddress.IPv4Network("192.168.1.0/24"))
        except Exception:
            pass
    
    return subnets


async def check_enpal_device(hass: HomeAssistant, ip: str, timeout: int = 2) -> Optional[str]:
    """Check if a given IP address hosts an Enpal device.
    
    Uses the same detection method as the working reference implementation:
    Looks for <h1 class="m-3">Device Messages</h1>
    
    Args:
        hass: Home Assistant instance
        ip: IP address to check
        timeout: Request timeout in seconds (default: 2)
        
    Returns:
        Full URL if Enpal device found, None otherwise
    """
    url = f"http://{ip}{DEVICE_MESSAGES_PATH}"
    
    try:
        session = async_get_clientsession(hass)
        async with session.get(url, timeout=timeout) as response:
            if response.status != 200:
                return None
            
            # Parse HTML and look for Enpal-specific markers
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")
            
            # Look for <h1 class="m-3">Device Messages</h1>
            h1 = soup.find("h1", class_=IDENTIFY_CLASS)
            if h1 and h1.text.strip() == IDENTIFY_TEXT:
                _LOGGER.info("[Enpal] Found Enpal device at %s", url)
                return url
                
    except asyncio.TimeoutError:
        pass  # Timeout is expected for non-responsive IPs
    except Exception:
        pass  # Connection errors are expected during scanning
    
    return None


async def discover_enpal_devices(hass: HomeAssistant, progress_callback=None, max_hosts: int = 1024) -> List[str]:
    """Discover Enpal devices on the local network.
    
    Scans all IP addresses in local subnets for Enpal devices.
    
    Args:
        hass: Home Assistant instance
        progress_callback: Optional callback function(current, total) for progress updates
        max_hosts: Maximum number of hosts to scan (safety limit to prevent scanning huge networks)
        
    Returns:
        List of discovered Enpal device URLs
    """
    _LOGGER.info("[Enpal] Starting Enpal device discovery")
    
    subnets = get_local_subnets()
    if not subnets:
        _LOGGER.warning("[Enpal] No subnets found for discovery")
        return []
    
    _LOGGER.info("[Enpal] Scanning subnets: %s", [str(s) for s in subnets])
    
    discovered_urls = []
    
    # Collect all IPs to scan
    ips_to_scan = []
    total_possible_ips = 0
    
    for subnet in subnets:
        # Count total IPs in this subnet
        subnet_size = subnet.num_addresses - 2  # Exclude network and broadcast
        total_possible_ips += subnet_size
        
        # Log warning for large subnets
        if subnet_size > 254:
            _LOGGER.warning(
                "[Enpal] Large subnet detected: %s (%d hosts). This may take a while.",
                subnet, subnet_size
            )
        
        # Skip network and broadcast addresses
        for ip in subnet.hosts():
            if len(ips_to_scan) >= max_hosts:
                _LOGGER.warning(
                    "[Enpal] Reached max scan limit of %d hosts. Remaining IPs will be skipped.",
                    max_hosts
                )
                break
            ips_to_scan.append(str(ip))
        
        if len(ips_to_scan) >= max_hosts:
            break
    
    total_ips = len(ips_to_scan)
    
    # Log IP ranges being scanned
    if ips_to_scan:
        first_ip = ips_to_scan[0]
        last_ip = ips_to_scan[-1]
        _LOGGER.info(
            "[Enpal] Scanning %d IP addresses (out of %d possible) from %s to %s",
            total_ips, total_possible_ips, first_ip, last_ip
        )
    else:
        _LOGGER.info("[Enpal] No IPs to scan")
    
    # Scan in batches to avoid overwhelming the network
    batch_size = 50
    completed = 0
    
    for i in range(0, total_ips, batch_size):
        batch = ips_to_scan[i:i + batch_size]
        batch_tasks = [check_enpal_device(hass, ip) for ip in batch]
        
        results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, str):
                discovered_urls.append(result)
        
        completed += len(batch)
        
        if progress_callback:
            progress_callback(completed, total_ips)
        
        _LOGGER.debug("[Enpal] Discovery progress: %d/%d", completed, total_ips)
    
    _LOGGER.info("[Enpal] Discovery complete. Found %d device(s)", len(discovered_urls))
    return discovered_urls


async def quick_discover_enpal_devices(hass: HomeAssistant) -> List[str]:
    """Quick discovery that checks common IP patterns in detected subnets.
    
    This is faster than full subnet scan. It checks IPs ending in common patterns
    like .1, .10, .50, .100, .150, .200, .254 across all detected subnets.
    
    Args:
        hass: Home Assistant instance
        
    Returns:
        List of discovered Enpal device URLs
    """
    _LOGGER.info("[Enpal] Starting quick Enpal device discovery")
    
    # Common host numbers to check (router is often .1, devices often .10-.254)
    common_host_numbers = [1, 2, 10, 20, 50, 100, 150, 200, 250, 254]
    
    check_ips = []
    subnets = get_local_subnets()
    
    for subnet in subnets:
        # For each subnet, try common host numbers
        for host_num in common_host_numbers:
            try:
                # Create IP address from subnet base + host number
                ip = ipaddress.IPv4Address(int(subnet.network_address) + host_num)
                # Make sure it's actually in the subnet (not network or broadcast)
                if ip in subnet and ip != subnet.network_address and ip != subnet.broadcast_address:
                    check_ips.append(str(ip))
            except (ValueError, ipaddress.AddressValueError):
                continue
    
    # Log what we're scanning
    if check_ips:
        _LOGGER.info(
            "[Enpal] Quick scan checking %d IPs across %d subnet(s): %s",
            len(check_ips), len(subnets), ", ".join(check_ips[:5]) + ("..." if len(check_ips) > 5 else "")
        )
    else:
        _LOGGER.warning("[Enpal] Quick scan: No IPs to check")
    
    tasks = [check_enpal_device(hass, ip, timeout=2) for ip in check_ips]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    discovered_urls = [result for result in results if isinstance(result, str)]
    
    _LOGGER.info("[Enpal] Quick discovery found %d device(s)", len(discovered_urls))
    return discovered_urls
