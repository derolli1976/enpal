"""HTML client for Enpal Box using existing HTML parser"""
import logging
from typing import Dict, List, Any
import aiohttp
from bs4 import BeautifulSoup

from .base import EnpalApiClient

_LOGGER = logging.getLogger(__name__)


class EnpalHtmlClient(EnpalApiClient):
    """HTML parser client for Enpal Box (legacy/fallback mode)"""
    
    def __init__(self, base_url: str, groups: List[str]):
        """
        Initialize HTML client.
        
        Args:
            base_url: Base URL of Enpal Box (e.g., http://192.168.1.100)
            groups: List of sensor groups to parse
        """
        self.base_url = base_url.rstrip('/')
        self.groups = groups
        self.session: aiohttp.ClientSession = None
        self.connected: bool = False
    
    async def connect(self) -> bool:
        """
        Establish HTTP session.
        
        Returns:
            True (HTTP doesn't need explicit connection)
        """
        self.session = aiohttp.ClientSession()
        self.connected = True
        _LOGGER.info("[Enpal HTML Client] HTTP session ready for %s", self.base_url)
        return True
    
    async def fetch_data(self) -> Dict:
        """
        Fetch data from Enpal Box via HTTP and parse HTML.
        
        Returns:
            Dictionary with 'sensors' key containing List[Dict[str, Any]]
            
        Raises:
            RuntimeError: If not connected
            Exception: If HTTP request fails
        """
        if not self.connected:
            raise RuntimeError("Not connected to Enpal Box")
        
        url = f"{self.base_url}/deviceMessages"
        
        try:
            _LOGGER.debug("[Enpal HTML Client] Fetching HTML from %s", url)
            
            async with self.session.get(url, timeout=30) as resp:
                if resp.status != 200:
                    raise Exception(f"HTTP {resp.status} from {url}")
                
                html = await resp.text()
            
            _LOGGER.debug("[Enpal HTML Client] HTML fetched, parsing...")
            
            # Parse HTML with BeautifulSoup
            from bs4 import BeautifulSoup
            
            # Import parse function - handle both package and standalone mode
            try:
                from ..utils import parse_enpal_html_sensors
            except ImportError:
                # Standalone mode - import directly
                import sys
                from pathlib import Path
                parent_dir = Path(__file__).parent.parent
                sys.path.insert(0, str(parent_dir))
                from utils import parse_enpal_html_sensors
            
            sensors = parse_enpal_html_sensors(html, self.groups)
            
            _LOGGER.info(
                "[Enpal HTML Client] Parsed %d sensors from HTML",
                len(sensors)
            )
            
            return {
                'sensors': sensors,
                'source': 'html',
            }
            
        except Exception as e:
            _LOGGER.error("[Enpal HTML Client] Fetch failed: %s", e)
            raise
    
    async def close(self) -> None:
        """Close HTTP session"""
        self.connected = False
        
        if self.session:
            await self.session.close()
        
        _LOGGER.info("[Enpal HTML Client] Session closed")
    
    def is_connected(self) -> bool:
        """Check if session is ready"""
        return self.connected
