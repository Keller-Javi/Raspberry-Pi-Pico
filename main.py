# Germán Andrés Xander 2024

from machine import Pin
import time

print("\nesperando pulsador")

sw = Pin(28, Pin.IN, Pin.PULL_DOWN) # Se configura el pin 28 como entrada y se activa su pull down
led_board = Pin("LED", Pin.OUT)
contador = 0
bandera = True

while True:
    try:
        if sw.value() and bandera: # Se usa una bandera para que entre una sola vez en el loop 
            # (Los botones usados en este caso no tienen rebote)
            bandera = False
            led_board.toggle()
            # led_board.value(not led_board.value())
            contador += 1
            print(contador)
        elif not sw.value(): # Cuando detecta que se soltó el botón vueve a activar la bandera
            bandera = True
        time.sleep_ms(5) # Las pulsaciones de los humanos dura entre 200ms y 300ms, 
            # por lo que se puede poner un timer con un tiempo superior y evitar la bandera
    except KeyboardInterrupt:
        print('Keyboard interrupt at loop level.')
        break
