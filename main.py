# (C) Copyright Peter Hinch 2017-2019.
# Released under the MIT licence.

# Termostato con Raspberry Pi Pico W + DHT22 + relé
# - Modo manual/automático
# - Publica temperatura, humedad, setpoint, periodo y modo en JSON
# - Se suscribe a tópicos para cambiar parámetros y destellar LED
# - Almacena parámetros no volátiles en db.json

# red LED: ON == WiFi fail

# modo == 0 ---> manual
# modo == 1 ---> automático
# rele == 1 ---> apagado
# rele == 0 ---> encendido

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
    # Guarda en db.json los parámetros no volátiles 
    try:
        with open("db.json", "w") as file:
            ujson.dump(data, file)
            print("Datos guardados de manera correcta")
    except:
        print("Error al guardar los datos")

def load_data():
    # Carga los parámetros desde db.json o devuelve {} si no existe/da error
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
    db["setpoint"] = 25
    db["periodo"] = 60
    db["modo"] = 1
    db["rele"] = 1
    save_data(db)

def sub_cb(topic, msg, retained):
    global flash_band
    print('Topic = {} -> Valor = {}'.format(topic.decode(), msg.decode()))

    topic_d = topic.decode()

    # The values are load in a database
    if topic_d == f"{id}/setpoint":
        db["setpoint"] = int(msg.decode())
        save_data(db)
    if topic_d == f"{id}/periodo":
        db["periodo"] = int(msg.decode())
        save_data(db)
    if topic_d == f"{id}/destello": 
        # El comando “destello” no se almacena en db.json, solo lanza la tarea de parpadeo
        asyncio.create_task(flash_led())
    if topic_d == f"{id}/modo":
        db["modo"] = int(msg.decode())
        save_data(db)
    if topic_d == f"{id}/rele": 
        # Si llega “rele”, alterna el estado del relé y actualiza db.json
        if msg.decode() == "rele":
            if db["rele"] == 0:
                r.value(1)
                db["rele"] = 1
            else:
                r.value(0)
                db["rele"] = 0
            save_data(db)

async def flash_led():
    for i in range(0,30):
        l.toggle()
        await asyncio.sleep_ms(200)

async def periodic_run():
    try:
        #d.measure() # Hace la lectura del sensor
        
        try:
            temperatura = d.temperature()
        except OSError as e:
            print("Sin sensor temperatura")
        try:
            humedad=d.humidity()
        except OSError as e:
            print("Sin sensor humedad")
            
        print("Por crear el .json")

        # create json data 
        data_json = ujson.dumps({"temperatura": temperatura, "humedad": humedad, "setpoint": db["setpoint"],"periodo": db["periodo"], "modo": db["modo"]})
            
        print("Se creó el .json")

        # publish data in a "database"
        await client.publish(id, data_json, qos = 1) 

        print("Datos publicados")

        if db["modo"] == 1 and temperatura > db["setpoint"]:
            if db["rele"] == 1: # Turn on relay
                    r.value(0)
                    db["rele"] = 0
                    save_data(db)
        elif db["modo"] == 1: # Turn off relay 
            if db["rele"] == 0:
                    r.value(1)
                    db["rele"] = 1
                    save_data(db)

    except OSError as e:
            print("Sin sensor")

    await asyncio.sleep(db["periodo"])

async def wifi_han(state):
    print('Wifi is ', 'up' if state else 'down')
    await asyncio.sleep(1)

# If you connect with clean_session True, must re-subscribe (MQTT spec 3.1.2.4)
async def conn_han(client):
    await client.subscribe(id)
    await client.subscribe(id + '/setpoint', 1)
    await client.subscribe(id + '/periodo', 1)
    await client.subscribe(id + '/destello', 1)
    await client.subscribe(id + '/modo', 1)
    await client.subscribe(id + '/rele', 1)

async def main(client):
    global flash_band

    await client.connect()

    await asyncio.sleep(2)  # Give broker time

    r.value(db["rele"])

    periodic_task = asyncio.create_task(periodic_run())
    # Lanzamos periodic_run en segundo plano para no bloquear el loop principal

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