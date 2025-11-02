#!/usr/bin/env python3
"""
Configuration Manager
Handles loading, validation, and persistence of add-on configuration
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages add-on configuration"""

    # Default configuration (single source of truth)
    DEFAULTS = {
        "send_events": True,
        "send_mqtt": False,
        "mqtt_host": "192.168.1.160",
        "mqtt_port": 1883,
        "mqtt_user": "mqttuser",
        "mqtt_pass": "mqttuser",
        "mqtt_topic": "key_remap/events",
        "mqtt_qos": 1,
        "mqtt_retain": False,
        "startup_delay_sec": 5,
        "ignore_key_repeat": True,
        "emit_release_events": True,
        "debounce_ms": 30,
        "rate_limit_per_device_hz": 50,
        "long_press_ms_default": 500,
        "long_press_overrides": {},
        "scroll_step_scale": 1.0,
        "scroll_burst_window_ms": 120,
        "filter_mouse_devices": False,
        "filter_scrolling": False,
        "deny_names": [
            "Power Button", "Sleep Button", "Video Bus", "Lid Switch",
            "PC Speaker", "HDA Intel HDMI/DP", "gpio-keys",
            "ACPI Video", "AT Translated Set 2 keyboard"
        ],
        "selected_devices": [],
        "keymap_override": {}
    }

    # Configuration constraints
    CONSTRAINTS = {
        "mqtt_port": (1, 65535),
        "startup_delay_sec": (0, 30),
        "debounce_ms": (0, 200),
        "rate_limit_per_device_hz": (5, 200),
        "long_press_ms_default": (200, 2000),
        "scroll_step_scale": (0.1, 5.0),
        "scroll_burst_window_ms": (50, 500),
        "mqtt_qos": (0, 2)
    }

    def __init__(self):
        # Home Assistant add-on options file
        self.options_file = Path("/data/options.json")
        # Persistent data file for device selections
        self.data_file = Path("/data/hid_bridge_data.json")
        self.config = {}

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from options.json and merge with defaults"""
        # Start with defaults
        config = self.DEFAULTS.copy()

        # Load from HA options if exists
        if self.options_file.exists():
            try:
                with open(self.options_file, 'r') as f:
                    user_options = json.load(f)
                    config.update(user_options)
                    logger.info(f"Loaded configuration from {self.options_file}")
            except Exception as e:
                logger.error(f"Failed to load options.json: {e}")

        # Also check environment variables (for container runtime)
        config = self._load_from_env(config)

        # Load persistent data (device selections)
        persistent_data = self._load_persistent_data()
        if persistent_data.get('selected_devices'):
            config['selected_devices'] = persistent_data['selected_devices']

        # Validate
        config = self._validate_config(config)

        self.config = config
        return config

    def _load_from_env(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        env_mappings = {
            "HID_SEND_EVENTS": ("send_events", lambda x: x.lower() == "true"),
            "HID_SEND_MQTT": ("send_mqtt", lambda x: x.lower() == "true"),
            "HID_MQTT_HOST": ("mqtt_host", str),
            "HID_MQTT_PORT": ("mqtt_port", int),
            "HID_MQTT_USER": ("mqtt_user", str),
            "HID_MQTT_PASS": ("mqtt_pass", str),
            "HID_MQTT_TOPIC": ("mqtt_topic", str),
            "HID_MQTT_QOS": ("mqtt_qos", int),
            "HID_MQTT_RETAIN": ("mqtt_retain", lambda x: x.lower() == "true"),
            "HID_STARTUP_DELAY": ("startup_delay_sec", int),
            "HID_IGNORE_KEY_REPEAT": ("ignore_key_repeat", lambda x: x.lower() == "true"),
            "HID_EMIT_RELEASE_EVENTS": ("emit_release_events", lambda x: x.lower() == "true"),
            "HID_DEBOUNCE_MS": ("debounce_ms", int),
            "HID_RATE_LIMIT_HZ": ("rate_limit_per_device_hz", int),
            "HID_LONG_PRESS_MS": ("long_press_ms_default", int),
            "HID_SCROLL_SCALE": ("scroll_step_scale", float),
            "HID_SCROLL_BURST_MS": ("scroll_burst_window_ms", int),
            "HID_FILTER_MICE": ("filter_mouse_devices", lambda x: x.lower() == "true"),
            "HID_FILTER_SCROLL": ("filter_scrolling", lambda x: x.lower() == "true"),
        }

        for env_var, (config_key, converter) in env_mappings.items():
            if env_var in os.environ:
                try:
                    config[config_key] = converter(os.environ[env_var])
                except Exception as e:
                    logger.warning(f"Invalid value for {env_var}: {e}")

        return config

    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration values against constraints"""
        for key, (min_val, max_val) in self.CONSTRAINTS.items():
            if key in config:
                value = config[key]
                if isinstance(value, (int, float)):
                    if value < min_val or value > max_val:
                        logger.warning(
                            f"Config '{key}' value {value} out of range [{min_val}, {max_val}], "
                            f"using default {self.DEFAULTS[key]}"
                        )
                        config[key] = self.DEFAULTS[key]

        return config

    def _load_persistent_data(self) -> Dict[str, Any]:
        """Load persistent data (device selections)"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load persistent data: {e}")
        return {}

    def save_persistent_data(self, data: Dict[str, Any]):
        """Save persistent data (device selections)"""
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info("Persistent data saved")
        except Exception as e:
            logger.error(f"Failed to save persistent data: {e}")

    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration"""
        return self.config.copy()

    def update(self, updates: Dict[str, Any]):
        """Update configuration (for web UI)"""
        self.config.update(updates)
        # Validate after update
        self.config = self._validate_config(self.config)
