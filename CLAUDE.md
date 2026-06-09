# CLAUDE.md — RaspScreen / Smart Printer

## O Projeto

Dashboard de controle para Ender 3 V2 rodando Klipper num Raspberry Pi 3 B v1.2.
Interface dupla: display TFT SPI 4" local + dashboard web remoto.

## Acesso ao Pi

```bash
ssh -i ~/.ssh/raspscreen pi@raspscreen.local    # LAN
ssh -i ~/.ssh/raspscreen pi@100.77.228.94        # Tailscale (fora de casa)
```

Sincronizar arquivo para o Pi:
```bash
scp -i ~/.ssh/raspscreen <arquivo> pi@raspscreen.local:/home/pi/smartprinter/<destino>
```

Depois de alterar qualquer arquivo Python do TFT:
```bash
sudo systemctl restart smartprinter-tft
```

## Regras de Desenvolvimento

- **Compilar Klipper localmente**, não no Pi. Usar `gcc-arm-none-eabi` em `/tmp/klipper/`.
- **Firmware GD32F103 OBRIGATÓRIO:** `CONFIG_STM32_CLOCK_REF_INTERNAL=y` + `CONFIG_STM32_FLASH_START_7000=y`. Ver `memory/firmware_klipper.md`.
- **Moonraker entry point:** `python -m moonraker -d /home/pi/printer_data` (não `moonraker.py`).
- **numpy disponível** no venv do TFT — usar para operações de imagem RGB565.
- **Touch GPIO 17** pode falhar após crash sem cleanup — reboot resolve. Touch é opcional (sistema funciona sem).

## Estrutura de Arquivos

```
main.py                   # Ponto de entrada asyncio
drivers/
  display.py              # ST7796S/ILI9488 via spidev + numpy RGB565
  touch.py                # XPT2046 CE1, IRQ GPIO17 (opcional)
core/
  moonraker.py            # WebSocket client + HTTP para gcodes
ui/
  renderer.py             # Pillow 480×320 dark mode
web/
  index.html              # Dashboard HTML/CSS/JS puro
config/
  printer.cfg             # Klipper — Ender 3 V2 (GD32F103)
  moonraker.conf          # host 0.0.0.0:7125, octoprint_compat
  nginx-smartprinter      # reverse proxy porta 80
scripts/
  smartprinter-tft.service
  install.sh
  calibrate_touch.py
```

## Serviços no Pi

| Serviço          | Porta  | Restart                                       |
|------------------|--------|-----------------------------------------------|
| klipper          | socket | `sudo systemctl restart klipper`              |
| moonraker        | 7125   | `sudo systemctl restart moonraker`            |
| crowsnest        | 8080   | `sudo systemctl reset-failed crowsnest && sudo systemctl start crowsnest` |
| nginx            | 80     | `sudo systemctl restart nginx`                |
| smartprinter-tft | —      | `sudo systemctl restart smartprinter-tft`     |

## Pinagem GPIO (BCM)

| Sinal     | GPIO | Pino Físico | Dispositivo      |
|-----------|------|-------------|------------------|
| Display CS| 8    | 24          | SPI CE0          |
| Display DC| 24   | 18          | saída digital    |
| Display RST| 25  | 22          | saída digital    |
| Backlight | 18   | 12          | PWM0             |
| Touch CS  | 7    | 26          | SPI CE1          |
| Touch IRQ | 17   | 11          | entrada (PEN)    |
| MOSI      | 10   | 19          | compartilhado    |
| MISO      | 9    | 21          | compartilhado    |
| SCLK      | 11   | 23          | compartilhado    |

## Logs Úteis

```bash
sudo journalctl -u smartprinter-tft -f     # TFT em tempo real
sudo journalctl -u moonraker -n 30         # Moonraker últimas linhas
sudo journalctl -u crowsnest -n 20         # Câmera
sudo journalctl -u klipper -n 20           # Klipper
```

## Testar API Moonraker

```bash
curl http://raspscreen.local/moonraker/printer/info
curl http://raspscreen.local/moonraker/printer/objects/query?extruder&heater_bed
```
