# RaspScreen — Smart Printer

Dashboard de controle para Ender 3 V2 rodando Klipper no Raspberry Pi 3 B.  
Interface dupla: display TFT SPI 4" local + dashboard web remoto (dark mode).

## Hardware

| Componente | Detalhe |
|---|---|
| Raspberry Pi | 3 B v1.2 |
| Impressora | Creality Ender 3 V2 (board 32-bit, USB) |
| Display | TFT SPI 4.0" 480×320 (ST7796S ou ILI9488 + touch XPT2046) |
| Câmera | Webcam USB genérica |
| Rede | Ethernet LAN |

## Pinagem GPIO (BCM)

```
Display SPI (CE0)          Touch XPT2046 (CE1)
──────────────────         ──────────────────────
GPIO10 (MOSI) → SDA        GPIO9  (MISO) → SDO
GPIO11 (SCLK) → SCL        GPIO11 (SCLK) → CLK (compartilhado)
GPIO8  (CE0)  → CS         GPIO7  (CE1)  → T_CS
GPIO24        → DC/RS       GPIO17        → T_IRQ / PEN
GPIO25        → RST
GPIO18 (PWM0) → BL/LED
```

## Estrutura

```
├── main.py                 # Ponto de entrada (asyncio)
├── drivers/
│   ├── display.py          # Driver SPI ST7796S/ILI9488
│   └── touch.py            # Driver XPT2046 com interrupção GPIO
├── core/
│   └── moonraker.py        # Cliente WebSocket/HTTP Moonraker
├── ui/
│   └── renderer.py         # Renderização Pillow 480×320
├── web/
│   └── index.html          # Dashboard web (HTML/CSS/JS puro)
├── config/
│   ├── printer.cfg         # Klipper — Ender 3 V2
│   ├── moonraker.conf      # Moonraker
│   └── nginx-smartprinter  # Nginx reverse proxy
└── scripts/
    ├── install.sh           # Instalação automatizada
    ├── smartprinter-tft.service  # Serviço systemd
    └── calibrate_touch.py  # Calibração do touch resistivo
```

## Instalação no Pi

```bash
# 1. Clone o repositório
git clone https://github.com/DaviBaechtold/raspscreen.git ~/smartprinter-repo

# 2. Execute o instalador
bash ~/smartprinter-repo/scripts/install.sh

# 3. Copie as configs do Klipper
cp ~/smartprinter-repo/config/printer.cfg    ~/printer_data/config/printer.cfg
cp ~/smartprinter-repo/config/moonraker.conf ~/printer_data/config/moonraker.conf

# 4. Edite o serial da impressora em printer.cfg
# Descubra com: ls /dev/serial/by-id/
nano ~/printer_data/config/printer.cfg

# 5. Calibre o touch (opcional mas recomendado)
source ~/smartprinter/venv/bin/activate
python ~/smartprinter/scripts/calibrate_touch.py
```

## Acesso

| Interface | URL |
|---|---|
| Dashboard Web | `http://<IP-DO-PI>` |
| Mainsail (config) | `http://<IP-DO-PI>/mainsail/` |
| Webcam | `http://<IP-DO-PI>/webcam/?action=stream` |
| Moonraker API | `http://<IP-DO-PI>/moonraker/` |

## Creality Print

Adicionar impressora → tipo **OctoPrint** → Host: `http://<IP-DO-PI>/moonraker/`

## Atualizar após mudanças

```bash
cd ~/smartprinter
git pull
sudo systemctl restart smartprinter-tft
```

## Troubleshooting

**Display não inicia (tela branca/preta):**  
Troque `CMD_COLMOD` de `0x55` para `0x66` em `drivers/display.py` (ILI9488 18-bit).

**Touch descalibrado:**  
Execute `python scripts/calibrate_touch.py` e atualize as constantes em `drivers/touch.py`.

**Logs do serviço TFT:**  
`sudo journalctl -u smartprinter-tft -f`
