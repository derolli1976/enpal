# pyright: reportIncompatibleVariableOverride=false
#
# Home Assistant Custom Component: Enpal Webparser
#
# File: test_discovery.py
#
# Description:
#   Tests for the network discovery functionality.
#
# Author:       Oliver Stock (github.com/derolli1976)
# License:      MIT
# Repository:   https://github.com/derolli1976/enpal
#
# Compatible with Home Assistant Core 2024.x and later.
#
# To run: pytest custom_components/enpal_webparser/tests/test_discovery.py
#

import ipaddress
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from custom_components.enpal_webparser.discovery import (
    get_local_subnets,
    check_enpal_device,
)


def test_get_local_subnets_basic():
    """Test that get_local_subnets returns valid IPv4Network objects."""
    subnets = get_local_subnets()
    
    assert isinstance(subnets, list)
    
    # Should return at least one subnet (or fallback)
    assert len(subnets) > 0
    
    # All results should be IPv4Network objects
    for subnet in subnets:
        assert isinstance(subnet, ipaddress.IPv4Network)
        
        # Should be a valid CIDR subnet (not just single IP)
        assert subnet.prefixlen >= 8  # At least /8
        assert subnet.prefixlen <= 30  # At most /30


def test_get_local_subnets_excludes_localhost():
    """Test that localhost (127.x.x.x) is excluded from subnets."""
    subnets = get_local_subnets()
    
    for subnet in subnets:
        # No subnet should be in the 127.0.0.0/8 range
        assert not subnet.overlaps(ipaddress.IPv4Network("127.0.0.0/8"))


@pytest.mark.asyncio
async def test_check_enpal_device_valid():
    """Test checking a valid Enpal device."""
    # Mock Home Assistant and HTTP session
    hass = MagicMock()
    
    # Mock HTML response with Enpal markers (updated to match actual Enpal device HTML)
    mock_response = MagicMock()
    mock_response.status = 200
    # Use AsyncMock for the async text() method
    mock_response.text = AsyncMock(
        return_value='<html><h1 class="m-3">Device Messages</h1><div class="card"><h2>Inverter</h2><table></table></div></html>'
    )
    
    # Properly mock the async context manager
    mock_session = MagicMock()
    mock_get = MagicMock()
    mock_get.__aenter__ = AsyncMock(return_value=mock_response)
    mock_get.__aexit__ = AsyncMock(return_value=None)
    mock_session.get = MagicMock(return_value=mock_get)
    
    with patch('custom_components.enpal_webparser.discovery.async_get_clientsession', return_value=mock_session):
        result = await check_enpal_device(hass, "192.168.178.178")
        
        assert result == "http://192.168.178.178/deviceMessages"


@pytest.mark.asyncio
async def test_check_enpal_device_invalid():
    """Test checking an invalid device (no Enpal markers)."""
    hass = MagicMock()
    
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = MagicMock(return_value='<html><body>Not an Enpal device</body></html>')
    
    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_response)
    mock_session.get.return_value.__aenter__ = MagicMock(return_value=mock_response)
    mock_session.get.return_value.__aexit__ = MagicMock(return_value=None)
    
    with patch('custom_components.enpal_webparser.discovery.async_get_clientsession', return_value=mock_session):
        result = await check_enpal_device(hass, "192.168.1.1")
        
        assert result is None


@pytest.mark.asyncio
async def test_check_enpal_device_not_reachable():
    """Test checking a device that's not reachable."""
    hass = MagicMock()
    
    mock_session = MagicMock()
    mock_session.get = MagicMock(side_effect=Exception("Connection refused"))
    
    with patch('custom_components.enpal_webparser.discovery.async_get_clientsession', return_value=mock_session):
        result = await check_enpal_device(hass, "192.168.1.1")
        
        assert result is None
