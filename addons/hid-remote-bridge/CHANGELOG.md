# Changelog

All notable changes to the HID Remote Bridge add-on will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-15

### Added
- Initial release of HID Remote Bridge add-on
- Device discovery from /dev/input/eventX
- Web UI for device selection and configuration
- Support for USB and Bluetooth HID devices
- Event capture for keyboard events (KeyDown, KeyUp, KeyRepeat)
- Event capture for scroll events (vertical and horizontal wheels)
- Emit events to Home Assistant as `hid_remote_event`
- Optional MQTT output
- Smart device filtering:
  - Auto-exclude system devices (power button, lid switch, etc.)
  - Mandatory movement filter (excludes pure pointer devices)
  - Optional mouse device filter
- Persistent device selections across reboots
- Device matching by unique ID (Bluetooth MAC) or name+phys hash
- Hotplug support (detect devices during runtime)
- Configurable event processing:
  - Debouncing
  - Rate limiting per device
  - Key repeat filtering
  - Key release event control
- Long press detection with configurable thresholds
- Per-device long press overrides
- Scroll event processing:
  - Scroll step scaling
  - Scroll burst merging
  - Optional scroll filtering
- Key remapping via keymap override
- Multi-architecture support (aarch64, amd64, armhf, armv7, i386)
- AppArmor security enabled
- Watchdog support
- Health check endpoint
- Web UI tabs:
  - Devices (discovery and selection)
  - Outputs (HA events and MQTT configuration)
  - Behavior (debounce, rate limit, long press)
  - Scrolling (scale, burst window, filtering)
  - Filters (mouse filter, deny list)
  - Advanced (keymap override)
- Comprehensive documentation and examples
- Troubleshooting guide

### Security
- Read-only access to /dev/input
- AppArmor enabled
- Network disabled by default (only enabled when MQTT is configured)
- MQTT password never logged
- Configuration validation with range constraints

[0.1.0]: https://github.com/Qutaiba-Khader/qut-haos-addons/releases/tag/v0.1.0
