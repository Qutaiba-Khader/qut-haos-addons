#!/usr/bin/env python3
"""
HID Remote Bridge - Main Application
Monitors HID devices and emits events to Home Assistant and/or MQTT
"""

import os
import sys
import time
import json
import logging
import threading
import signal
from pathlib import Path
from typing import Dict, Any

# Local imports
from config_manager import ConfigManager
from device_scanner import DeviceScanner
from event_handler import EventHandler
from web_ui import WebUI

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class HIDRemoteBridge:
    """Main application class"""

    def __init__(self):
        self.running = False
        self.config_manager = ConfigManager()
        self.device_scanner = DeviceScanner(self.config_manager)
        self.event_handler = EventHandler(self.config_manager)
        self.web_ui = WebUI(self.config_manager, self.device_scanner, self.event_handler)

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()

    def start(self):
        """Start the application"""
        logger.info("Starting HID Remote Bridge v0.1.0")

        # Load configuration
        config = self.config_manager.load_config()
        logger.info("Configuration loaded successfully")

        # Validate outputs
        if not config['send_events'] and not config['send_mqtt']:
            logger.warning("⚠️  WARNING: No outputs enabled! Events will not be sent anywhere.")
            logger.warning("⚠️  Enable either 'send_events' or 'send_mqtt' in the configuration.")

        # Start web UI in a separate thread
        ui_thread = threading.Thread(target=self.web_ui.start, daemon=True)
        ui_thread.start()
        logger.info("Web UI started on port 8099")

        # Startup delay
        startup_delay = config.get('startup_delay_sec', 5)
        if startup_delay > 0:
            logger.info(f"Waiting {startup_delay}s before scanning devices...")
            time.sleep(startup_delay)

        # Initial device scan
        logger.info("Scanning for HID devices...")
        self.device_scanner.scan_devices()

        # Start monitoring selected devices
        self.running = True
        self.event_handler.start_monitoring(self.device_scanner.get_selected_devices())

        # Main loop - handle hotplug events
        logger.info("Application running. Press Ctrl+C to stop.")
        try:
            while self.running:
                time.sleep(10)
                # Periodic rescan for hotplug
                self.device_scanner.scan_devices()
                self.event_handler.update_devices(self.device_scanner.get_selected_devices())
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.stop()

    def stop(self):
        """Stop the application"""
        logger.info("Stopping HID Remote Bridge...")
        self.running = False
        self.event_handler.stop()
        logger.info("Shutdown complete")
        sys.exit(0)

def main():
    """Entry point"""
    try:
        app = HIDRemoteBridge()
        app.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
