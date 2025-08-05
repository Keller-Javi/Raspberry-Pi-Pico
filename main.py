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
d = dht.DHT22(Pin(13))

# Set relay pin as output
r = Pin(16, Pin.OUT)

# Set LED pin as output
l = Pin("LED", Pin.OUT)

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
    for i in range(0,30):
        l.toggle()
        await asyncio.sleep_ms(200)

async def periodic_run():
    try:
        d.measure() # Hace la lectura del sensor
        
        try:
            temperatura = d.temperature()
        except OSError as e:
            print("Sin sensor temperatura")

        try:
            sensor_luz = 776
        except OSError as e:
            print("Sin sensor de luz")
            
        print("Por crear el .json")

        # Create json data 
        data_json = ujson.dumps({"temperatura": temperatura, "porcentaje_luz": (sensor_luz/4095)*100,"periodo": db["periodo"],
                                  "temp_min": db["temp_min"], "temp_max": db["temp_max"], "histeresis": db["histeresis"],
                                  "foco": db["foco"], "estufa": db["estufa"], "ventilador": db["ventilador"]})
            
        print("Se creó el .json")

        # Publish data in a "database"
        await client.publish(id, data_json, qos = 1) 

        print("Datos publicados")

        # Check if the temperature is in the range
        if temperatura > db["temp_max"] + db["histeresis"]:
            if db["ventilador"] == 0:
                db["ventilador"] = 1
                save_data(db)
                print("Ventilador encendido")
        elif temperatura < db["temp_min"] - db["histeresis"]:
            if db["ventilador"] == 1:
                db["ventilador"] = 0
                save_data(db)
                print("Ventilador apagado")
        
        if temperatura < db["temp_min"] - db["histeresis"]:
            if db["estufa"] == 0:
                db["estufa"] = 1
                save_data(db)
                print("Estufa encendida")
        elif temperatura > db["temp_max"] + db["histeresis"]:
            if db["estufa"] == 1:
                db["estufa"] = 0
                save_data(db)
                print("Estufa apagada")
        
        if (sensor_luz/4095)*100 < db["porcentaje_luz"]:
            if db["foco"] == 0:
                db["foco"] = 1
                save_data(db)
                print("Foco encendido")
        elif (sensor_luz/4095)*100 >= db["porcentaje_luz"]:
            if db["foco"] == 1:
                db["foco"] = 0
                save_data(db)
                print("Foco apagado")

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

    r.value(db["rele"])

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