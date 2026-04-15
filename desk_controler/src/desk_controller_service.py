#!/usr/bin/env python3
"""
Background service version of desk controller.
Runs without user interaction, responding to MQTT commands only.

This replaces the old run_test() approach with an automated service.
"""

import sys
import time
import signal
import threading
import config
from desk_controller_wrapper import DeskControllerWrapper


class DeskControllerService:
    """Service wrapper for background operation."""
    
    def __init__(self):
        """Initialize the service."""
        self.controller = None
        self.running = False
        self.heartbeat_thread = None
    
    def start(self) -> bool:
        """
        Start the service.
        
        Returns
        -------
        bool
            True if successful
        """
        print("="*70)
        print("  DESK CONTROLLER SERVICE")
        print("="*70)
        
        try:
            # Create controller
            self.controller = DeskControllerWrapper(
                broker=config.MQTT_BROKER,
                mqtt_port=config.MQTT_PORT,
                mqtt_username=config.MQTT_USERNAME,
                mqtt_password=config.MQTT_PASSWORD,
                presets_file="desk_presets.json",
                log_file="/var/log/desk_controller.log"
            )
            
            # Initialize hardware
            print("\n[Service] Initializing hardware...")
            if not self.controller.initialize_hardware():
                print("✗ Hardware initialization failed")
                return False
            print("✓ Hardware initialized")
            
            # Load presets
            print("[Service] Loading presets...")
            self.controller.load_presets_from_file()
            print("✓ Presets loaded")
            
            # Connect to MQTT
            print("[Service] Connecting to MQTT broker...")
            if not self.controller.mqtt_connect():
                print("⚠ MQTT connection failed - will retry periodically")
            else:
                print("✓ MQTT connected")
            
            self.running = True
            print("\n[Service] Status: RUNNING")
            print("[Service] Listening for MQTT commands...")
            print("[Service] Publishing heartbeat every 60 seconds\n")
            
            # Start heartbeat thread
            self.heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                daemon=True
            )
            self.heartbeat_thread.start()
            
            # Keep service running
            self._keep_alive()
            
            return True
        
        except Exception as e:
            print(f"✗ Service start failed: {e}")
            self.controller.logger.error(f"Service start failed: {e}")
            return False
    
    def _heartbeat_loop(self):
        """Run periodic heartbeat and status updates."""
        while self.running:
            try:
                # Publish heartbeat
                if self.controller.mqtt_connected:
                    self.controller.publish_status("service_running")
                    self.controller.publish_all_position_feedback()
                    self.controller.logger.debug("Heartbeat published")
                
                time.sleep(60)
            
            except Exception as e:
                self.controller.logger.error(f"Error in heartbeat: {e}")
                time.sleep(10)
    
    def _keep_alive(self):
        """Keep service alive until shutdown requested."""
        while self.running:
            try:
                time.sleep(5)
            except KeyboardInterrupt:
                break
    
    def stop(self):
        """Stop the service gracefully."""
        print("\n[Service] Stopping...")
        self.running = False
        
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        
        if self.controller:
            self.controller.shutdown()
        
        print("[Service] Stopped")


def main():
    """Main service entry point."""
    service = DeskControllerService()
    
    def signal_handler(signum, frame):
        """Handle signals."""
        print("\n[Service] Signal received")
        service.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if service.start():
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
