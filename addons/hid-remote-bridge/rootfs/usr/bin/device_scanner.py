#!/usr/bin/env python3
"""
Device Scanner
Discovers and manages HID input devices
"""

import os
import re
import glob
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class DeviceScanner:
    """Scans and manages HID input devices"""

    # Bus types
    BUS_TYPES = {
        0x03: "usb",
        0x05: "bluetooth",
        0x11: "virtual",
        0x19: "i2c"
    }

    # Event types (from linux/input-event-codes.h)
    EV_KEY = 0x01
    EV_REL = 0x02
    EV_ABS = 0x03

    # Relative axes
    REL_X = 0x00
    REL_Y = 0x01
    REL_WHEEL = 0x08
    REL_HWHEEL = 0x06

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.discovered_devices = []
        self.selected_devices = []

    def scan_devices(self) -> List[Dict[str, Any]]:
        """Scan /dev/input for event devices"""
        config = self.config_manager.get_all()
        deny_names = config.get('deny_names', [])
        filter_mice = config.get('filter_mouse_devices', False)

        devices = []
        event_paths = sorted(glob.glob('/dev/input/event*'))

        for event_path in event_paths:
            try:
                device_info = self._read_device_info(event_path)
                if not device_info:
                    continue

                # Apply deny list (always ignored)
                if self._is_denied(device_info['name'], deny_names):
                    logger.debug(f"Denied device: {device_info['name']}")
                    continue

                # Mandatory movement filter (always on)
                if self._is_pure_pointer(device_info):
                    logger.debug(f"Filtered pure pointer device: {device_info['name']}")
                    continue

                # Optional mouse device filter
                if filter_mice and self._is_mouse(device_info):
                    logger.debug(f"Filtered mouse device: {device_info['name']}")
                    continue

                # Keep devices with keys and/or scroll
                if device_info.get('has_keys') or device_info.get('has_scroll'):
                    devices.append(device_info)
                    logger.debug(f"Discovered: {device_info['name']} ({device_info['source']})")

            except Exception as e:
                logger.warning(f"Failed to read {event_path}: {e}")

        self.discovered_devices = devices

        # Restore previous selections
        self._restore_selections()

        logger.info(f"Discovered {len(devices)} HID devices")
        return devices

    def _read_device_info(self, event_path: str) -> Optional[Dict[str, Any]]:
        """Read device information from sysfs"""
        try:
            # Get event number
            event_num = re.search(r'event(\d+)$', event_path)
            if not event_num:
                return None
            event_num = event_num.group(1)

            sysfs_path = f"/sys/class/input/event{event_num}/device"
            if not os.path.exists(sysfs_path):
                return None

            # Read device attributes
            name = self._read_sysfs(sysfs_path, "name") or "Unknown"
            phys = self._read_sysfs(sysfs_path, "phys") or ""
            uniq = self._read_sysfs(sysfs_path, "uniq") or ""

            # Read device ID
            id_path = os.path.join(sysfs_path, "id")
            bustype = self._read_sysfs_int(id_path, "bustype", base=16)
            vendor = self._read_sysfs_int(id_path, "vendor", base=16)
            product = self._read_sysfs_int(id_path, "product", base=16)

            # Read capabilities
            capabilities = self._read_capabilities(sysfs_path)

            # Determine source (USB, Bluetooth, etc.)
            source = self.BUS_TYPES.get(bustype, "unknown")

            # Generate stable device ID
            device_id = self._generate_device_id(name, phys, uniq)

            device_info = {
                "event_path": event_path,
                "event_num": event_num,
                "name": name,
                "phys": phys,
                "uniq": uniq,
                "bustype": bustype,
                "source": source,
                "vendor": f"{vendor:04x}" if vendor else "",
                "product": f"{product:04x}" if product else "",
                "device_id": device_id,
                "capabilities": capabilities,
                "has_keys": self.EV_KEY in capabilities,
                "has_rel": self.EV_REL in capabilities,
                "has_scroll": self._has_scroll(capabilities),
                "selected": False
            }

            return device_info

        except Exception as e:
            logger.debug(f"Error reading device info for {event_path}: {e}")
            return None

    def _read_sysfs(self, base_path: str, attr: str) -> Optional[str]:
        """Read a sysfs attribute"""
        try:
            attr_path = os.path.join(base_path, attr)
            if os.path.exists(attr_path):
                with open(attr_path, 'r') as f:
                    return f.read().strip()
        except:
            pass
        return None

    def _read_sysfs_int(self, base_path: str, attr: str, base=10) -> Optional[int]:
        """Read a sysfs integer attribute"""
        value = self._read_sysfs(base_path, attr)
        if value:
            try:
                return int(value, base)
            except:
                pass
        return None

    def _read_capabilities(self, sysfs_path: str) -> Dict[int, List[int]]:
        """Read device capabilities (event types and codes)"""
        capabilities = {}
        caps_path = os.path.join(sysfs_path, "capabilities")

        if not os.path.exists(caps_path):
            return capabilities

        # Read event type bitmasks
        ev_file = os.path.join(caps_path, "ev")
        if os.path.exists(ev_file):
            with open(ev_file, 'r') as f:
                ev_mask = int(f.read().strip(), 16)
                # Check which event types are supported
                if ev_mask & (1 << self.EV_KEY):
                    capabilities[self.EV_KEY] = self._read_key_capabilities(caps_path)
                if ev_mask & (1 << self.EV_REL):
                    capabilities[self.EV_REL] = self._read_rel_capabilities(caps_path)

        return capabilities

    def _read_key_capabilities(self, caps_path: str) -> List[int]:
        """Read supported key codes"""
        key_file = os.path.join(caps_path, "key")
        if os.path.exists(key_file):
            with open(key_file, 'r') as f:
                # Just return a marker; full parsing is complex
                return [1]  # Non-empty means has keys
        return []

    def _read_rel_capabilities(self, caps_path: str) -> List[int]:
        """Read supported relative axes"""
        rel_codes = []
        rel_file = os.path.join(caps_path, "rel")
        if os.path.exists(rel_file):
            with open(rel_file, 'r') as f:
                rel_mask = int(f.read().strip(), 16)
                # Check for specific axes
                if rel_mask & (1 << self.REL_X):
                    rel_codes.append(self.REL_X)
                if rel_mask & (1 << self.REL_Y):
                    rel_codes.append(self.REL_Y)
                if rel_mask & (1 << self.REL_WHEEL):
                    rel_codes.append(self.REL_WHEEL)
                if rel_mask & (1 << self.REL_HWHEEL):
                    rel_codes.append(self.REL_HWHEEL)
        return rel_codes

    def _has_scroll(self, capabilities: Dict[int, List[int]]) -> bool:
        """Check if device supports scroll wheels"""
        if self.EV_REL in capabilities:
            rel_codes = capabilities[self.EV_REL]
            return self.REL_WHEEL in rel_codes or self.REL_HWHEEL in rel_codes
        return False

    def _is_pure_pointer(self, device_info: Dict[str, Any]) -> bool:
        """Check if device is pure pointer movement (REL_X/REL_Y only, no keys/scroll)"""
        if not device_info.get('has_rel'):
            return False

        if device_info.get('has_keys') or device_info.get('has_scroll'):
            return False

        # Has REL but no keys or scroll -> pure pointer movement
        caps = device_info.get('capabilities', {})
        if self.EV_REL in caps:
            rel_codes = caps[self.EV_REL]
            # If it only has X/Y movement, filter it out
            if self.REL_X in rel_codes or self.REL_Y in rel_codes:
                return True

        return False

    def _is_mouse(self, device_info: Dict[str, Any]) -> bool:
        """Check if device is classified as a mouse"""
        name_lower = device_info['name'].lower()
        mouse_keywords = ['mouse', 'trackball', 'touchpad', 'pointing']
        return any(keyword in name_lower for keyword in mouse_keywords)

    def _is_denied(self, name: str, deny_names: List[str]) -> bool:
        """Check if device name is in deny list"""
        return name in deny_names

    def _generate_device_id(self, name: str, phys: str, uniq: str) -> str:
        """Generate stable device ID"""
        # Prefer unique ID (MAC address for BT devices)
        if uniq:
            return f"uniq_{uniq}"

        # Fallback to hash of name+phys
        combined = f"{name}_{phys}"
        hash_val = hashlib.md5(combined.encode()).hexdigest()[:12]
        return f"hash_{hash_val}"

    def _restore_selections(self):
        """Restore previously selected devices"""
        config = self.config_manager.get_all()
        saved_selections = config.get('selected_devices', [])

        for device in self.discovered_devices:
            # Match by device_id
            if device['device_id'] in saved_selections:
                device['selected'] = True
            # Also match by name+uniq for backwards compat
            elif any(s == device['name'] or s == device['uniq'] for s in saved_selections):
                device['selected'] = True

        self._update_selected_devices()

    def _update_selected_devices(self):
        """Update list of selected devices"""
        self.selected_devices = [d for d in self.discovered_devices if d.get('selected')]

    def get_discovered_devices(self) -> List[Dict[str, Any]]:
        """Get all discovered devices"""
        return self.discovered_devices

    def get_selected_devices(self) -> List[Dict[str, Any]]:
        """Get selected devices for monitoring"""
        return self.selected_devices

    def select_device(self, device_id: str):
        """Select a device for monitoring"""
        for device in self.discovered_devices:
            if device['device_id'] == device_id:
                device['selected'] = True
                break
        self._update_selected_devices()
        self._save_selections()

    def deselect_device(self, device_id: str):
        """Deselect a device"""
        for device in self.discovered_devices:
            if device['device_id'] == device_id:
                device['selected'] = False
                break
        self._update_selected_devices()
        self._save_selections()

    def _save_selections(self):
        """Save device selections to persistent storage"""
        selected_ids = [d['device_id'] for d in self.selected_devices]
        self.config_manager.save_persistent_data({
            'selected_devices': selected_ids
        })
