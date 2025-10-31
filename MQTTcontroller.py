# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()
import network
import time
from umqtt.simple import MQTTClient
import ssl
import secrets
import neopixel
import json
from machine import Pin, ADC

class MQTTDevice:
    def __init__(self):
        self.SSID = secrets.SSID
        self.PASSWORD = secrets.PWD

        #Neopixel intialize
        self.np = neopixel.NeoPixel(Pin(15), 2)

        self.entered_time = 0
        # MQTT settings
        self.MQTT_BROKER = secrets.mqtt_url 
        self.MQTT_PORT = 8883
        self.MQTT_USERNAME = secrets.mqtt_username 
        self.MQTT_PASSWORD = secrets.mqtt_password 
        self.CLIENT_ID = "Controller"
        self.TOPIC_PUB = "/Controller"

        
        self.button = Pin(35, Pin.IN, Pin.PULL_UP)
        #self.button.irq(trigger = Pin.IRQ_RISING, handler = self.button_pressed)
    
    def button_pressed(self, p):
        #how do you add debounce?
        #uncomment the following - try to understand what's happening
        now_time = time.ticks_ms()
        if(now_time - self.entered_time < 200):
            return
        self.entered_time = now_time
            
        self.client.publish(self.TOPIC_PUB, "{\"fan_motor\":[0,100]}")
        print("Button was pressed")
        
    def connect_wifi(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        if not self.wlan.isconnected():
            print("Connecting to WiFi...")
            print(self.SSID, self.PASSWORD)
            self.wlan.connect(self.SSID, self.PASSWORD)
            timeout = 10
            while not self.wlan.isconnected() and timeout > 0:
                time.sleep(1)
                timeout -= 1
            
        if self.wlan.isconnected():
            print("WiFi Connected! IP:", self.wlan.ifconfig()[0])
            return True
        else:
            print("WiFi connection failed!")
            return False

    def publish(self, topic, msg):
        self.client.publish(topic, msg)
        print(f"Published message to topic '{topic}' : '{msg}'")
        
    def subscribe(self, topic):
        self.client.subscribe(topic)
        
    def sub_cb(self, topic, msg):
        json_str = json.loads(msg)
        #self.np[0] = json_str["color"]
        #self.np.write()
        print(f"Received message on topic '{topic.decode()}' : '{msg.decode()}'")

    def mqtt_connect(self):
        try:
            print(self.MQTT_USERNAME)
            self.client = MQTTClient(
                client_id = self.CLIENT_ID,
                server = self.MQTT_BROKER,
                port = self.MQTT_PORT,
                user = self.MQTT_USERNAME,
                password = self.MQTT_PASSWORD,
                ssl = True,  # Enable SSL
                ssl_params = {'server_hostname': self.MQTT_BROKER}  # Important for certificate validation
            )
            self.client.set_callback(self.sub_cb)
            self.client.connect()
            
            print("MQTT Connected successfully!")
            return self.client
        except OSError as e:
            print(f"MQTT Connection failed: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None


mqtt_obj = MQTTDevice()

if mqtt_obj.connect_wifi():
    client = mqtt_obj.mqtt_connect()
    mqtt_obj.subscribe("/Controller")


vrx = ADC(Pin(33)) # Joystick X
vry = ADC(Pin(34)) # Joystick Y
sw = Pin(5, Pin.IN) # Joystick button
fan_on = False
json_data = {"fan": fan_on, "servo": {0}, "base":{0}}

count = 0
while True:
    # Get values from joystick
    x = vrx.read_u16()
    y = vry.read_u16()
    button = sw.value()
    #print(f"x: {x} y: {y} b:{button}")
    
    
    
    if button == 0:
        # debounce
        now_time = time.ticks_ms()
        if(now_time - mqtt_obj.entered_time < 500):
            continue
        mqtt_obj.entered_time = now_time
        
        # update fan state in json
        fan_on = not fan_on
        json_data["fan"] = fan_on
        
    
    # update servo state based on joystick Y position
    if y > 60000:
        json_data["servo"] = 1
    elif y == 0:
        json_data["servo"] = -1
    else:
        json_data["servo"] = 0
        
    # update base state based on joystick Y position
    if x > 60000:
        json_data["base"] = 1
    elif x == 0:
        json_data["base"] = -1
    else:
        json_data["base"] = 0
        
    print(json_data)
        
    if count == 5:
        mqtt_obj.client.publish(mqtt_obj.TOPIC_PUB, json.dumps(json_data))
        count = 0
    time.sleep(.01)
    count += 1
    
    '''
    try:
        client.check_msg()
        time.sleep(.1)
    except Exception as e:
        time.sleep(.1)
        print(f"Checking message failed: {e}")
    '''
    
    