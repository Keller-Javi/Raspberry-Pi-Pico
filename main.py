# (C) Copyright Peter Hinch 2017-2019.
# Released under the MIT licence.

# Titulo
# - Publica temperatura, temperatura minima y máxima, histeresis, periodo y porcentaje de luz medido y el valor para activar el foco en JSON
# - Se suscribe a tópicos para cambiar parámetros y destellar LED
# - Almacena parámetros no volátiles (temperatura maxima y mínima, histeresis, periodo y porcentaje de luz para activar el foco) en db.json
# - Destello de LED al recibir el comando "destello" a modo de prueba

# red LED: ON == WiFi fail

import os
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
temperature_sensor = dht.DHT22(Pin(27))
light_sensor = machine.ADC(26)

# Set LED pin as output
l = Pin("LED", Pin.OUT)

# Set relayS pin as output
cooler = Pin(16, Pin.OUT) # Ventilador
heater = Pin(17, Pin.OUT) # Estufa
light = Pin(18, Pin.OUT) # Foco

def save_data(data):
    # Save non volatile parameters in db.json (setpoint, periodo, modo, rele)   
    try:
        with open("db.json", "w") as file:
            ujson.dump(data, file)
            print("Datos guardados de manera correcta")
    except:
        print("Error al guardar los datos")

def load_data():
    # Load parameters from db.json or return {} in case of error
    try:
        with open("db.json", "r") as file:
            data = ujson.load(file)
            return data
    except:
        print("Hubo un error a cargar los datos")
        return {}

try: # Try if a database exist
    os.stat("db.json")
    db = load_data()
except: # Set default values  
    db = load_data()
    db["temp_max"] = 30
    db["temp_min"] = 20
    db["histeresis"] = 2
    db["periodo"] = 60
    db["porcentaje_luz"] = 30
    db["foco"] = 0
    db["estufa"] = 0
    db["ventilador"] = 0
    save_data(db)

def sub_cb(topic, msg, retained):
    global flash_band
    print('Topic = {} -> Valor = {}'.format(topic.decode(), msg.decode()))

    topic_d = topic.decode()

    # The values are load in a database
    if topic_d == f"{id}/temp_max":
        db["temp_max"] = int(msg.decode())
        save_data(db)
    if topic_d == f"{id}/temp_min":
        db["temp_min"] = int(msg.decode())
        save_data(db)
    if topic_d == f"{id}/histeresis":
        db["histeresis"] = int(msg.decode())
        save_data(db)
    if topic_d == f"{id}/periodo":
        db["periodo"] = int(msg.decode())
        save_data(db)
    if topic_d == f"{id}/porcentaje_luz":
        db["porcentaje_luz"] = int(msg.decode())
        save_data(db)
    if topic_d == f"{id}/destello":
        # The "destello" command is not saved, only execute task of flash
        asyncio.create_task(flash_led())

async def flash_led():
    for _ in range(0,30):
        l.toggle()
        await asyncio.sleep_ms(200)

def update_actuators():
    # Update actuators based on the current state in db
    cooler.value(db["ventilador"])
    heater.value(db["estufa"])
    light.value(db["foco"])
    print("Actuadores actualizados: Ventilador={}, Estufa={}, Foco={}".format(db["ventilador"], db["estufa"], db["foco"]))

def actuators_control(temperature, light_percentage):
    if temperature > (db["temp_max"] + db["histeresis"]):
            if db["ventilador"] == 0:
                db["ventilador"] = 1
                save_data(db)
                print("Ventilador encendido")
    elif temperature < (db["temp_min"] - db["histeresis"]):
            if db["ventilador"] == 1:
                db["ventilador"] = 0
                save_data(db)
                print("Ventilador apagado")
        
    if temperature < (db["temp_min"] - db["histeresis"]):
            if db["estufa"] == 0:
                db["estufa"] = 1
                save_data(db)
                print("Estufa encendida")
    elif temperature > (db["temp_max"] + db["histeresis"]):
            if db["estufa"] == 1:
                db["estufa"] = 0
                save_data(db)
                print("Estufa apagada")
    
    if light_percentage < db["porcentaje_luz"]:
            if db["foco"] == 0:
                db["foco"] = 1
                save_data(db)
                print("Foco encendido")
    elif light_percentage >= db["porcentaje_luz"]:
            if db["foco"] == 1:
                db["foco"] = 0
                save_data(db)
                print("Foco apagado")
    
    # Update actuators based on the current state in db
    update_actuators()

async def periodic_run():
    try:
        temperature_sensor.measure()
        temperature = None
        light_percentage = None
        
        try:
            temperature = temperature_sensor.temperature()
        except OSError as e:
            print("Sin sensor temperatura")

        try:
            light_value = light_sensor.read_u16()
            light_percentage = (light_value / 65535) * 100 if light_value is not None else 0
        except OSError as e:
            print("Sin sensor de luz")
            
        print("Por crear el .json")

        # Create json data 
        data_json = ujson.dumps({"temperatura": temperature, "porcentaje_luz": (light_percentage/65535)*100,"periodo": db["periodo"],
                                  "temp_min": db["temp_min"], "temp_max": db["temp_max"], "histeresis": db["histeresis"],
                                  "foco": db["foco"], "estufa": db["estufa"], "ventilador": db["ventilador"]})
            
        print("Se creó el .json")

        # Publish data in a "database"
        await client.publish(id, data_json, qos = 1) 

        print("Datos publicados")

        # Set actuators based on temperature and light sensor values
        actuators_control(temperature, light_percentage)

    except OSError as e:
            print("Sin sensor")

    await asyncio.sleep(db["periodo"])

async def wifi_han(state):
    print('Wifi is ', 'up' if state else 'down')
    await asyncio.sleep(1)

# If you connect with clean_session True, must re-subscribe (MQTT spec 3.1.2.4)
async def conn_han(client):
    await client.subscribe(id)
    await client.subscribe(id + '/temp_min', 1)
    await client.subscribe(id + '/temp_max', 1)
    await client.subscribe(id + '/periodo', 1)
    await client.subscribe(id + '/destello', 1)
    await client.subscribe(id + '/histeresis', 1)
    await client.subscribe(id + '/porcenaje_luz', 1)

async def main(client):
    global flash_band

    await client.connect()
    print("Conectado al broker MQTT")

    await asyncio.sleep(2)  # Give broker time

    update_actuators()  # Initialize actuators based on db state

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