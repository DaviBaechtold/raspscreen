"""
Driver para displays SPI 480x320 com controladores ST7796S ou ILI9488.
Comunicação direta via spidev, sem framebuffer do kernel.
"""
import spidev
import RPi.GPIO as GPIO
import time
import struct
from PIL import Image

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
            for i in range(0, len(data), 4096):
                self.spi.writebytes(data[i:i+4096])

    def _init_sequence(self):
        # Pixel format: 16-bit RGB565 (0x55).
        # Para ILI9488 em 18-bit use 0x66 e ajuste o empacotamento em display_image().
        self._cmd(CMD_SWRESET); time.sleep(0.15)
        self._cmd(CMD_SLPOUT);  time.sleep(0.15)
        self._cmd(CMD_COLMOD);  self._data(0x55)
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
        """Envia uma imagem PIL RGB para o display inteiro via RGB565."""
        img = image.convert('RGB').resize((WIDTH, HEIGHT))
        r_arr, g_arr, b_arr = [bytes(ch) for ch in img.split()]

        buf = bytearray(WIDTH * HEIGHT * 2)
        for i in range(WIDTH * HEIGHT):
            r5 = r_arr[i] >> 3
            g6 = g_arr[i] >> 2
            b5 = b_arr[i] >> 3
            pixel = (r5 << 11) | (g6 << 5) | b5
            buf[i*2]     = (pixel >> 8) & 0xFF
            buf[i*2 + 1] = pixel & 0xFF

        self._set_window(0, 0, WIDTH - 1, HEIGHT - 1)
        GPIO.output(PIN_DC, GPIO.HIGH)
        for i in range(0, len(buf), 4096):
            self.spi.writebytes(buf[i:i+4096])

    def backlight(self, on: bool):
        GPIO.output(PIN_BL, GPIO.HIGH if on else GPIO.LOW)

    def cleanup(self):
        self.spi.close()
        GPIO.cleanup()
