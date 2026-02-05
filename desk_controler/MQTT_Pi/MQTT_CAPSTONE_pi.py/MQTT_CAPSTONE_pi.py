import paho.mqtt.client as mqtt
import time

BROKER = "192.168.1.138" # replace with broker 
PORT = 1883
TOPIC_SUB = "home/desk/command"
TOPIC_PUB = "pi/status"
USERNAME = "mqtttest"
PASSWORD = "VMIececapstone"

# connected
#async with Client(BROKER, PORT, USERNAME, PASSWORD) as client:
def on_connect(client, userdata, flags, reason, properties):
  print(f"Connected with rc_code {reason}")
  client.subscribe("home/desk/command", 1)
  print("subscribed to topic")
        
# message is received
def on_message(client, userdata, message):
  print(f'Recieved msg topic {message.topic} with payload {message.payload}')


def main(): 
  client = mqtt.Client(
      protocol = mqtt.MQTTv5
  )
  client.on_connect = on_connect
  client.on_message = on_message
  
  client.username_pw_set("mqtttest" , "VMIececapstone")
  client.connect("192.168.1.138") #keep alive every 1 minute (heartbeat)
  client.loop_start()
  
  try:
    while True:
      client.publish(TOPIC_SUB, "Heartbeat")
      print("heartbeat sent")
      time.sleep(5)

  except KeyboardInterrupt:
      print("Disconnecting...")
      client.loop_stop()
      client.disconnect()

  finally:
      client.loop_stop()
      client.disconnect()
    
if __name__ == '__main__':
  main()

      