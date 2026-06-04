# pyright: reportIncompatibleVariableOverride=false
#
# Home Assistant Custom Component: Enpal Webparser
#
# File: wallbox_api.py
#
# Description:
#   Centralized Wallbox API client for Enpal wallbox control.
#   Supports two modes:
#   - Native: Direct Blazor SignalR connection to /wallbox (no addon needed)
#   - Legacy: HTTP calls to external wallbox addon on port 36725
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

# Legacy addon endpoint (kept for backward compatibility)
_LEGACY_ADDON_ENDPOINT = "http://localhost:36725/wallbox"

_LOGGER = logging.getLogger(__name__)


class WallboxApiClient:
    """Centralized client for Enpal Wallbox control.

    Supports native Blazor mode (direct connection to Enpal Box /wallbox page)
    or legacy addon mode (HTTP calls to localhost:36725).
    """

    def __init__(
        self,
        hass: HomeAssistant,
        base_url: str = _LEGACY_ADDON_ENDPOINT,
        enpal_base_url: Optional[str] = None,
        use_native: bool = False,
    ):
        """Initialize the Wallbox API client.

        Args:
            hass: Home Assistant instance
            base_url: Base URL for the legacy wallbox addon API
            enpal_base_url: Base URL of the Enpal Box (e.g. http://192.168.2.70)
            use_native: If True, use native Blazor connection instead of addon
        """
        self._hass = hass
        self._base_url = base_url.rstrip("/")
        self._enpal_base_url = enpal_base_url
        self._use_native = use_native
        self._blazor_client = None

        if use_native:
            _LOGGER.info("[Enpal] WallboxApiClient using native Blazor mode (URL: %s)", enpal_base_url)
        else:
            _LOGGER.debug("[Enpal] WallboxApiClient using legacy addon mode (URL: %s)", self._base_url)

    async def _ensure_blazor_client(self) -> bool:
        """Ensure the native Blazor client is connected and not stale.

        The Blazor client is available whenever the Enpal box URL is known,
        independent of ``use_native`` - this allows control actions (button
        clicks) to use Blazor even in legacy/HTML status mode.
        """
        if not self._enpal_base_url:
            return False

        from .api.wallbox_client import WallboxBlazorClient

        if self._blazor_client is None:
            self._blazor_client = WallboxBlazorClient(self._enpal_base_url)

        return await self._blazor_client.ensure_fresh_connection()

    @property
    def _blazor_enabled(self) -> bool:
        """Whether Blazor-based control is possible (Enpal box URL known)."""
        return bool(self._enpal_base_url)

    async def _control(self, action_name: str, blazor_action, addon_endpoint: str) -> bool:
        """Run a control action, preferring Blazor with addon fallback.

        Args:
            action_name: Human-readable action name for logging.
            blazor_action: Zero-arg coroutine function performing the Blazor click.
            addon_endpoint: Legacy addon endpoint to fall back to (e.g. "/set_eco").

        Returns:
            True if either the Blazor action or the addon call succeeded.
        """
        # Prefer the native Blazor button click (works on firmware >= 8.50 and
        # does not depend on the external addon).
        if self._blazor_enabled:
            if await self._ensure_blazor_client():
                try:
                    if await blazor_action():
                        _LOGGER.info("[Enpal] Wallbox %s via Blazor succeeded", action_name)
                        return True
                    _LOGGER.warning(
                        "[Enpal] Wallbox %s via Blazor returned failure, falling back to addon",
                        action_name,
                    )
                except Exception as e:  # noqa: BLE001 - fall back to addon
                    _LOGGER.warning(
                        "[Enpal] Wallbox %s via Blazor raised %s, falling back to addon",
                        action_name, e,
                    )
            else:
                _LOGGER.warning(
                    "[Enpal] Blazor client unavailable for %s, falling back to addon",
                    action_name,
                )

        # Legacy fallback: HTTP call to the addon on localhost:36725.
        return await self._post(addon_endpoint)

    async def close(self) -> None:
        """Close the native Blazor client if active."""
        if self._blazor_client:
            await self._blazor_client.close()
            self._blazor_client = None

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
        return await self._control(
            "start", lambda: self._blazor_client.start_charging(), "/start"
        )

    async def stop_charging(self) -> bool:
        """Stop wallbox charging."""
        _LOGGER.info("[Enpal] Stopping wallbox charging")
        return await self._control(
            "stop", lambda: self._blazor_client.stop_charging(), "/stop"
        )

    async def set_mode_eco(self) -> bool:
        """Set wallbox to Eco mode."""
        _LOGGER.info("[Enpal] Setting wallbox to Eco mode")
        return await self._control(
            "set Eco", lambda: self._blazor_client.set_mode("eco"), "/set_eco"
        )

    async def set_mode_solar(self) -> bool:
        """Set wallbox to Solar mode."""
        _LOGGER.info("[Enpal] Setting wallbox to Solar mode")
        return await self._control(
            "set Solar", lambda: self._blazor_client.set_mode("solar"), "/set_solar"
        )

    async def set_mode_full(self) -> bool:
        """Set wallbox to Full mode."""
        _LOGGER.info("[Enpal] Setting wallbox to Full mode")
        return await self._control(
            "set Full", lambda: self._blazor_client.set_mode("full"), "/set_full"
        )

    async def set_mode_smart(self) -> bool:
        """Set wallbox to Smart mode."""
        _LOGGER.info("[Enpal] Setting wallbox to Smart mode")
        return await self._control(
            "set Smart", lambda: self._blazor_client.set_mode("smart"), "/set_smart"
        )

    async def get_status(self, timeout: int = 15) -> Optional[dict]:
        """Get current wallbox status.
        
        Args:
            timeout: Request timeout in seconds (default: 15)
        
        Returns:
            Status dict with 'mode' and 'status' keys, or None if failed
        """
        if self._use_native:
            if not await self._ensure_blazor_client():
                return None
            return await self._blazor_client.get_wallbox_data()
        return await self._get("/status", timeout=timeout)

    async def call_and_refresh_sensors(
        self,
        endpoint: str,
        sensor_entities: list[str],
        wait_time: float = 2.0
    ) -> bool:
        """Call API endpoint and refresh related sensors.
        
        For native mode, the endpoint is mapped to the corresponding action.
        For legacy mode, it calls the addon HTTP endpoint directly.
        
        Args:
            endpoint: API endpoint to call (e.g. "/start", "/set_eco")
            sensor_entities: List of sensor entity IDs to refresh
            wait_time: Seconds to wait before refreshing sensors
            
        Returns:
            True if API call was successful
        """
        # Map endpoint names to control actions. Each action prefers the native
        # Blazor client and falls back to the legacy addon when needed, so this
        # works the same in legacy/HTML and websocket modes.
        endpoint_map = {
            "/start": self.start_charging,
            "/stop": self.stop_charging,
            "/set_eco": self.set_mode_eco,
            "/set_solar": self.set_mode_solar,
            "/set_full": self.set_mode_full,
            "/set_smart": self.set_mode_smart,
        }
        action = endpoint_map.get(endpoint)
        if action is None:
            _LOGGER.warning("[Enpal] Unknown wallbox endpoint: %s", endpoint)
            return False
        success = await action()
        
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
