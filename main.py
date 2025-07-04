# (C) Copyright Peter Hinch 2017-2019.
# Released under the MIT licence.

# Example of a DHT22 sensor with MQTT.
# The DHT22 is connected to GPIO13.
# The LED of the device is toggled by a message on the topic <device_id>/LED.
# The device publishes its temperature and humidity every 60 seconds.
# Returns a JSON object with the following structure:
# {
#   "temperatura": <float>,
#   "humedad": <float>
# }
# Another JSON object is returned when the LED is toggled:
# {
#   "estado": <int>
# }

# red LED: ON == WiFi fail

from mqtt_as import MQTTClient
from mqtt_local import config
import uasyncio as asyncio
import dht, machine
from machine import Pin 
import ujson

# Get a device id
id = ""
for b in machine.unique_id():
	id += "{:02X}".format(b)

print("La id del dispositivo es: " + id)

# Set input of sensor
d = dht.DHT22(Pin(14))

# Set LED pin as output
l = Pin("LED", Pin.OUT)

def sub_cb(topic, msg, retained):
    print('Topic = {} -> Valor = {}'.format(topic.decode(), msg.decode()))

    topic_d = topic.decode()

    # Check if the topic is for toggling the LED
    if topic_d == f"{id}/LED":
            asyncio.create_task(active_led(msg.decode()))

# Function to toggle the LED and publish its state
# This function is called when a message is received on the LED topic
async def active_led(a):
    l.toggle()  # Toggle the LED state
    print("LED toggled")
    data_json = ujson.dumps({"estado": l.value()})
    await client.publish(str(id)+"/estado", data_json, qos = 1) 

# Function to periodically read the DHT22 sensor and publish data
async def periodic_run():
    temperatura = 0
    humedad = 0
    try:
        d.measure() # Hace la lectura del sensor
        
        try:
            temperatura = d.temperature()
        except OSError as e:
            print("Sin sensor temperatura")
        try:
            humedad=d.humidity()
        except OSError as e:
            print("Sin sensor humedad")
            
        print("Por crear el .json")

        # Create json data 
        #data_json_m = ujson.dumps({"temperatura": temperatura, "humedad": humedad})
        data_json_m = ujson.dumps({"temperatura": humedad, "humedad": temperatura})
            
        print("Se creó el .json")

        # Publish data in a broker
        await client.publish(id, data_json_m, qos = 1) 

        print("Datos publicados")

    except OSError as e:
            print("Sin sensor")

    await asyncio.sleep(60)  # wait 60 seconds before next run

async def wifi_han(state):
    print('Wifi is ', 'up' if state else 'down')
    await asyncio.sleep(1)

# If you connect with clean_session True, must re-subscribe (MQTT spec 3.1.2.4)
async def conn_han(client):
    await client.subscribe(id + '/LED', 1)

async def main(client):
    await client.connect()
    print("Conectado al broker MQTT")

    await asyncio.sleep(2)  # Give broker time

    # Publish initial LED state
    l.value(0)  # Ensure LED is off initially
    data_json = ujson.dumps({"estado": l.value()})
    await client.publish(str(id)+"/estado", data_json, qos = 1) 

    periodic_task = asyncio.create_task(periodic_run())
    while True:
        if periodic_task.done():
            periodic_task = asyncio.create_task(periodic_run())
        
        await asyncio.sleep_ms(10)

# Define configuration
config['subs_cb'] = sub_cb
config['connect_coro'] = conn_han
config['wifi_coro'] = wifi_han
config['ssl'] = True

# Set up client
MQTTClient.DEBUG = True  # Optional
client = MQTTClient(config)
try:
    asyncio.run(main(client))
finally:
    client.close()
    asyncio.new_event_loop()