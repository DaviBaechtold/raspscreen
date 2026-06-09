#!/usr/bin/env bash
# Instalação completa do Smart Printer no Raspberry Pi.
# Execute como usuário 'pi': bash install.sh
set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INSTALL_DIR="$HOME/smartprinter"

echo "==> Atualizando sistema..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y git wget curl nginx python3-pip python3-dev python3-venv libopenjp2-7

echo "==> Habilitando SPI..."
sudo raspi-config nonint do_spi 0

echo "==> Clonando / atualizando repositório em $INSTALL_DIR..."
if [ -d "$INSTALL_DIR/.git" ]; then
  git -C "$INSTALL_DIR" pull
else
  cp -r "$REPO_DIR" "$INSTALL_DIR"
fi

echo "==> Criando ambiente virtual Python..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

echo "==> Baixando fontes DejaVu..."
FONT_DIR="$INSTALL_DIR/ui/assets"
mkdir -p "$FONT_DIR"
[ -f "$FONT_DIR/font.ttf" ] || wget -q -O "$FONT_DIR/font.ttf" \
  "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSansMono.ttf"
[ -f "$FONT_DIR/font_bold.ttf" ] || wget -q -O "$FONT_DIR/font_bold.ttf" \
  "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSansMono-Bold.ttf"

echo "==> Configurando Nginx..."
sudo cp "$INSTALL_DIR/config/nginx-smartprinter" /etc/nginx/sites-available/smartprinter
sudo ln -sf /etc/nginx/sites-available/smartprinter /etc/nginx/sites-enabled/smartprinter
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

echo "==> Configurando serviço systemd..."
sudo cp "$INSTALL_DIR/scripts/smartprinter-tft.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable smartprinter-tft
sudo systemctl start smartprinter-tft

echo ""
echo "==> Configurações do Klipper (copie manualmente):"
echo "    printer.cfg  → ~/printer_data/config/printer.cfg"
echo "    moonraker.conf → ~/printer_data/config/moonraker.conf"
echo ""
echo "==> IP do Pi:"
hostname -I | awk '{print "    http://" $1}'
echo ""
echo "✓ Instalação concluída!"
