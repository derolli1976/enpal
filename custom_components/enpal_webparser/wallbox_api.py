# pyright: reportIncompatibleVariableOverride=false
#
# Home Assistant Custom Component: Enpal Webparser
#
# File: wallbox_api.py
#
# Description:
#   Centralized Wallbox API client for Enpal wallbox control.
#   Provides a single interface for all wallbox HTTP communication.
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
import logging
from typing import Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_WALLBOX_API_ENDPOINT

_LOGGER = logging.getLogger(__name__)


class WallboxApiClient:
    """Centralized client for Enpal Wallbox API communication."""

    def __init__(self, hass: HomeAssistant, base_url: str = DEFAULT_WALLBOX_API_ENDPOINT):
        """Initialize the Wallbox API client.
        
        Args:
            hass: Home Assistant instance
            base_url: Base URL for the wallbox API (default: from const.py)
        """
        self._hass = hass
        self._base_url = base_url.rstrip("/")
        _LOGGER.debug("[Enpal] WallboxApiClient initialized with base URL: %s", self._base_url)

    async def _post(self, endpoint: str, timeout: int = 30) -> bool:
        """Execute a POST request to the wallbox API.
        
        Args:
            endpoint: API endpoint (e.g., "/start", "/stop", "/set_eco")
            timeout: Request timeout in seconds
            
        Returns:
            True if successful (status 200), False otherwise
        """
        url = f"{self._base_url}{endpoint}"
        try:
            session = async_get_clientsession(self._hass)
            async with session.post(url, timeout=timeout) as response:
                if response.status != 200:
                    text = await response.text()
                    _LOGGER.warning(
                        "[Enpal] Wallbox API call failed: %s (status: %s, response: %s)",
                        url, response.status, text
                    )
                    return False
                
                _LOGGER.info("[Enpal] Wallbox API call successful: %s", url)
                return True
                
        except asyncio.TimeoutError:
            _LOGGER.error("[Enpal] Wallbox API timeout: %s", url)
            return False
        except Exception as e:
            _LOGGER.exception("[Enpal] Wallbox API request failed: %s - %s", url, e)
            return False

    async def _get(self, endpoint: str, timeout: int = 30) -> Optional[dict]:
        """Execute a GET request to the wallbox API.
        
        Args:
            endpoint: API endpoint (e.g., "/status")
            timeout: Request timeout in seconds
            
        Returns:
            JSON response dict if successful, None otherwise
        """
        url = f"{self._base_url}{endpoint}"
        try:
            session = async_get_clientsession(self._hass)
            async with session.get(url, timeout=timeout) as response:
                if response.status != 200:
                    _LOGGER.warning(
                        "[Enpal] Wallbox API GET failed: %s (status: %s)",
                        url, response.status
                    )
                    return None
                
                data = await response.json()
                _LOGGER.debug("[Enpal] Wallbox API GET successful: %s", url)
                return data
                
        except asyncio.TimeoutError:
            _LOGGER.error("[Enpal] Wallbox API GET timeout: %s", url)
            return None
        except Exception as e:
            _LOGGER.exception("[Enpal] Wallbox API GET request failed: %s - %s", url, e)
            return None

    async def start_charging(self) -> bool:
        """Start wallbox charging."""
        _LOGGER.info("[Enpal] Starting wallbox charging")
        return await self._post("/start")

    async def stop_charging(self) -> bool:
        """Stop wallbox charging."""
        _LOGGER.info("[Enpal] Stopping wallbox charging")
        return await self._post("/stop")

    async def set_mode_eco(self) -> bool:
        """Set wallbox to Eco mode."""
        _LOGGER.info("[Enpal] Setting wallbox to Eco mode")
        return await self._post("/set_eco")

    async def set_mode_solar(self) -> bool:
        """Set wallbox to Solar mode."""
        _LOGGER.info("[Enpal] Setting wallbox to Solar mode")
        return await self._post("/set_solar")

    async def set_mode_full(self) -> bool:
        """Set wallbox to Full mode."""
        _LOGGER.info("[Enpal] Setting wallbox to Full mode")
        return await self._post("/set_full")

    async def get_status(self, timeout: int = 15) -> Optional[dict]:
        """Get current wallbox status.
        
        Args:
            timeout: Request timeout in seconds (default: 15)
        
        Returns:
            Status dict from API or None if failed
        """
        return await self._get("/status", timeout=timeout)

    async def call_and_refresh_sensors(
        self,
        endpoint: str,
        sensor_entities: list[str],
        wait_time: float = 2.0
    ) -> bool:
        """Call API endpoint and refresh related sensors.
        
        This is a convenience method that:
        1. Calls the API endpoint
        2. Waits for wallbox to process
        3. Triggers sensor updates
        
        Args:
            endpoint: API endpoint to call
            sensor_entities: List of sensor entity IDs to refresh
            wait_time: Seconds to wait before refreshing sensors
            
        Returns:
            True if API call was successful
        """
        success = await self._post(endpoint)
        
        if success and sensor_entities:
            # Wait for wallbox to process the change
            await asyncio.sleep(wait_time)
            
            # Trigger sensor updates
            await self._hass.services.async_call(
                "homeassistant",
                "update_entity",
                {"entity_id": sensor_entities},
                blocking=True
            )
            _LOGGER.debug("[Enpal] Triggered refresh for sensors: %s", sensor_entities)
        
        return success
