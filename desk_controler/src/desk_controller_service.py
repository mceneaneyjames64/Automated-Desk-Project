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
        self.mqtt_keepalive_thread = None
    
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
            self.controller.publish_status("service_running")
            
            print("\n[Service] Status: RUNNING")
            print("[Service] Listening for MQTT commands...")
            print("[Service] Publishing heartbeat every 60 seconds\n")
            
            # Start heartbeat thread
            self.heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                daemon=True,
                name="heartbeat-thread"
            )
            self.heartbeat_thread.start()
            
            # Start MQTT keepalive thread to prevent disconnects
            self.mqtt_keepalive_thread = threading.Thread(
                target=self._mqtt_keepalive_loop,
                daemon=True,
                name="mqtt-keepalive-thread"
            )
            self.mqtt_keepalive_thread.start()
            
            # Keep service running
            self._keep_alive()
            
            return True
        
        except Exception as e:
            print(f"✗ Service start failed: {e}")
            if self.controller:
                self.controller.logger.error(f"Service start failed: {e}")
            return False
    
    def _heartbeat_loop(self):
        """Run periodic heartbeat and status updates."""
        while self.running:
            try:
                # Publish heartbeat and position feedback
                if self.controller.mqtt_connected:
                    self.controller.publish_status("service_running")
                    self.controller.publish_all_position_feedback()
                    self.controller.logger.debug("Heartbeat published")
                
                time.sleep(60)
            
            except Exception as e:
                self.controller.logger.error(f"Error in heartbeat: {e}")
                time.sleep(10)
    
    def _mqtt_keepalive_loop(self):
        """Monitor MQTT connection and reconnect if necessary.
        
        This loop also ensures the MQTT network loop stays active by
        occasionally checking the connection status. If the MQTT client
        becomes disconnected, it will attempt to reconnect.
        """
        reconnect_delay = 5  # Start with 5 second delay
        max_reconnect_delay = 60  # Max 60 seconds
        
        while self.running:
            try:
                # Check if MQTT is still connected
                if not self.controller.mqtt_connected:
                    self.controller.logger.warning(
                        f"MQTT disconnected. Attempting reconnect (delay={reconnect_delay}s)..."
                    )
                    time.sleep(reconnect_delay)
                    
                    # Try to reconnect
                    if self.controller.mqtt_connect():
                        self.controller.logger.info("✓ MQTT reconnected")
                        reconnect_delay = 5  # Reset delay on successful reconnect
                    else:
                        self.controller.logger.warning("MQTT reconnect failed")
                        # Exponential backoff (5s, 10s, 20s, ..., max 60s)
                        reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                else:
                    # Connected - reset reconnect delay and do normal keepalive check
                    reconnect_delay = 5
                    
                    # Keep the MQTT loop active by checking it periodically
                    # (This helps prevent the broker from timing out the connection)
                    if self.controller.mqtt_client is not None:
                        # The loop_start() call in mqtt_connect() handles the network loop
                        # This is just a sanity check that the thread is still alive
                        pass
                
                time.sleep(10)  # Check connection status every 10 seconds
            
            except Exception as e:
                self.controller.logger.error(f"Error in MQTT keepalive: {e}")
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
        
        self.controller.publish_status("service_stopped")
        self.running = False
        
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        
        if self.mqtt_keepalive_thread:
            self.mqtt_keepalive_thread.join(timeout=5)
        
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
