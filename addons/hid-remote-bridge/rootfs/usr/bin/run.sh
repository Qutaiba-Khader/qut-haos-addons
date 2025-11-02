#!/usr/bin/with-contenv bashio
# ==============================================================================
# HID Remote Bridge - Start Script
# ==============================================================================

bashio::log.info "Starting HID Remote Bridge..."

# Ensure /data directory exists
mkdir -p /data

# Check for /dev/input
if [ ! -d "/dev/input" ]; then
    bashio::log.warning "/dev/input not found - no input devices available"
fi

# Export configuration as environment variables (optional, config_manager reads from /data/options.json)
export HID_SEND_EVENTS=$(bashio::config 'send_events')
export HID_SEND_MQTT=$(bashio::config 'send_mqtt')

if bashio::config.true 'send_mqtt'; then
    export HID_MQTT_HOST=$(bashio::config 'mqtt_host')
    export HID_MQTT_PORT=$(bashio::config 'mqtt_port')
    export HID_MQTT_USER=$(bashio::config 'mqtt_user')
    export HID_MQTT_PASS=$(bashio::config 'mqtt_pass')
    export HID_MQTT_TOPIC=$(bashio::config 'mqtt_topic')
    export HID_MQTT_QOS=$(bashio::config 'mqtt_qos')
    export HID_MQTT_RETAIN=$(bashio::config 'mqtt_retain')
fi

export HID_STARTUP_DELAY=$(bashio::config 'startup_delay_sec')
export HID_IGNORE_KEY_REPEAT=$(bashio::config 'ignore_key_repeat')
export HID_EMIT_RELEASE_EVENTS=$(bashio::config 'emit_release_events')
export HID_DEBOUNCE_MS=$(bashio::config 'debounce_ms')
export HID_RATE_LIMIT_HZ=$(bashio::config 'rate_limit_per_device_hz')
export HID_LONG_PRESS_MS=$(bashio::config 'long_press_ms_default')
export HID_SCROLL_SCALE=$(bashio::config 'scroll_step_scale')
export HID_SCROLL_BURST_MS=$(bashio::config 'scroll_burst_window_ms')
export HID_FILTER_MICE=$(bashio::config 'filter_mouse_devices')
export HID_FILTER_SCROLL=$(bashio::config 'filter_scrolling')

bashio::log.info "Configuration loaded"

# Start the Python application
cd /usr/bin
exec python3 -u app.py
