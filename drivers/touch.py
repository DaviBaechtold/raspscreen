"""
Driver para touch resistivo XPT2046 via SPI (CE1).
Usa interrupção GPIO no pino T_IRQ/PEN para eficiência.
"""
import spidev
import RPi.GPIO as GPIO
import time

PIN_T_IRQ = 17  # T_IRQ / PEN

CHANNEL_X = 0xD0  # Differential X
CHANNEL_Y = 0x90  # Differential Y

# Calibração — ajuste após rodar scripts/calibrate_touch.py no seu display
CAL_X_MIN, CAL_X_MAX = 200, 3800
CAL_Y_MIN, CAL_Y_MAX = 200, 3800
SCREEN_W, SCREEN_H   = 480, 320


def _force_gpio_reset(pin: int):
    """Force-unexport pin via sysfs to clear stale kernel edge-detection state."""
    try:
        with open("/sys/class/gpio/unexport", "w") as f:
            f.write(str(pin))
    except OSError:
        pass


class XPT2046Touch:
    def __init__(self, spi_bus=0, spi_device=1, spi_speed=1_000_000):
        _force_gpio_reset(PIN_T_IRQ)

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(PIN_T_IRQ, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        self.spi.max_speed_hz = spi_speed
        self.spi.mode = 0b00

        self._callback = None
        GPIO.add_event_detect(
            PIN_T_IRQ, GPIO.FALLING,
            callback=self._irq_handler,
            bouncetime=50,
        )

    def _read_raw(self, channel) -> int:
        resp = self.spi.xfer2([channel, 0x00, 0x00])
        return ((resp[1] << 8) | resp[2]) >> 3

    def _irq_handler(self, _channel):
        if GPIO.input(PIN_T_IRQ) != GPIO.LOW:
            return
        time.sleep(0.01)
        raw_x = self._read_raw(CHANNEL_X)
        raw_y = self._read_raw(CHANNEL_Y)
        sx = int((raw_x - CAL_X_MIN) * SCREEN_W / (CAL_X_MAX - CAL_X_MIN))
        sy = int((raw_y - CAL_Y_MIN) * SCREEN_H / (CAL_Y_MAX - CAL_Y_MIN))
        sx = max(0, min(SCREEN_W - 1, sx))
        sy = max(0, min(SCREEN_H - 1, sy))
        if self._callback:
            self._callback(sx, sy)

    def on_touch(self, callback):
        """Registra callback(x, y) chamado em cada toque."""
        self._callback = callback

    def cleanup(self):
        try:
            GPIO.remove_event_detect(PIN_T_IRQ)
        except Exception:
            pass
        self.spi.close()
        GPIO.cleanup(PIN_T_IRQ)
