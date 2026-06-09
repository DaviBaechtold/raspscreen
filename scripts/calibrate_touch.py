"""
Calibração do touch XPT2046.
Execute no Pi com o display conectado: python calibrate_touch.py
Toque nos 4 cantos quando solicitado e anote os valores para touch.py.
"""
import spidev
import RPi.GPIO as GPIO
import time

PIN_T_IRQ = 17
CHANNEL_X = 0xD0
CHANNEL_Y = 0x90

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_T_IRQ, GPIO.IN, pull_up_down=GPIO.PUD_UP)

spi = spidev.SpiDev()
spi.open(0, 1)
spi.max_speed_hz = 1_000_000
spi.mode = 0b00


def read_raw(channel):
    resp = spi.xfer2([channel, 0x00, 0x00])
    return ((resp[1] << 8) | resp[2]) >> 3


def wait_touch():
    print("  Aguardando toque...", end=" ", flush=True)
    while GPIO.input(PIN_T_IRQ) == GPIO.HIGH:
        time.sleep(0.05)
    time.sleep(0.02)
    samples_x = [read_raw(CHANNEL_X) for _ in range(8)]
    samples_y = [read_raw(CHANNEL_Y) for _ in range(8)]
    # descarta min e max, média dos restantes
    samples_x.sort(); samples_y.sort()
    rx = sum(samples_x[2:-2]) // 4
    ry = sum(samples_y[2:-2]) // 4
    while GPIO.input(PIN_T_IRQ) == GPIO.LOW:
        time.sleep(0.05)
    print(f"X={rx}  Y={ry}")
    return rx, ry


print("=== Calibração XPT2046 ===")
print("Toque em cada canto quando solicitado.\n")

print("1. Canto SUPERIOR ESQUERDO:")
x1, y1 = wait_touch()

print("2. Canto SUPERIOR DIREITO:")
x2, y2 = wait_touch()

print("3. Canto INFERIOR ESQUERDO:")
x3, y3 = wait_touch()

print("4. Canto INFERIOR DIREITO:")
x4, y4 = wait_touch()

cal_x_min = min(x1, x3)
cal_x_max = max(x2, x4)
cal_y_min = min(y1, y2)
cal_y_max = max(y3, y4)

print(f"""
=== Resultado ===
Atualize em drivers/touch.py:

CAL_X_MIN, CAL_X_MAX = {cal_x_min}, {cal_x_max}
CAL_Y_MIN, CAL_Y_MAX = {cal_y_min}, {cal_y_max}
""")

spi.close()
GPIO.cleanup()
