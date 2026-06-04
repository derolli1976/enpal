"""Data models for Enpal API"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class DataPoint:
    """Single data point from Enpal device"""
    value: Any
    unit: Optional[str] = None
    timestamp_utc: Optional[str] = None


@dataclass
class DeviceCollection:
    """Data collection from a single device (Inverter, Battery, Wallbox, etc.)"""
    device_id: str
    device_class: str  # "Inverter", "Battery", "Wallbox", "Heatpump", etc.
    timestamp_utc: str
    number_data_points: Dict[str, DataPoint] = field(default_factory=dict)
    text_data_points: Dict[str, DataPoint] = field(default_factory=dict)
    error_codes: List[Dict] = field(default_factory=list)


@dataclass
class CollectorData:
    """Complete collector data from Enpal Box"""
    collection_id: str
    iot_device_id: str
    timestamp_utc: str
    device_collections: List[DeviceCollection] = field(default_factory=list)
    energy_management: List[Dict] = field(default_factory=list)
    error_codes: List[Dict] = field(default_factory=list)


@dataclass
class ComponentDescriptor:
    """Blazor server component descriptor"""
    type: str = ""
    sequence: int = 0
    descriptor: str = ""
    prerender_id: str = ""
    key: Dict[str, str] = field(default_factory=dict)
