#!/usr/bin/env python3
"""
Event Handler
Captures events from HID devices and emits to Home Assistant and/or MQTT
"""

import os
import time
import struct
import select
import logging
import threading
import json
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    logging.warning("paho-mqtt not available, MQTT output disabled")

logger = logging.getLogger(__name__)

class EventHandler:
    """Handles event capture and emission"""

    # Event format: struct input_event (see linux/input.h)
    # long sec, long usec, ushort type, ushort code, int value
    EVENT_FORMAT = 'llHHi'
    EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

    # Event types
    EV_SYN = 0x00
    EV_KEY = 0x01
    EV_REL = 0x02

    # Key states
    KEY_UP = 0
    KEY_DOWN = 1
    KEY_REPEAT = 2

    # Relative axes
    REL_WHEEL = 0x08
    REL_HWHEEL = 0x06

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.running = False
        self.device_threads = {}
        self.device_fds = {}
        self.mqtt_client = None

        # Rate limiting state
        self.last_event_time = defaultdict(float)

        # Long press state
        self.key_press_times = defaultdict(dict)

        # Scroll burst state
        self.scroll_burst_buffer = defaultdict(lambda: {'value': 0, 'time': 0})

    def start_monitoring(self, devices: List[Dict[str, Any]]):
        """Start monitoring selected devices"""
        config = self.config_manager.get_all()

        # Initialize MQTT if needed
        if config.get('send_mqtt') and MQTT_AVAILABLE:
            self._init_mqtt()

        self.running = True

        for device in devices:
            self._start_device_monitor(device)

        logger.info(f"Monitoring {len(devices)} devices")

    def update_devices(self, devices: List[Dict[str, Any]]):
        """Update monitored devices (for hotplug)"""
        current_paths = set(self.device_fds.keys())
        new_paths = set(d['event_path'] for d in devices)

        # Stop removed devices
        for path in current_paths - new_paths:
            self._stop_device_monitor(path)

        # Start new devices
        for device in devices:
            if device['event_path'] not in current_paths:
                self._start_device_monitor(device)

    def _start_device_monitor(self, device: Dict[str, Any]):
        """Start monitoring a single device"""
        event_path = device['event_path']

        try:
            # Open device for reading
            fd = os.open(event_path, os.O_RDONLY | os.O_NONBLOCK)
            self.device_fds[event_path] = fd

            # Start thread for this device
            thread = threading.Thread(
                target=self._monitor_device,
                args=(device, fd),
                daemon=True
            )
            thread.start()
            self.device_threads[event_path] = thread

            logger.info(f"Started monitoring: {device['name']} ({event_path})")

        except Exception as e:
            logger.error(f"Failed to open {event_path}: {e}")

    def _stop_device_monitor(self, event_path: str):
        """Stop monitoring a device"""
        if event_path in self.device_fds:
            try:
                os.close(self.device_fds[event_path])
            except:
                pass
            del self.device_fds[event_path]

        if event_path in self.device_threads:
            del self.device_threads[event_path]

        logger.info(f"Stopped monitoring: {event_path}")

    def _monitor_device(self, device: Dict[str, Any], fd: int):
        """Monitor a single device (runs in thread)"""
        config = self.config_manager.get_all()
        debounce_ms = config.get('debounce_ms', 30)

        while self.running:
            try:
                # Use select to avoid busy waiting
                ready, _, _ = select.select([fd], [], [], 1.0)
                if not ready:
                    continue

                # Read event
                data = os.read(fd, self.EVENT_SIZE)
                if len(data) < self.EVENT_SIZE:
                    continue

                # Unpack event
                sec, usec, ev_type, code, value = struct.unpack(self.EVENT_FORMAT, data)

                # Skip SYN events
                if ev_type == self.EV_SYN:
                    continue

                # Apply debounce
                if debounce_ms > 0:
                    time.sleep(debounce_ms / 1000.0)

                # Process event
                if ev_type == self.EV_KEY:
                    self._handle_key_event(device, code, value)
                elif ev_type == self.EV_REL:
                    self._handle_rel_event(device, code, value)

            except Exception as e:
                if self.running:
                    logger.error(f"Error monitoring {device['name']}: {e}")
                break

    def _handle_key_event(self, device: Dict[str, Any], code: int, value: int):
        """Handle keyboard event"""
        config = self.config_manager.get_all()

        # Filter key repeat if configured
        if value == self.KEY_REPEAT and config.get('ignore_key_repeat', True):
            return

        # Filter key release if configured
        if value == self.KEY_UP and not config.get('emit_release_events', True):
            return

        # Apply rate limiting
        if not self._check_rate_limit(device):
            return

        # Get key name
        key_name = self._get_key_name(code)

        # Apply keymap override
        keymap_override = config.get('keymap_override', {})
        if key_name in keymap_override:
            key_name = keymap_override[key_name]

        # Determine state
        if value == self.KEY_DOWN:
            state = "down"
            # Track press time for long press detection
            self.key_press_times[device['device_id']][code] = time.time()
        elif value == self.KEY_UP:
            state = "up"
            # Check for long press
            if self._is_long_press(device, code):
                self._emit_long_press_event(device, key_name)
            # Clear press time
            self.key_press_times[device['device_id']].pop(code, None)
        else:
            state = "repeat"

        # Emit event
        self._emit_event(device, "key", key_name, state, value)

    def _handle_rel_event(self, device: Dict[str, Any], code: int, value: int):
        """Handle relative motion event (scroll)"""
        config = self.config_manager.get_all()

        # Filter scrolling if configured
        if config.get('filter_scrolling', False):
            return

        # Only handle scroll events
        if code not in [self.REL_WHEEL, self.REL_HWHEEL]:
            return

        # Apply rate limiting
        if not self._check_rate_limit(device):
            return

        # Get scroll scaling (apply AFTER merging)
        scale = config.get('scroll_step_scale', 1.0)

        # Handle scroll burst merging
        burst_window = config.get('scroll_burst_window_ms', 120)
        if burst_window > 0:
            key = f"{device['device_id']}_{code}"
            now = time.time() * 1000  # milliseconds
            last_time = self.scroll_burst_buffer[key]['time']

            if now - last_time < burst_window:
                # Within burst window, accumulate RAW values
                self.scroll_burst_buffer[key]['value'] += value
                self.scroll_burst_buffer[key]['time'] = now
                return
            else:
                # Emit accumulated burst with scaling applied AFTER merging
                if self.scroll_burst_buffer[key]['value'] != 0:
                    axis = "REL_WHEEL" if code == self.REL_WHEEL else "REL_HWHEEL"
                    scaled_value = int(self.scroll_burst_buffer[key]['value'] * scale)
                    self._emit_event(device, "scroll", axis, None, scaled_value)

                # Start new burst with raw value
                self.scroll_burst_buffer[key] = {'value': value, 'time': now}
                return

        # Emit scroll event immediately with scaling
        axis = "REL_WHEEL" if code == self.REL_WHEEL else "REL_HWHEEL"
        scaled_value = int(value * scale)
        self._emit_event(device, "scroll", axis, None, scaled_value)

    def _check_rate_limit(self, device: Dict[str, Any]) -> bool:
        """Check if event passes rate limiting"""
        config = self.config_manager.get_all()
        rate_limit_hz = config.get('rate_limit_per_device_hz', 50)

        if rate_limit_hz <= 0:
            return True

        device_id = device['device_id']
        now = time.time()
        last_time = self.last_event_time[device_id]
        min_interval = 1.0 / rate_limit_hz

        if now - last_time < min_interval:
            return False

        self.last_event_time[device_id] = now
        return True

    def _is_long_press(self, device: Dict[str, Any], code: int) -> bool:
        """Check if key press was a long press"""
        config = self.config_manager.get_all()
        device_id = device['device_id']

        if code not in self.key_press_times[device_id]:
            return False

        press_time = self.key_press_times[device_id][code]
        duration_ms = (time.time() - press_time) * 1000

        # Check device-specific override
        overrides = config.get('long_press_overrides', {})
        threshold = overrides.get(device['name'], config.get('long_press_ms_default', 500))

        return duration_ms >= threshold

    def _emit_long_press_event(self, device: Dict[str, Any], key_name: str):
        """Emit a long press event"""
        self._emit_event(device, "long_press", key_name, None, 1)

    def _emit_event(self, device: Dict[str, Any], event_type: str, key_code: str, key_state: Optional[str], value: int):
        """Emit event to Home Assistant and/or MQTT"""
        config = self.config_manager.get_all()

        # Build event payload
        payload = {
            "device_id": device['device_id'],
            "device_name": device['name'],
            "source": device['source'],
            "event_type": event_type,
            "key_code": key_code,
            "value": value,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        if key_state is not None:
            payload["key_state"] = key_state

        # Emit to Home Assistant
        if config.get('send_events', True):
            self._emit_ha_event(payload)

        # Emit to MQTT
        if config.get('send_mqtt', False):
            self._emit_mqtt_event(payload)

    def _emit_ha_event(self, payload: Dict[str, Any]):
        """Emit event to Home Assistant"""
        try:
            # Use Supervisor API
            supervisor_token = os.environ.get('SUPERVISOR_TOKEN')
            if not supervisor_token:
                logger.warning("SUPERVISOR_TOKEN not available")
                return

            url = "http://supervisor/core/api/events/hid_remote_event"
            headers = {
                "Authorization": f"Bearer {supervisor_token}",
                "Content-Type": "application/json"
            }

            response = requests.post(url, json=payload, headers=headers, timeout=5)
            if response.status_code == 200:
                logger.debug(f"HA event sent: {payload['event_type']} {payload['key_code']}")
            else:
                logger.warning(f"Failed to send HA event: {response.status_code}")

        except Exception as e:
            logger.error(f"Error sending HA event: {e}")

    def _emit_mqtt_event(self, payload: Dict[str, Any]):
        """Emit event to MQTT"""
        if not self.mqtt_client or not self.mqtt_client.is_connected():
            logger.warning("MQTT not connected")
            return

        try:
            config = self.config_manager.get_all()
            topic = config.get('mqtt_topic', 'key_remap/events')
            qos = config.get('mqtt_qos', 1)
            retain = config.get('mqtt_retain', False)

            message = json.dumps(payload)
            self.mqtt_client.publish(topic, message, qos=qos, retain=retain)
            logger.debug(f"MQTT event sent: {payload['event_type']} {payload['key_code']}")

        except Exception as e:
            logger.error(f"Error sending MQTT event: {e}")

    def _init_mqtt(self):
        """Initialize MQTT client"""
        if not MQTT_AVAILABLE:
            logger.error("MQTT requested but paho-mqtt not available")
            return

        try:
            config = self.config_manager.get_all()

            self.mqtt_client = mqtt.Client()

            # Set username/password if provided
            username = config.get('mqtt_user')
            password = config.get('mqtt_pass')
            if username:
                self.mqtt_client.username_pw_set(username, password)

            # Connect
            host = config.get('mqtt_host', '192.168.1.160')
            port = config.get('mqtt_port', 1883)

            self.mqtt_client.connect(host, port, keepalive=60)
            self.mqtt_client.loop_start()

            logger.info(f"MQTT connected to {host}:{port}")

        except Exception as e:
            logger.error(f"Failed to initialize MQTT: {e}")
            self.mqtt_client = None

    def _get_key_name(self, code: int) -> str:
        """Get key name from code"""
        # This is a simplified mapping; full mapping would be larger
        # For now, return generic name
        key_map = {
            28: "KEY_ENTER",
            1: "KEY_ESC",
            57: "KEY_SPACE",
            115: "KEY_VOLUMEUP",
            114: "KEY_VOLUMEDOWN",
            113: "KEY_MUTE",
            163: "KEY_NEXTSONG",
            165: "KEY_PREVIOUSSONG",
            164: "KEY_PLAYPAUSE",
        }
        return key_map.get(code, f"KEY_{code}")

    def stop(self):
        """Stop all monitoring"""
        logger.info("Stopping event handler...")
        self.running = False

        # Close all device file descriptors
        for event_path in list(self.device_fds.keys()):
            self._stop_device_monitor(event_path)

        # Disconnect MQTT
        if self.mqtt_client:
            try:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            except:
                pass

        logger.info("Event handler stopped")
