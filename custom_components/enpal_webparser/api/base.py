"""Abstract Base Class for Enpal API Clients"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class EnpalApiClient(ABC):
    """Abstract base class for Enpal API clients"""

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to Enpal Box.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def fetch_data(self) -> Dict:
        """
        Fetch data from Enpal Box.
        
        Returns:
            Dictionary with structure:
            {
                'sensors': List[Dict[str, Any]],  # Sensor dictionaries
                'source': str,  # 'html' or 'websocket'
            }
            
            Sensor dict format:
            {
                'name': str,              # Friendly name with group prefix
                'value': str,             # String representation of value
                'unit': Optional[str],    # Unit (kWh, W, V, etc.)
                'device_class': Optional[str],  # HA device class
                'enabled': bool,          # If sensor group is enabled
                'enpal_last_update': Optional[str],  # ISO timestamp
                'group': str,             # Group name (Battery, Inverter, etc.)
            }
            
        Raises:
            RuntimeError: If not connected
            TimeoutError: If data fetch times out
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connection to Enpal Box"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check connection status.
        
        Returns:
            True if connected, False otherwise
        """
        pass
