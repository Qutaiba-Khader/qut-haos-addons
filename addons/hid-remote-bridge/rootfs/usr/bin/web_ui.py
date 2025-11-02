#!/usr/bin/env python3
"""
Web UI
Flask-based web interface for device selection and configuration
"""

import os
import logging
from flask import Flask, render_template_string, jsonify, request
from typing import Dict, Any

logger = logging.getLogger(__name__)

class WebUI:
    """Web UI server"""

    def __init__(self, config_manager, device_scanner, event_handler):
        self.config_manager = config_manager
        self.device_scanner = device_scanner
        self.event_handler = event_handler
        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/')
        def index():
            """Main UI page"""
            return render_template_string(HTML_TEMPLATE)

        @self.app.route('/api/devices')
        def get_devices():
            """Get discovered devices"""
            devices = self.device_scanner.get_discovered_devices()
            return jsonify({'devices': devices})

        @self.app.route('/api/devices/rescan', methods=['POST'])
        def rescan_devices():
            """Rescan for devices"""
            self.device_scanner.scan_devices()
            devices = self.device_scanner.get_discovered_devices()
            return jsonify({'devices': devices})

        @self.app.route('/api/devices/select', methods=['POST'])
        def select_device():
            """Select a device"""
            data = request.get_json()
            device_id = data.get('device_id')
            if device_id:
                self.device_scanner.select_device(device_id)
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Missing device_id'}), 400

        @self.app.route('/api/devices/deselect', methods=['POST'])
        def deselect_device():
            """Deselect a device"""
            data = request.get_json()
            device_id = data.get('device_id')
            if device_id:
                self.device_scanner.deselect_device(device_id)
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Missing device_id'}), 400

        @self.app.route('/api/config')
        def get_config():
            """Get current configuration"""
            config = self.config_manager.get_all()
            # Don't send password in plain text
            safe_config = config.copy()
            if 'mqtt_pass' in safe_config:
                safe_config['mqtt_pass'] = '****' if safe_config['mqtt_pass'] else ''
            return jsonify(safe_config)

        @self.app.route('/api/config', methods=['POST'])
        def update_config():
            """Update configuration"""
            try:
                data = request.get_json()
                self.config_manager.update(data)
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 400

        @self.app.route('/api/health')
        def health():
            """Health check endpoint"""
            return jsonify({'status': 'ok'})

    def start(self):
        """Start web UI server"""
        try:
            # Disable Flask logging to avoid clutter
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)

            self.app.run(host='0.0.0.0', port=8099, debug=False)
        except Exception as e:
            logger.error(f"Failed to start web UI: {e}")

