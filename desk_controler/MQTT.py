import paho.mqtt.client as mqtt
import time
import asyncio

BROKER = "192.168.1.138" # replace with broker 
PORT = 1883
TOPIC_SUB = "home/desk/command"
TOPIC_PUB = "pi/status"
USERNAME = "mqtttest"
PASSWORD = "VMIececapstone"

############################################################################
################################ VARIABLES #################################
############################################################################
global currposition1, currposition2, currposition3 
currposition1 = 201
currposition2 = 785
currposition3 = 146

preset1_1 = 110
preset1_2 = 120
preset1_3 = 130

preset2_1 = 210
preset2_2 = 220
preset2_3 = 230

preset3_1 = 310
preset3_2 = 320
preset3_3 = 330

############################################################################
################################ FUNCTIONS #################################
############################################################################
def feedbackpub1(client, userdate, message):
    client.publish(TOPIC_SUB, f"Feedback1{preset1_1}")
    client.publish(TOPIC_SUB, f"Feedback2{preset1_2}")
    client.publish(TOPIC_SUB, f"Feedback3{preset1_3}")
    
def feedbackpub2(client, userdate, message):
    client.publish(TOPIC_SUB, f"Feedback1{preset2_1}")
    client.publish(TOPIC_SUB, f"Feedback2{preset2_2}")
    client.publish(TOPIC_SUB, f"Feedback3{preset2_3}")
    
def feedbackpub3(client, userdate, message):
    client.publish(TOPIC_SUB, f"Feedback1{preset3_1}")
    client.publish(TOPIC_SUB, f"Feedback2{preset3_2}")
    client.publish(TOPIC_SUB, f"Feedback3{preset3_3}")
    
def monitor_up(client, userdata, message):
    ##MOVE MONITOR UP
    client.publish(TOPIC_SUB, "Monitor: up")
    
def monitor_down(client, userdata, message):
    ##MOVE MONITOR DOWN
    client.publish(TOPIC_SUB, "Monitor: down")
    
def keyboard_up(client, userdata, message):
    ##MOVE KEYBOARD UP
    client.publish(TOPIC_SUB, "Keyboard: up")
    
def keyboard_down(client, userdata, message):
    ##MOVE KEYBOARD DOWN
    client.publish(TOPIC_SUB, "Keyboard: down")
    
def tilt_up(client, userdata, message):
    ##TILT UP
    client.publish(TOPIC_SUB, "Tilt: up")
    
def tilt_down(client, userdata, message):
    ##TILT DOWN
    client.publish(TOPIC_SUB, "Tilt: down")
    
#########################PRESET 1#########################
    
def start_actuator_1_1(client, userdata, message):
    #MOVE MONITOR TO PRESET 1
    client.publish(TOPIC_SUB, f"m1 -> {preset1_1}")
    start_actuator_1_2(client, userdata, message)

def start_actuator_1_2(client, userdata, message):
    #MOVE KEYBOARD TO PRESET 1
    client.publish(TOPIC_SUB, f"m2 -> {preset1_2}")
    start_actuator_1_3(client, userdata, message)
        
def start_actuator_1_3(client, userdata, message):
    #TILT MONITOR TO PRESET 1
    client.publish(TOPIC_SUB, f"m3 -> {preset1_3}")
    client.publish(TOPIC_SUB, "Preset1 Movement Complete")
    
#########################PRESET 2#########################
    
def start_actuator_2_1(client, userdata, message):
    #MOVE MONITOR TO PRESET 2
    client.publish(TOPIC_SUB, f"m1 -> {preset2_1}")
    start_actuator_2_2(client, userdata, message)

def start_actuator_2_2(client, userdata, message):
    #MOVE KEYBOARD TO PRESET 2
    client.publish(TOPIC_SUB, f"m2 -> {preset2_2}")
    start_actuator_2_3(client, userdata, message)
        
def start_actuator_2_3(client, userdata, message):
    #TILT MONITOR TO PRESET 2
    client.publish(TOPIC_SUB, f"m3 -> {preset2_3}")
    client.publish(TOPIC_SUB, "Preset2 Movement Complete")
    
#########################PRESET 3#########################
    
