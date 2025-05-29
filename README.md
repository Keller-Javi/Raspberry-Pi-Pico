# Raspberry Pi Pico W Termostato

Solución al ejercicio de **IC511 – Internet de las Cosas, Sensores y Redes**.

## Descripción

Termostato con Raspberry Pi Pico W, sensor DHT22 y relé, que puede funcionar en:

- **Automático**: activa el relé si la temperatura supera el setpoint.  
- **Manual**: controla el relé vía MQTT.

## Funcionalidades

- Programado en MicroPython con `uasyncio` y `mqtt_as`.  
- Comunicación segura MQTT (MQTTS).
- Publica cada _periodo_ un JSON en `ID_DEL_DISPOSITIVO` con:
  - temperatura  
  - humedad  
  - setpoint  
  - periodo  
  - modo  
- Se suscribe a:
  - `ID_DEL_DISPOSITIVO/setpoint`  
  - `ID_DEL_DISPOSITIVO/periodo`  
  - `ID_DEL_DISPOSITIVO/destello`  
  - `ID_DEL_DISPOSITIVO/modo`  
  - `ID_DEL_DISPOSITIVO/rele`  
- Guarda en `db.json` (no volátil): setpoint, periodo, modo y estado del relé.  
- Parpadea el LED al recibir `destello`.