# HTML Template for the Web UI
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HID Remote Bridge</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            color: #333;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 {
            font-size: 28px;
            margin-bottom: 10px;
            color: #03a9f4;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #ddd;
            flex-wrap: wrap;
        }
        .tab {
            padding: 12px 24px;
            background: #fff;
            border: none;
            cursor: pointer;
            font-size: 14px;
            border-radius: 5px 5px 0 0;
            transition: all 0.2s;
        }
        .tab:hover { background: #f0f0f0; }
        .tab.active {
            background: #03a9f4;
            color: white;
            font-weight: 600;
        }
        .tab-content {
            display: none;
            background: white;
            padding: 30px;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .tab-content.active { display: block; }

        .warning-banner {
            background: #ff5252;
            color: white;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: none;
        }
        .warning-banner.show { display: block; }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #f5f5f5;
            font-weight: 600;
            color: #555;
        }
        tr:hover { background: #f9f9f9; }

        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-usb { background: #4caf50; color: white; }
        .badge-bluetooth { background: #2196f3; color: white; }
        .badge-keys { background: #ff9800; color: white; }
        .badge-scroll { background: #9c27b0; color: white; }

        input[type="checkbox"] {
            width: 20px;
            height: 20px;
            cursor: pointer;
        }

        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #555;
        }
        input[type="text"], input[type="number"], input[type="password"], select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        input[type="text"]:focus, input[type="number"]:focus, input[type="password"]:focus {
            outline: none;
            border-color: #03a9f4;
        }

        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.2s;
        }
        .btn-primary {
            background: #03a9f4;
            color: white;
        }
        .btn-primary:hover { background: #0288d1; }
        .btn-secondary {
            background: #757575;
            color: white;
        }
        .btn-secondary:hover { background: #616161; }

        .toggle {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .toggle input[type="checkbox"] {
            width: auto;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }

        .help-text {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 HID Remote Bridge</h1>
        <p class="subtitle">Monitor USB and Bluetooth HID devices</p>

        <div class="warning-banner" id="warningBanner">
            ⚠️ No outputs enabled! Events will not be sent anywhere. Enable either 'send_events' or 'send_mqtt' in the Outputs tab.
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab('devices')">Devices</button>
            <button class="tab" onclick="showTab('outputs')">Outputs</button>
            <button class="tab" onclick="showTab('behavior')">Behavior</button>
            <button class="tab" onclick="showTab('scrolling')">Scrolling</button>
            <button class="tab" onclick="showTab('filters')">Filters</button>
            <button class="tab" onclick="showTab('advanced')">Advanced</button>
        </div>

        <!-- Devices Tab -->
        <div class="tab-content active" id="devices">
            <h2>Discovered Devices</h2>
            <p class="help-text">Select devices to monitor. Selections are persisted across reboots.</p>
            <button class="btn btn-primary" onclick="rescanDevices()" style="margin-top: 10px;">🔄 Rescan Devices</button>
            <table id="devicesTable">
                <thead>
                    <tr>
                        <th>Monitor</th>
                        <th>Device Name</th>
                        <th>Source</th>
                        <th>Capabilities</th>
                        <th>Unique ID</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>

        <!-- Outputs Tab -->
        <div class="tab-content" id="outputs">
            <h2>Output Configuration</h2>
            <div class="form-group">
                <div class="toggle">
                    <input type="checkbox" id="send_events" onchange="saveConfig()">
                    <label for="send_events">Send events to Home Assistant</label>
                </div>
                <p class="help-text">Emit events as 'hid_remote_event' in Home Assistant (default: enabled)</p>
            </div>
            <div class="form-group">
                <div class="toggle">
                    <input type="checkbox" id="send_mqtt" onchange="saveConfig()">
                    <label for="send_mqtt">Send events to MQTT</label>
                </div>
                <p class="help-text">Mirror events to MQTT broker (default: disabled)</p>
            </div>
            <div id="mqttSettings" style="display:none; margin-top: 20px; padding: 20px; background: #f9f9f9; border-radius: 5px;">
                <h3>MQTT Settings</h3>
                <div class="grid">
                    <div class="form-group">
                        <label>MQTT Host</label>
                        <input type="text" id="mqtt_host" onchange="saveConfig()">
                    </div>
                    <div class="form-group">
                        <label>MQTT Port</label>
                        <input type="number" id="mqtt_port" onchange="saveConfig()">
                    </div>
                    <div class="form-group">
                        <label>MQTT Username</label>
                        <input type="text" id="mqtt_user" onchange="saveConfig()">
                    </div>
                    <div class="form-group">
                        <label>MQTT Password</label>
                        <input type="password" id="mqtt_pass" onchange="saveConfig()">
                    </div>
                    <div class="form-group">
                        <label>MQTT Topic</label>
                        <input type="text" id="mqtt_topic" onchange="saveConfig()">
                    </div>
                    <div class="form-group">
                        <label>QoS</label>
                        <select id="mqtt_qos" onchange="saveConfig()">
                            <option value="0">0 - At most once</option>
                            <option value="1">1 - At least once</option>
                            <option value="2">2 - Exactly once</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <div class="toggle">
                        <input type="checkbox" id="mqtt_retain" onchange="saveConfig()">
                        <label for="mqtt_retain">Retain messages</label>
                    </div>
                </div>
            </div>
        </div>

        <!-- Behavior Tab -->
        <div class="tab-content" id="behavior">
            <h2>Behavior Settings</h2>
            <div class="grid">
                <div class="form-group">
                    <label>Startup Delay (seconds)</label>
                    <input type="number" id="startup_delay_sec" min="0" max="30" onchange="saveConfig()">
                    <p class="help-text">Wait before scanning devices (0-30)</p>
                </div>
                <div class="form-group">
                    <label>Debounce (ms)</label>
                    <input type="number" id="debounce_ms" min="0" max="200" onchange="saveConfig()">
                    <p class="help-text">Delay after each event (0-200)</p>
                </div>
                <div class="form-group">
                    <label>Rate Limit (Hz)</label>
                    <input type="number" id="rate_limit_per_device_hz" min="5" max="200" onchange="saveConfig()">
                    <p class="help-text">Max events per second per device (5-200)</p>
                </div>
                <div class="form-group">
                    <label>Long Press Threshold (ms)</label>
                    <input type="number" id="long_press_ms_default" min="200" max="2000" onchange="saveConfig()">
                    <p class="help-text">Minimum duration for long press (200-2000)</p>
                </div>
            </div>
            <div class="form-group">
                <div class="toggle">
                    <input type="checkbox" id="ignore_key_repeat" onchange="saveConfig()">
                    <label for="ignore_key_repeat">Ignore key repeat events</label>
                </div>
            </div>
            <div class="form-group">
                <div class="toggle">
                    <input type="checkbox" id="emit_release_events" onchange="saveConfig()">
                    <label for="emit_release_events">Emit key release events</label>
                </div>
            </div>
        </div>

        <!-- Scrolling Tab -->
        <div class="tab-content" id="scrolling">
            <h2>Scrolling Settings</h2>
            <div class="grid">
                <div class="form-group">
                    <label>Scroll Step Scale</label>
                    <input type="number" id="scroll_step_scale" step="0.1" min="0.1" max="5" onchange="saveConfig()">
                    <p class="help-text">Multiply scroll values after merging (0.1-5.0)</p>
                </div>
                <div class="form-group">
                    <label>Scroll Burst Window (ms)</label>
                    <input type="number" id="scroll_burst_window_ms" min="50" max="500" onchange="saveConfig()">
                    <p class="help-text">Merge rapid scroll events within this window (50-500)</p>
                </div>
            </div>
            <div class="form-group">
                <div class="toggle">
                    <input type="checkbox" id="filter_scrolling" onchange="saveConfig()">
                    <label for="filter_scrolling">Filter all scroll events</label>
                </div>
                <p class="help-text">Suppress all scroll events if enabled</p>
            </div>
        </div>

        <!-- Filters Tab -->
        <div class="tab-content" id="filters">
            <h2>Device Filters</h2>
            <div class="form-group">
                <div class="toggle">
                    <input type="checkbox" id="filter_mouse_devices" onchange="saveConfig()">
                    <label for="filter_mouse_devices">Filter mouse devices</label>
                </div>
                <p class="help-text">Hide all devices classified as mice from discovery</p>
            </div>
            <div class="form-group">
                <label>Deny List (one per line)</label>
                <textarea id="deny_names" rows="8" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-family: monospace;" onchange="saveConfig()"></textarea>
                <p class="help-text">Device names that are always ignored</p>
            </div>
        </div>

        <!-- Advanced Tab -->
        <div class="tab-content" id="advanced">
            <h2>Advanced Settings</h2>
            <div class="form-group">
                <label>Key Remapping (JSON)</label>
                <textarea id="keymap_override" rows="10" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-family: monospace;" onchange="saveConfig()"></textarea>
                <p class="help-text">Map key names to custom values (e.g., {"KEY_VOLUMEUP": "KEY_CUSTOM"})</p>
            </div>
        </div>
    </div>

    <script>
        let config = {};

        // Load initial data
        async function loadData() {
            await loadConfig();
            await loadDevices();
            checkOutputWarning();
        }

        async function loadConfig() {
            const response = await fetch('/api/config');
            config = await response.json();

            // Update form fields
            document.getElementById('send_events').checked = config.send_events || false;
            document.getElementById('send_mqtt').checked = config.send_mqtt || false;
            document.getElementById('mqtt_host').value = config.mqtt_host || '';
            document.getElementById('mqtt_port').value = config.mqtt_port || 1883;
            document.getElementById('mqtt_user').value = config.mqtt_user || '';
            document.getElementById('mqtt_pass').value = config.mqtt_pass || '';
            document.getElementById('mqtt_topic').value = config.mqtt_topic || '';
            document.getElementById('mqtt_qos').value = config.mqtt_qos || 1;
            document.getElementById('mqtt_retain').checked = config.mqtt_retain || false;
            document.getElementById('startup_delay_sec').value = config.startup_delay_sec || 5;
            document.getElementById('ignore_key_repeat').checked = config.ignore_key_repeat !== false;
            document.getElementById('emit_release_events').checked = config.emit_release_events !== false;
            document.getElementById('debounce_ms').value = config.debounce_ms || 30;
            document.getElementById('rate_limit_per_device_hz').value = config.rate_limit_per_device_hz || 50;
            document.getElementById('long_press_ms_default').value = config.long_press_ms_default || 500;
            document.getElementById('scroll_step_scale').value = config.scroll_step_scale || 1.0;
            document.getElementById('scroll_burst_window_ms').value = config.scroll_burst_window_ms || 120;
            document.getElementById('filter_mouse_devices').checked = config.filter_mouse_devices || false;
            document.getElementById('filter_scrolling').checked = config.filter_scrolling || false;
            document.getElementById('deny_names').value = (config.deny_names || []).join('\\n');
            document.getElementById('keymap_override').value = JSON.stringify(config.keymap_override || {}, null, 2);

            toggleMqttSettings();
        }

        async function loadDevices() {
            const response = await fetch('/api/devices');
            const data = await response.json();

            const tbody = document.querySelector('#devicesTable tbody');
            tbody.innerHTML = '';

            if (data.devices.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#999;">No devices found. Click "Rescan Devices" to search again.</td></tr>';
                return;
            }

            data.devices.forEach(device => {
                const row = document.createElement('tr');

                const capabilities = [];
                if (device.has_keys) capabilities.push('<span class="badge badge-keys">KEYS</span>');
                if (device.has_scroll) capabilities.push('<span class="badge badge-scroll">SCROLL</span>');

                row.innerHTML = `
                    <td><input type="checkbox" ${device.selected ? 'checked' : ''} onchange="toggleDevice('${device.device_id}', this.checked)"></td>
                    <td>${device.name}</td>
                    <td><span class="badge badge-${device.source}">${device.source.toUpperCase()}</span></td>
                    <td>${capabilities.join(' ')}</td>
                    <td style="font-family: monospace; font-size: 11px;">${device.uniq || device.device_id}</td>
                `;
                tbody.appendChild(row);
            });
        }

        async function rescanDevices() {
            await fetch('/api/devices/rescan', { method: 'POST' });
            await loadDevices();
        }

        async function toggleDevice(deviceId, selected) {
            const endpoint = selected ? '/api/devices/select' : '/api/devices/deselect';
            await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device_id: deviceId })
            });
        }

        async function saveConfig() {
            const updates = {
                send_events: document.getElementById('send_events').checked,
                send_mqtt: document.getElementById('send_mqtt').checked,
                mqtt_host: document.getElementById('mqtt_host').value,
                mqtt_port: parseInt(document.getElementById('mqtt_port').value),
                mqtt_user: document.getElementById('mqtt_user').value,
                mqtt_pass: document.getElementById('mqtt_pass').value,
                mqtt_topic: document.getElementById('mqtt_topic').value,
                mqtt_qos: parseInt(document.getElementById('mqtt_qos').value),
                mqtt_retain: document.getElementById('mqtt_retain').checked,
                startup_delay_sec: parseInt(document.getElementById('startup_delay_sec').value),
                ignore_key_repeat: document.getElementById('ignore_key_repeat').checked,
                emit_release_events: document.getElementById('emit_release_events').checked,
                debounce_ms: parseInt(document.getElementById('debounce_ms').value),
                rate_limit_per_device_hz: parseInt(document.getElementById('rate_limit_per_device_hz').value),
                long_press_ms_default: parseInt(document.getElementById('long_press_ms_default').value),
                scroll_step_scale: parseFloat(document.getElementById('scroll_step_scale').value),
                scroll_burst_window_ms: parseInt(document.getElementById('scroll_burst_window_ms').value),
                filter_mouse_devices: document.getElementById('filter_mouse_devices').checked,
                filter_scrolling: document.getElementById('filter_scrolling').checked,
                deny_names: document.getElementById('deny_names').value.split('\\n').filter(x => x.trim()),
            };

            try {
                updates.keymap_override = JSON.parse(document.getElementById('keymap_override').value);
            } catch (e) {
                alert('Invalid JSON in keymap_override');
                return;
            }

            await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updates)
            });

            config = { ...config, ...updates };
            toggleMqttSettings();
            checkOutputWarning();
        }

        function toggleMqttSettings() {
            const mqttSettings = document.getElementById('mqttSettings');
            mqttSettings.style.display = document.getElementById('send_mqtt').checked ? 'block' : 'none';
        }

        function checkOutputWarning() {
            const banner = document.getElementById('warningBanner');
            const send_events = document.getElementById('send_events').checked;
            const send_mqtt = document.getElementById('send_mqtt').checked;

            if (!send_events && !send_mqtt) {
                banner.classList.add('show');
            } else {
                banner.classList.remove('show');
            }
        }

        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

            // Show selected tab
            event.target.classList.add('active');
            document.getElementById(tabName).classList.add('active');
        }

        // Initialize
        loadData();
        setInterval(loadDevices, 30000); // Refresh devices every 30s for hotplug
    </script>
</body>
</html>
'''
