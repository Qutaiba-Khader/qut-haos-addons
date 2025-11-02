# Add-on Contract Verification

This document confirms that the HID Remote Bridge add-on meets all requirements.

## config.json Requirements

### Permissions
- ✓ `"homeassistant_api": true` (line 12)
- ✓ `"udev": true` (line 17)
- ✓ `"devices": ["/dev/input:/dev/input:ro"]` (line 16)
- ✓ `"ingress": true` (line 13)
- ✓ `"watchdog": "http://[HOST]:8099/api/health"` (line 11)

### Defaults
- ✓ `"send_events": true` (line 20)
- ✓ `"send_mqtt": false` (line 21)

### Schema Ranges
- ✓ `"startup_delay_sec": "int(0,30)"` (line 64)
- ✓ `"debounce_ms": "int(0,200)"` (line 67)
- ✓ `"rate_limit_per_device_hz": "int(5,200)"` (line 68)
- ✓ `"long_press_ms_default": "int(200,2000)"` (line 69)
- ✓ `"scroll_burst_window_ms": "int(50,500)"` (line 72)
- ✓ `"scroll_step_scale": "float(0.1,5.0)"` (line 71)

### Data Types
- ✓ `"long_press_overrides": {}` - dict (line 35)
- ✓ `"keymap_override": {}` - dict (line 52)
- ✓ `"selected_devices": []` - list (line 51)

### Deny Names
- ✓ Includes "ACPI Video" (line 48)
- ✓ Includes "AT Translated Set 2 keyboard" (line 49)

### Security
- ✓ `"mqtt_pass": "password?"` - secret type (line 60)
- ✓ Masked in UI (web_ui.py line 72)

## Dockerfile Requirements

- ✓ curl installed (line 11)
- ✓ HEALTHCHECK defined (lines 28-29)
- ✓ Hits `/api/health` endpoint

## Runtime Logic

### Device Matching (device_scanner.py)
- ✓ uniq-first matching (line 254-255)
- ✓ hash(name+phys) fallback (line 258-260)
- ✓ Never binds to eventX

### Filters
- ✓ Mandatory movement-only filter (line 223-233)

### Event Processing (event_handler.py)
- ✓ Scroll burst merging before scaling (line 240-248)
- ✓ Debounce before rate limit (line 156-158, then 184/226)
- ✓ Event name: `hid_remote_event` (line 335)

### Outputs
- ✓ MQTT payload mirrors internal events
- ✓ mqtt_pass never logged

### UI
- ✓ Red banner for no outputs (web_ui.py line 273, 584-590)

## Status

All requirements from the add-on contract are verified and implemented correctly.