def start_actuator_3_1(client, userdata, message):
    #MOVE MONITOR TO PRESET 3
    client.publish(TOPIC_SUB, f"m1 -> {preset3_1}")
    start_actuator_3_2(client, userdata, message)

def start_actuator_3_2(client, userdata, message):
    #MOVE KEYBOARD TO PRESET 3
    client.publish(TOPIC_SUB, f"m2 -> {preset3_2}")
    start_actuator_3_3(client, userdata, message)
        
def start_actuator_3_3(client, userdata, message):
    #TILT MONITOR TO PRESET 3
    client.publish(TOPIC_SUB, f"m3 -> {preset3_3}")
    client.publish(TOPIC_SUB, "Preset3 Movement Complete")
    
#############################################################
#########################SET PRESETS#########################
#############################################################
    
def preset1(client, userdata, message):
    global preset1_1, preset1_2, preset1_3
    
    preset1_1 = currposition1
    preset1_2 = currposition2
    preset1_3 = currposition3
    client.publish(TOPIC_SUB, "preset1 saved")
    feedbackpub1(client, userdata, message)

def preset2(client, userdata, message):
    global preset2_1, preset2_2, preset2_3
    
    preset2_1 = currposition1
    preset2_2 = currposition2
    preset2_3 = currposition3
    client.publish(TOPIC_SUB, "preset2 saved")
    feedbackpub2(client, userdata, message)

def preset3(client, userdata, message):
    global preset3_1, preset3_2, preset3_3
    
    preset3_1 = currposition1
    preset3_2 = currposition2
    preset3_3 = currposition3
    client.publish(TOPIC_SUB, "preset3 saved")
    feedbackpub3(client, userdata, message)

def on_connect(client, userdata, flags, reason, properties):
  print(f"Connected with rc_code {reason}")
  client.subscribe("home/desk/command", 1)
        
# message is received
def on_message(client, userdata, message):
  print(f'Recieved msg topic {message.topic} with payload {message.payload}')
  
############################################################################
############################# READING MESSAGES #############################
############################################################################

  if message.payload.decode() == "Heartbeat":
      return
    
  elif message.payload.decode().startswith("Heartbeat, Preset"):
      return
  
  elif message.payload.decode() == "m1 -> up":
      monitor_up(client, userdata, message)
      
  elif message.payload.decode() == "m1 -> down":
      monitor_down(client, userdata, message)
      
  elif message.payload.decode() == "m2 -> up":
      keyboard_up(client, userdata, message)
      
  elif message.payload.decode() == "m2 -> down":
      keyboard_down(client, userdata, message)
      
  elif message.payload.decode() == "m3 -> up":
      tilt_up(client, userdata, message)

  elif message.payload.decode() == "m3 -> down":
      tilt_down(client, userdata, message)
      
  elif message.payload.decode() == "preset_one":
      start_actuator_1_1(client, userdata, message)
      
  elif message.payload.decode() == "preset_two":
      start_actuator_2_1(client, userdata, message)
      
  elif message.payload.decode() == "preset_three":
      start_actuator_3_1(client, userdata, message)
      
  elif message.payload.decode() == "set_preset_one":
      preset1(client, userdata, message)
      
  elif message.payload.decode() == "set_preset_two":
      preset2(client, userdata, message)
      
  elif message.payload.decode() == "set_preset_three":
      preset3(client, userdata, message)

def main():
  client = mqtt.Client(
      mqtt.CallbackAPIVersion.VERSION2,
      protocol = mqtt.MQTTv5
  )
  client.on_connect = on_connect
  client.on_message = on_message
  
  client.username_pw_set("mqtttest" , "VMIececapstone")
  client.connect("192.168.1.138", 1883)
  client.loop_start()
  
############################################################################
############################ HEARTBEAT/POSITION ############################
############################################################################
      
  try:
    while True:  
      client.publish(TOPIC_SUB, "Heartbeat")
      client.publish(TOPIC_SUB, f"Feedback1{currposition1}")
      client.publish(TOPIC_SUB, f"Feedback2{currposition2}")
      client.publish(TOPIC_SUB, f"Feedback3{currposition3}")
      time.sleep(60)

  except KeyboardInterrupt:
      print("Disconnecting...")
      client.loop_stop()
      client.disconnect()

  finally:
      client.loop_stop()
      client.disconnect()
    
if __name__ == '__main__':
  main()
