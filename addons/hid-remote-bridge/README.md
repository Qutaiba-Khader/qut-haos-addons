# HID Remote Bridge

Monitor USB and Bluetooth HID devices (keyboards, remotes, game controllers) and emit their events to Home Assistant.

## Overview

This add-on reads input events from `/dev/input/eventX` devices and makes them available in Home Assistant as events. You can select which devices to monitor through an intuitive web UI, configure event filtering, and optionally mirror events to MQTT.

## Features

- **Device Discovery**: Automatically discovers USB and Bluetooth HID devices
- **Selective Monitoring**: Choose which devices to monitor via checkbox UI
- **Persistent Selections**: Device selections survive reboots (matched by unique ID or device characteristics)
- **Hotplug Support**: Automatically detects devices when plugged in or paired
- **Smart Filtering**:
  - Auto-excludes system devices (power button, lid switch, etc.)
  - Filters pure pointer movement (mouse X/Y without keys)
  - Optional mouse device filtering
- **Event Types**:
  - Key events (KeyDown, KeyUp, KeyRepeat)
  - Scroll events (vertical and horizontal)
  - Long-press detection with configurable thresholds
- **Rate Limiting**: Prevent event floods with per-device rate limiting
- **Dual Output**: Send to Home Assistant events and/or MQTT
- **Web UI**: Configure everything through tabs (Devices, Outputs, Behavior, Scrolling, Filters, Advanced)

## Installation

1. Add this repository to your Home Assistant add-on store
2. Install the "HID Remote Bridge" add-on
3. Start the add-on
4. Open the Web UI to select devices and configure options

## Configuration

### Quick Start

The add-on works out of the box with sensible defaults. Simply:

1. Start the add-on
2. Open the Web UI
3. Go to the "Devices" tab
4. Check the devices you want to monitor
5. Events will be emitted as `hid_remote_event` in Home Assistant

### Web UI Tabs

#### 1. Devices
- View all discovered HID devices
- Select devices to monitor with checkboxes
- See device type (USB/Bluetooth) and capabilities (KEYS/SCROLL)
- Rescan for new devices (hotplug)

#### 2. Outputs
- **Send events to Home Assistant**: Emit events as `hid_remote_event` (default: ON)
- **Send events to MQTT**: Mirror events to MQTT broker (default: OFF)
- MQTT settings: host, port, username, password, topic, QoS, retain

#### 3. Behavior
- **Startup delay**: Wait before scanning devices (0-60 seconds, default: 5)
- **Debounce**: Delay after each event (0-500 ms, default: 30)
- **Rate limit**: Max events per second per device (1-500 Hz, default: 50)
- **Long press threshold**: Minimum duration for long press (100-5000 ms, default: 500)
- **Ignore key repeat**: Filter out repeat events (default: ON)
- **Emit release events**: Send key-up events (default: ON)

#### 4. Scrolling
- **Scroll step scale**: Multiply scroll values (0.1-10, default: 1.0)
- **Scroll burst window**: Merge rapid scrolls within window (0-1000 ms, default: 120)
- **Filter scrolling**: Suppress all scroll events (default: OFF)

#### 5. Filters
- **Filter mouse devices**: Hide all mice from discovery (default: OFF)
- **Deny list**: Device names that are always ignored

Default deny list:
```
Power Button
Sleep Button
Video Bus
Lid Switch
PC Speaker
HDA Intel HDMI/DP
gpio-keys
```

#### 6. Advanced
- **Key remapping**: Map key names to custom values (JSON format)

Example keymap:
```json
{
  "KEY_VOLUMEUP": "KEY_CUSTOM_VOL_UP",
  "KEY_PLAYPAUSE": "KEY_MEDIA_TOGGLE"
}
```

## Event Schema

Events are emitted with the following structure:

```json
{
  "device_id": "uniq_AA:BB:CC:DD:EE:FF",
  "device_name": "Bluetooth Remote",
  "source": "bluetooth",
  "event_type": "key",
  "key_code": "KEY_VOLUMEUP",
  "key_state": "down",
  "value": 1,
  "timestamp": "2025-01-15T10:30:45Z"
}
```

### Fields

- **device_id**: Stable identifier (from unique ID or hash of name+phys)
- **device_name**: Kernel device name
- **source**: `usb`, `bluetooth`, `virtual`, or `unknown`
- **event_type**: `key`, `scroll`, or `long_press`
- **key_code**: Key name (e.g., `KEY_ENTER`) or axis (e.g., `REL_WHEEL`)
- **key_state**: `down`, `up`, or `repeat` (only for `key` events)
- **value**:
  - For keys: 1 (down), 0 (up), 2 (repeat)
  - For scroll: signed integer (positive/negative for direction)
- **timestamp**: UTC timestamp (ISO 8601)

## Usage in Home Assistant

### Listening to Events

You can listen to `hid_remote_event` events in automations:

```yaml
automation:
  - alias: "Volume Up Pressed"
    trigger:
      - platform: event
        event_type: hid_remote_event
        event_data:
          device_name: "Bluetooth Remote"
          event_type: key
          key_code: KEY_VOLUMEUP
          key_state: down
    action:
      - service: media_player.volume_up
        target:
          entity_id: media_player.living_room
```

