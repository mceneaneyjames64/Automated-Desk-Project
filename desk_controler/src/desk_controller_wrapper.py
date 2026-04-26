    def mqtt_connect(self) -> bool:
        """
        Connect to MQTT broker.
        
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        if not MQTT_AVAILABLE:
            self.logger.warning("MQTT not available (paho-mqtt not installed)")
            return False
        
        try:
            # Use VERSION1 (not VERSION2) to support standard callback signatures
            # VERSION2 requires different callback parameters
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
            
            self.mqtt_client.on_connect = self._mqtt_on_connect
            self.mqtt_client.on_message = self._mqtt_on_message
            self.mqtt_client.on_disconnect = self._mqtt_on_disconnect
            
            self.mqtt_client.username_pw_set(
                self.mqtt_config["username"],
                self.mqtt_config["password"]
            )
            
            # Set keepalive to 60 seconds (default is 60, but being explicit)
            self.mqtt_client.connect(
                self.mqtt_config["broker"],
                self.mqtt_config["port"],
                keepalive=60
            )
            
            self.mqtt_client.loop_start()
            self.logger.info(f"✓ MQTT connection initiated to {self.mqtt_config['broker']}")
            return True
        
        except Exception as e:
            self.logger.error(f"MQTT connection failed: {e}")
            return False
    
    def mqtt_disconnect(self) -> bool:
        """
        Disconnect from MQTT broker.
        
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        try:
            if self.mqtt_client is not None:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
                self.mqtt_connected = False
                self.logger.info("✓ MQTT disconnected")
                return True
            return False
        
        except Exception as e:
            self.logger.error(f"Error disconnecting MQTT: {e}")
            return False
    
    def _mqtt_on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback.
        
        Parameters
        ----------
        client : mqtt.Client
            MQTT client instance
        userdata : Any
            User data (if set)
        flags : dict
            Connection flags
        rc : int
            Return code (0 = success)
        """
        if rc == 0:
            with self.mqtt_lock:
                self.mqtt_connected = True
            self.logger.info(f"✓ MQTT connected (return code: {rc})")
            client.subscribe(self.mqtt_config["command_topic"], 1)
        else:
            with self.mqtt_lock:
                self.mqtt_connected = False
            self.logger.error(f"MQTT connection failed (return code: {rc})")
    
    def _mqtt_on_message(self, client, userdata, message):
        """MQTT message callback.

        Routes incoming command payloads to the appropriate handler.  All
        motor-movement commands are dispatched to background worker threads
        (via _start_motor_movement_worker) so that this callback returns
        immediately and does not block the MQTT network loop.

        Routing order (first match wins):
          "Heartbeat"           – publish heartbeat_ok status.
          "Feedback{N}:{v}"    – update cached motor position under position_lock.
          "m{N} -> up|down|…"  – start a motor movement worker.
          "save preset {N}"    – save current sensor readings as preset N.
          "preset {N}"         – execute preset N in a worker thread.
          "preset_{word}"      – execute named preset (one/two/three).
          "set_preset_{word}"  – save named preset.
          "emergency_stop"     – halt all motors immediately.
          "calibrate"          – run calibration in a worker thread.
        """
        try:
            payload = message.payload.decode().strip()
            self.logger.debug(f"MQTT message received: {payload}")
            
            # Handle different command types
            if payload == "Heartbeat":
                self.publish_status("heartbeat_ok")
            
            elif payload.startswith("Feedback"):
                # Position feedback from motor controller
                for motor_id in [1, 2, 3]:
                    if payload.startswith(f"Feedback{motor_id}:"):
                        value_str = payload[len(f"Feedback{motor_id}:"):].strip()
                        try:
                            position = float(value_str)
                            with self.position_lock:
                                self.motor_positions[motor_id] = position
                            self.logger.debug(f"Position updated - M{motor_id}: {position}")
                        except ValueError:
                            pass
                        break
            
            elif " -> " in payload:
                # Motor command: "m{id} -> {direction|position}"
                parts = payload.split("->")
                motor_part = parts[0].strip()
                direction_part = parts[1].strip()
                
                if motor_part.startswith("m"):
                    motor_id = int(motor_part[1:])
                    
                    if direction_part.lower() == "up":
                        target = self._motor_max_target(motor_id)
                        self._start_motor_movement_worker(
                            f"m{motor_id}-up",
                            self.move_motor_to_position,
                            motor_id,
                            target
                        )
                    elif direction_part.lower() == "down":
                        self._start_motor_movement_worker(
                            f"m{motor_id}-down",
                            self.retract_motor_fully,
                            motor_id
                        )
                    elif direction_part.lower() == "stop":
                        self.emergency_stop_all()
                    else:
                        try:
                            target_pos = float(direction_part)
                            self._start_motor_movement_worker(
                                f"m{motor_id}-move",
                                self.move_motor_to_position,
                                motor_id,
                                target_pos
                            )
                        except ValueError:
                            self.logger.warning(f"Could not parse motor target position from: {payload}")
            
            elif payload.startswith("save preset "):
                # Preset save: "save preset 1", "save preset 2", "save preset 3"
                try:
                    preset_id = int(payload.split()[-1])
                    if preset_id in self.presets:
                        self.save_current_position_as_preset(preset_id)
                    else:
                        self.logger.warning(f"Invalid preset ID in message: {payload}")
                except (ValueError, IndexError):
                    self.logger.warning(f"Could not parse preset ID from message: {payload}")

            elif payload.startswith("preset "):
                # Preset load: "preset 1", "preset 2", "preset 3"
                try:
                    preset_id = int(payload.split()[-1])
                    if preset_id in self.presets:
                        self._start_motor_worker(
                            f"preset-{preset_id}",
                            self.load_and_execute_preset,
                            preset_id,
                        )
                    else:
                        self.logger.warning(f"Invalid preset ID in message: {payload}")
                except (ValueError, IndexError):
                    self.logger.warning(f"Could not parse preset ID from message: {payload}")

            elif payload.startswith("preset_") and not payload.endswith("_save"):
                # Preset load: "preset_one", "preset_two", "preset_three"
                preset_names = {"one": 1, "two": 2, "three": 3}
                preset_word = payload.split("_")[1]
                preset_id = preset_names.get(preset_word)
                if preset_id:
                    self._start_motor_worker(
                        f"preset-{preset_id}",
                        self.load_and_execute_preset,
                        preset_id
                    )

            elif payload.startswith("set_preset_"):
                # Preset save: "set_preset_one", "set_preset_two", "set_preset_three"
                preset_names = {"one": 1, "two": 2, "three": 3}
                preset_word = payload.split("_")[-1]
                preset_id = preset_names.get(preset_word)
                if preset_id:
                    self.save_current_position_as_preset(preset_id)
            
            elif payload == "emergency_stop":
                self.emergency_stop_all()

            elif payload == "calibrate":
                self._start_motor_worker(
                    "calibrate",
                    self._run_calibration_worker,
                )
        
        except Exception as e:
            self.logger.error(f"Error processing MQTT message: {e}")
    
    def _mqtt_on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback.
        
        Parameters
        ----------
        client : mqtt.Client
            MQTT client instance
        userdata : Any
            User data (if set)
        rc : int
            Disconnect reason code (0 = normal, non-0 = unexpected)
        """
        with self.mqtt_lock:
            self.mqtt_connected = False
        
        if rc == 0:
            self.logger.info("MQTT disconnected normally")
        else:
            self.logger.warning(f"MQTT disconnected unexpectedly (reason code: {rc})")
