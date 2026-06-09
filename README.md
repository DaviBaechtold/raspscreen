# RaspScreen — Smart Printer

Controle completo de uma Creality Ender 3 V2 via Raspberry Pi 3 B, com interface dupla:
**display TFT SPI 4" local** (Python/Pillow, dark mode) + **dashboard web remoto** (HTML/JS puro).

Usa Klipper + Moonraker como backend. Acesso remoto via Tailscale.

---

## Hardware

| Componente | Detalhe |
|---|---|
| Raspberry Pi | 3 B v1.2 |
| Impressora | Creality Ender 3 V2 (board 4.2.7, MCU GD32F103) |
| Display | TFT SPI 4.0" 480×320 (ST7796S / ILI9488 + touch XPT2046) |
| Câmera | Logitech C922 Pro Stream |
| Acesso remoto | Tailscale mesh VPN |

## Stack de Software

| Componente | Função |
|---|---|
| Klipper | Firmware do MCU da impressora |
| Moonraker | API REST + WebSocket (porta 7125) |
| Mainsail | Web UI para configuração do Klipper |
| Crowsnest | Streaming da webcam via ustreamer (porta 8080) |
| Nginx | Reverse proxy porta 80 |
| smartprinter-tft | Dashboard local no display SPI (este repositório) |

## Pinagem GPIO (BCM)

```
Display SPI (CE0)              Touch XPT2046 (CE1)
─────────────────              ──────────────────────
GPIO 8  (CE0)  → CS            GPIO 7  (CE1)  → T_CS
GPIO 24        → DC/RS         GPIO 17        → T_IRQ / PEN
GPIO 25        → RST
GPIO 18 (PWM0) → BL/LED
                               Barramento compartilhado:
GPIO 10 (MOSI) → SDI           GPIO 10 → TDI
GPIO 11 (SCLK) → SCK           GPIO 11 → TCK
GPIO 9  (MISO) → SDO           GPIO 9  → TDO
```

## Estrutura

```
├── main.py                       # Ponto de entrada (asyncio)
├── drivers/
│   ├── display.py                # Driver SPI ST7796S/ILI9488 (numpy RGB565)
│   └── touch.py                  # Driver XPT2046 com interrupção GPIO
├── core/
│   └── moonraker.py              # Cliente WebSocket/HTTP Moonraker
├── ui/
│   └── renderer.py               # Renderização Pillow 480×320 dark mode
├── web/
│   └── index.html                # Dashboard web (sem dependências)
├── config/
│   ├── printer.cfg               # Klipper — Ender 3 V2
│   ├── moonraker.conf            # Moonraker (inclui OctoPrint compat)
│   └── nginx-smartprinter        # Nginx reverse proxy
└── scripts/
    ├── install.sh                # Instalação automatizada
    ├── smartprinter-tft.service  # Serviço systemd
    └── calibrate_touch.py        # Calibração do touch resistivo
```

## Instalação no Pi

```bash
# 1. Clone
git clone https://github.com/DaviBaechtold/raspscreen.git ~/smartprinter

# 2. Instale dependências Python
python3 -m venv ~/smartprinter/venv
~/smartprinter/venv/bin/pip install -r ~/smartprinter/requirements.txt

# 3. Copie as configs
cp ~/smartprinter/config/printer.cfg    ~/printer_data/config/printer.cfg
cp ~/smartprinter/config/moonraker.conf ~/printer_data/config/moonraker.conf

# 4. Configure o serial da impressora em printer.cfg
# ls /dev/serial/by-id/
nano ~/printer_data/config/printer.cfg

# 5. Instale o serviço systemd
sudo cp ~/smartprinter/scripts/smartprinter-tft.service /etc/systemd/system/
sudo systemctl enable --now smartprinter-tft
```

## Acesso

| Interface | URL |
|---|---|
| Dashboard Web | `http://<IP-DO-PI>` |
| Mainsail | `http://<IP-DO-PI>/mainsail/` |
| Webcam | `http://<IP-DO-PI>/webcam/?action=stream` |
| Moonraker API | `http://<IP-DO-PI>/moonraker/` |
| Acesso externo | `http://100.77.228.94` (Tailscale) |

## Creality Print / Slicer

Adicionar impressora → tipo **OctoPrint** → Host: `http://<IP-DO-PI>/moonraker/`

## Firmware Klipper (GD32F103)

A board 4.2.7 usa GD32F103 (clone do STM32). Requer configuração específica:

```
CONFIG_MACH_STM32F103=y
CONFIG_STM32_CLOCK_REF_INTERNAL=y   # clock interno 64MHz (GD32 sem cristal)
CONFIG_STM32_FLASH_START_7000=y     # bootloader Creality 28KiB
CONFIG_STM32_SERIAL_USART1=y
CONFIG_SERIAL_BAUD=250000
```

Compilar **localmente** (não no Pi — muito lento):
```bash
sudo apt install gcc-arm-none-eabi
cd /tmp/klipper && make
```

Flash: copiar `.bin` para o SD card com nome diferente do último arquivo flashado.

## Troubleshooting

**Display tela branca/preta:**
Trocar `CMD_COLMOD` de `0x55` para `0x66` em `drivers/display.py` (ILI9488 18-bit).

**Câmera offline após reboot:**
Crowsnest pode iniciar antes da câmera USB ser enumerada.
```bash
sudo systemctl reset-failed crowsnest && sudo systemctl start crowsnest
```

**Touch não responde:**
Fazer reboot limpo — estado GPIO persiste após crash sem cleanup.
```bash
sudo reboot
```

**Logs:**
```bash
sudo journalctl -u smartprinter-tft -f   # TFT
sudo journalctl -u moonraker -f          # Moonraker
sudo journalctl -u klipper -f            # Klipper
```

**Atualizar após mudanças:**
```bash
cd ~/smartprinter && git pull
sudo systemctl restart smartprinter-tft
```