### Developer Tools

To see events in real-time:

1. Go to **Developer Tools** → **Events**
2. Listen to `hid_remote_event`
3. Press keys on your device to see the events

### Template Example

```yaml
- sensor:
    - name: "Last Remote Key"
      state: >
        {{ state_attr('sensor.last_remote_key', 'key_code') }}
      attributes:
        device: >
          {{ trigger.event.data.device_name }}
        key_code: >
          {{ trigger.event.data.key_code }}
        key_state: >
          {{ trigger.event.data.key_state }}
      trigger:
        - platform: event
          event_type: hid_remote_event
```

## Permissions

This add-on requires the following permissions:

- **devices**: Read/write access to `/dev/input` (required for reading HID events)
- **udev**: Hotplug support (automatically detect new devices)
- **apparmor**: Enabled for security
- **network**: Only required if MQTT output is enabled

## Troubleshooting

### No devices found

1. Check that `/dev/input` exists in the container
2. Verify the add-on has `devices` permission
3. Check the add-on logs for errors
4. Try clicking "Rescan Devices"

### Device disappears after reboot

The add-on matches devices by unique ID (MAC address for Bluetooth) or by hashing name+phys. If a device's event number changes (e.g., from `event3` to `event5`), it should still be matched. If not:

1. Check the device's unique ID in the UI
2. Reselect the device
3. Check logs for matching errors

### Events not appearing in Home Assistant

1. Verify "Send events to Home Assistant" is enabled in Outputs tab
2. Check the add-on logs for event emission
3. Use Developer Tools → Events to listen for `hid_remote_event`
4. Verify the device is selected in the Devices tab

### MQTT not working

1. Verify "Send events to MQTT" is enabled
2. Check MQTT host/port/credentials
3. Test MQTT connection with a client (e.g., MQTT Explorer)
4. Check add-on logs for MQTT errors

### Too many events

Adjust these settings in the Behavior tab:

- Increase **Debounce** (e.g., 50-100 ms)
- Decrease **Rate limit** (e.g., 20-30 Hz)
- Enable **Ignore key repeat**
- Disable **Emit release events** (if you only need key-down)

### Scroll events too sensitive

Adjust these settings in the Scrolling tab:

- Decrease **Scroll step scale** (e.g., 0.5)
- Increase **Scroll burst window** (e.g., 200-300 ms) to merge rapid scrolls

## Architecture Support

This add-on supports the following architectures:

- `aarch64` (64-bit ARM, e.g., Raspberry Pi 4)
- `amd64` (64-bit Intel/AMD)
- `armhf` (32-bit ARM)
- `armv7` (32-bit ARM v7)
- `i386` (32-bit Intel)

## Security

- The add-on runs with **AppArmor** enabled for security
- `/dev/input` is accessed in **read-only mode** for event capture
- Network access is **disabled by default** (only enabled if MQTT is configured)
- MQTT password is never logged

## Advanced Configuration

### Device Selection Persistence

Device selections are stored in `/data/hid_bridge_data.json` with this format:

```json
{
  "selected_devices": [
    "uniq_AA:BB:CC:DD:EE:FF",
    "hash_a1b2c3d4e5f6"
  ]
}
```

Devices are matched in this order:
1. By `uniq` (unique ID, typically Bluetooth MAC)
2. By hash of `name + phys` (fallback for devices without unique ID)

### Long Press Per-Device Overrides

You can set different long-press thresholds for specific devices:

```json
{
  "long_press_overrides": {
    "Bluetooth Remote": 300,
    "USB Keyboard": 700
  }
}
```

## Default Configuration

```json
{
  "send_events": true,
  "send_mqtt": false,
  "mqtt_host": "192.168.1.160",
  "mqtt_port": 1883,
  "mqtt_user": "mqttuser",
  "mqtt_pass": "mqttuser",
  "mqtt_topic": "key_remap/events",
  "mqtt_qos": 1,
  "mqtt_retain": false,
  "startup_delay_sec": 5,
  "ignore_key_repeat": true,
  "emit_release_events": true,
  "debounce_ms": 30,
  "rate_limit_per_device_hz": 50,
  "long_press_ms_default": 500,
  "long_press_overrides": {},
  "scroll_step_scale": 1.0,
  "scroll_burst_window_ms": 120,
  "filter_mouse_devices": false,
  "filter_scrolling": false,
  "deny_names": [
    "Power Button",
    "Sleep Button",
    "Video Bus",
    "Lid Switch",
    "PC Speaker",
    "HDA Intel HDMI/DP",
    "gpio-keys"
  ],
  "selected_devices": [],
  "keymap_override": {}
}
```

## Support

For issues, feature requests, or contributions:

- GitHub: https://github.com/Qutaiba-Khader/qut-haos-addons
- Issues: https://github.com/Qutaiba-Khader/qut-haos-addons/issues

## License

MIT License - See [LICENSE](../../LICENSE) for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
