from machine import Pin
from time import sleep

led_board = Pin("LED", Pin.OUT)
sleep(1)    #le damos tiempo a vREPL
print("\nLED esta destellando...")
while True:
    try:
        led_board.toggle() # opsión unica para el pico
        # led_board.value(not led_board.value()) # Lo mismo pero también anda en el esp32, escribe el estado negado
        sleep(.25)
    except KeyboardInterrupt: # Except es para que no salte un mensaje raro al terminar el programa con ctrl + c
        break
led_board.off()
print("Listo")
