# Original author: Peter Hinch
# Copyright Peter Hinch 2017-2020 Released under the MIT license
# Adaptation Germán Andrés Xander 2024

import asyncio
from machine import Pin
from led_async import LED_async  # Class as listed above

async def main(): # Se define como una coroutine
    pines = [14, 17]
    leds = [LED_async(n) for n in pines]
    for n, led in enumerate(leds):
        led.flash(0.7 + n/4)
    sw = Pin(28, Pin.IN, Pin.PULL_DOWN)
    while not sw.value():
        await asyncio.sleep_ms(100)
    for n, led in enumerate(leds):
        led.off()

try:
    asyncio.run(main()) # Ejecutamos la coroutine 
except KeyboardInterrupt:
    print('Keyboard interrupt at loop level.')

# await async.sleep(delay) duerme la función por ese tiempo y otra función puede ejecutarse en ese tiempo 

# await hace que se duerma por un tiempo y si hay otra función esperando, esta se ejecuta
#   hasta que se despierte la otra función

# para que sean concurrentes hay que utilizar tareas 
#   (Las tareas se ven dentro del archivo led_async.py)