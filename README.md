# Qutaiba's Home Assistant Add-ons

This repository contains custom Home Assistant add-ons.

## Installation

To add this repository to your Home Assistant instance:

1. Navigate to **Settings** → **Add-ons** → **Add-on Store**
2. Click the **⋮** (three dots) menu in the top right
3. Select **Repositories**
4. Add this repository URL:
   ```
   https://github.com/Qutaiba-Khader/qut-haos-addons
   ```
5. Click **Add**
6. Refresh the Add-on Store page

The add-ons from this repository will now appear in your Add-on Store.

## Available Add-ons

### HID Remote Bridge

Monitor USB and Bluetooth HID devices (keyboards, remotes, controllers) and emit their events to Home Assistant.

**Features:**
- Device discovery with checkbox selection UI
- Supports USB and Bluetooth HID devices
- Captures keyboard events (KeyDown, KeyUp, KeyRepeat)
- Captures scroll events (vertical and horizontal)
- Configurable event filtering and rate limiting
- Long-press detection
- Hotplug support
- Optional MQTT output
- Persistent device selections across reboots

[Read more →](addons/hid-remote-bridge/README.md)

## Support

For issues or feature requests, please use the [GitHub issue tracker](https://github.com/Qutaiba-Khader/qut-haos-addons/issues).

## License

MIT License - see [LICENSE](LICENSE) file for details.
