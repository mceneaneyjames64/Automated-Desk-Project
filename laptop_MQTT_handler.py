def heartbeat_monitor():
    # Subscribe to the heartbeat request topic
    mqtt_client.subscribe("heartbeat/request")

    # Define a callback function for when a message is received
    def on_message(client, userdata, message):
        # Log the received heartbeat request
        print(f"Received heartbeat request: {message.payload.decode()}")

        # Immediately publish a heartbeat response
        client.publish("heartbeat/response", "heartbeat OK")

    # Set the callback function
    mqtt_client.on_message = on_message

    # Loop to keep the script running and listening for incoming messages
    mqtt_client.loop_start()