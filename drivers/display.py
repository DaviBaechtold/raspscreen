"""
Driver para displays SPI 480x320 com controladores ST7796S ou ILI9488.
Comunicação direta via spidev, sem framebuffer do kernel.
"""
import spidev
import RPi.GPIO as GPIO
import time
import struct
from PIL import Image

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

# Pinagem BCM
PIN_DC   = 24
PIN_RST  = 25
PIN_BL   = 18

# Comandos comuns ST7796S / ILI9488
CMD_SWRESET = 0x01
CMD_SLPOUT  = 0x11
CMD_NORON   = 0x13
CMD_INVOFF  = 0x20
CMD_DISPON  = 0x29
CMD_CASET   = 0x2A
CMD_RASET   = 0x2B
CMD_RAMWR   = 0x2C
CMD_MADCTL  = 0x36
CMD_COLMOD  = 0x3A

# MADCTL: landscape, BGR
MADCTL_MX  = 0x40
MADCTL_MV  = 0x20
MADCTL_BGR = 0x08

WIDTH  = 480
HEIGHT = 320

SPI_CHUNK = 4096


class ST7796SDisplay:
    def __init__(self, spi_bus=0, spi_device=0, spi_speed=40_000_000):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(PIN_DC,  GPIO.OUT)
        GPIO.setup(PIN_RST, GPIO.OUT)
        GPIO.setup(PIN_BL,  GPIO.OUT)

        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        self.spi.max_speed_hz = spi_speed
        self.spi.mode = 0b00

        GPIO.output(PIN_BL, GPIO.HIGH)
        self._reset()
        self._init_sequence()

    def _reset(self):
        GPIO.output(PIN_RST, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(PIN_RST, GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(PIN_RST, GPIO.HIGH)
        time.sleep(0.2)

    def _cmd(self, cmd):
        GPIO.output(PIN_DC, GPIO.LOW)
        self.spi.writebytes([cmd])

    def _data(self, data):
        GPIO.output(PIN_DC, GPIO.HIGH)
        if isinstance(data, int):
            self.spi.writebytes([data])
        else:
            mv = memoryview(data)
            for i in range(0, len(data), SPI_CHUNK):
                self.spi.writebytes2(mv[i:i + SPI_CHUNK])

    def _init_sequence(self):
        self._cmd(CMD_SWRESET); time.sleep(0.15)
        self._cmd(CMD_SLPOUT);  time.sleep(0.15)
        self._cmd(CMD_COLMOD);  self._data(0x55)   # 16-bit RGB565
        self._cmd(CMD_MADCTL);  self._data(MADCTL_MX | MADCTL_MV | MADCTL_BGR)
        self._cmd(CMD_INVOFF)
        self._cmd(CMD_NORON)
        self._cmd(CMD_DISPON)
        time.sleep(0.1)

    def _set_window(self, x0, y0, x1, y1):
        self._cmd(CMD_CASET)
        self._data(struct.pack('>HH', x0, x1))
        self._cmd(CMD_RASET)
        self._data(struct.pack('>HH', y0, y1))
        self._cmd(CMD_RAMWR)

    def display_image(self, image: Image.Image):
        """Envia imagem PIL RGB para o display inteiro via RGB565."""
        img = image.convert('RGB').resize((WIDTH, HEIGHT))
        buf = _rgb_to_rgb565(img)
        self._set_window(0, 0, WIDTH - 1, HEIGHT - 1)
        GPIO.output(PIN_DC, GPIO.HIGH)
        mv = memoryview(buf)
        for i in range(0, len(buf), SPI_CHUNK):
            self.spi.writebytes2(mv[i:i + SPI_CHUNK])

    def backlight(self, on: bool):
        GPIO.output(PIN_BL, GPIO.HIGH if on else GPIO.LOW)

    def cleanup(self):
        self.spi.close()
        GPIO.cleanup()


def _rgb_to_rgb565(img: Image.Image) -> bytearray:
    if _HAS_NUMPY:
        arr = np.asarray(img, dtype=np.uint16)
        r = arr[:, :, 0]
        g = arr[:, :, 1]
        b = arr[:, :, 2]
        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        return bytearray(rgb565.byteswap().tobytes())
    # Pure-Python fallback
    raw = img.tobytes()   # interleaved RGBRGB...
    n = WIDTH * HEIGHT
    buf = bytearray(n * 2)
    for i in range(n):
        r5 = raw[i * 3]     >> 3
        g6 = raw[i * 3 + 1] >> 2
        b5 = raw[i * 3 + 2] >> 3
        pixel = (r5 << 11) | (g6 << 5) | b5
        buf[i * 2]     = pixel >> 8
        buf[i * 2 + 1] = pixel & 0xFF
    return buf
