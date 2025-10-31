import network
import time
from umqtt.simple import MQTTClient
import ssl
import secrets
import neopixel
import json
from machine import Pin, PWM
#import encoder


class Motor():
    def __init__(self,m1,m2):
        self.M1 = PWM(m1, freq=100, duty_u16=0)
        self.M2 = PWM(m2, freq=100, duty_u16=0)
        self.stop()          
            
    def stop(self):
        self.M1.duty_u16(0) 
        self.M2.duty_u16(0) 

    def start(self, direction = 0, speed = 99):
        print("starting")
        if direction:
            self.M1.duty_u16(int(speed*65535/100)) 
            self.M2.duty_u16(0)
        else:
            self.M1.duty_u16(0)
            self.M2.duty_u16(int(speed*65535/100)) 

def servo_angle(angle,servo):
    if angle > 180:
        angle = 180
    elif angle < 0:
        angle = 1
    min_duty = 34
    max_duty = 90
    duty = min_duty + (max_duty-min_duty) * (angle / 180)
    servo.duty(int(duty))

class MQTTDevice:
    def __init__(self):
        self.SSID = secrets.SSID
        self.PASSWORD = secrets.PWD
        
        #Fan motor initialize
        self.fan = Motor(14,27)
        self.fan.start(0,99)
        time.sleep(2)
        self.fan.stop()
        
        #Base motor initalize
        self.base = Motor(12,13)
        self.base.stop()
        
        #Servo initialize
        self.servo = PWM(Pin(4))
        self.servo.freq(40)
        self.current_angle = 10
        servo_angle(self.current_angle, self.servo)

        #Neopixel intialize
        self.np = neopixel.NeoPixel(Pin(15), 2)
        self.np[0] = [0,0,0]
        self.np.write()

        self.entered_time = 0
        # MQTT settings
        self.MQTT_BROKER = secrets.mqtt_url 
        self.MQTT_PORT = 8883
        self.MQTT_USERNAME = secrets.mqtt_username 
        self.MQTT_PASSWORD = secrets.mqtt_password 
        self.CLIENT_ID = "Robot"
        self.TOPIC_PUB = "/P6"

        
        self.button = Pin(35, Pin.IN, Pin.PULL_UP)
        self.button.irq(trigger = Pin.IRQ_RISING, handler = self.button_pressed)
    
    def button_pressed(self, p):
        #how do you add debounce?
        #uncomment the following - try to understand what's happening 
        now_time = time.ticks_ms()
        if(now_time - self.entered_time < 200):
            return
        self.entered_time = now_time
            
        self.client.publish(self.TOPIC_PUB, "{\"color\":[120,0,300]}")
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
        print(f"Received message on topic '{topic.decode()}' : '{msg.decode()}'")

        # update fan state
        if json_str["fan"] == True:
            self.fan.start(1,99)
        else:
            self.fan.stop()
        
        # move servo
        if json_str["servo"] == 1:
            if self.current_angle < 175:
                self.current_angle += 3
                servo_angle(self.current_angle, self.servo)
                print(f" Moving forward to {self.current_angle}")
    
            else:
                print("servo at 180")
            
        elif json_str["servo"] == -1:
            if 5 < self.current_angle:
                self.current_angle -= 3
                servo_angle(self.current_angle, self.servo)
                print(f" Moving back to {self.current_angle}")
    
            else:
                print("servo at 0")
        
        if json_str["base"] == 1:
            print("turning base right")
            self.base.start(0, 20)
            time.sleep(.1)
            self.base.stop()
            
        elif json_str["base"] == -1:
            print("turning base left")
            self.base.start(1, 20)
            time.sleep(.1)
            self.base.stop()
                   

    def mqtt_connect(self):
        try:
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
    

# Initialize Receiver
mqtt_obj = MQTTDevice()

if mqtt_obj.connect_wifi():
    client = mqtt_obj.mqtt_connect()
    mqtt_obj.subscribe("/Controller")


# Continuously check for updates
while True:
    try:
        client.check_msg()
        time.sleep(.05)
    except Exception as e:
        time.sleep(.1)
        print(f"Checking message failed: {e}")
        
    

      
            
          

