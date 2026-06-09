"""
Renderiza o dashboard no buffer Pillow.
Layout dark mode 480x320 — mesma paleta da interface web.
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from core.moonraker import PrinterState

ASSETS = Path(__file__).parent / "assets"

C_BG       = (18,  18,  18)
C_SURFACE  = (30,  30,  30)
C_SURFACE2 = (45,  45,  45)
C_ACCENT   = (0,   188, 212)
C_TEXT     = (230, 230, 230)
C_DIM      = (120, 120, 120)
C_HOT      = (255, 87,  34)
C_WARM     = (255, 193, 7)
C_OK       = (76,  175, 80)
C_ERROR    = (244, 67,  54)

STATUS_COLORS = {
    "idle":         C_OK,
    "printing":     C_ACCENT,
    "paused":       C_WARM,
    "error":        C_ERROR,
    "disconnected": C_DIM,
}

W, H = 480, 320

# Regiões dos botões (x0, y0, x1, y1) — usadas pelo touch handler
BUTTON_REGIONS = [
    (8,   175, 158, 227),  # PLA
    (166, 175, 316, 227),  # ABS
    (324, 175, 474, 227),  # Resfriar
]
BUTTON_ACTIONS = ["preheat_pla", "preheat_abs", "cooldown"]


_fonts_cache = None

def _load_fonts():
    global _fonts_cache
    if _fonts_cache:
        return _fonts_cache
    try:
        reg  = ImageFont.truetype(str(ASSETS / "font.ttf"),      14)
        bold = ImageFont.truetype(str(ASSETS / "font_bold.ttf"),  16)
        lg   = ImageFont.truetype(str(ASSETS / "font_bold.ttf"),  22)
        xl   = ImageFont.truetype(str(ASSETS / "font_bold.ttf"),  32)
        sm   = ImageFont.truetype(str(ASSETS / "font.ttf"),       11)
    except IOError:
        default = ImageFont.load_default()
        reg = bold = lg = xl = sm = default
    _fonts_cache = (reg, bold, lg, xl, sm)
    return _fonts_cache


def _draw_temp_card(draw, x, y, w, h, current, target, label, fonts):
    reg, bold, lg, _, sm = fonts
    draw.rounded_rectangle([x, y, x+w, y+h], radius=8, fill=C_SURFACE)
    draw.text((x+10, y+8),  label, font=bold, fill=C_DIM)

    color = C_HOT if current > 50 else C_TEXT
    draw.text((x+10, y+26), f"{current:.1f}°", font=lg, fill=color)
    draw.text((x+10, y+54), f"→ {target:.0f}°", font=reg,
              fill=C_ACCENT if target > 0 else C_DIM)

    if target > 0:
        ratio   = min(current / target, 1.0)
        bx, by  = x+8, y+h-14
        bw_full = w - 16
        draw.rounded_rectangle([bx, by, bx+bw_full, by+8], radius=4, fill=C_SURFACE2)
        if ratio > 0:
            fill = C_OK if ratio >= 0.98 else C_WARM
            draw.rounded_rectangle([bx, by, bx+int(bw_full*ratio), by+8],
                                    radius=4, fill=fill)


def render(state: PrinterState) -> Image.Image:
    fonts = _load_fonts()
    reg, bold, lg, xl, sm = fonts

    img  = Image.new("RGB", (W, H), C_BG)
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([0, 0, W, 44], fill=C_SURFACE)
    draw.text((12, 12), "Smart Printer", font=bold, fill=C_ACCENT)

    ip_text = f"IP: {state.local_ip}"
    ip_w    = int(draw.textlength(ip_text, font=reg))
    draw.text((W - ip_w - 12, 15), ip_text, font=reg, fill=C_DIM)

    status_label = state.status.upper()
    status_color = STATUS_COLORS.get(state.status, C_DIM)
    badge_w      = int(draw.textlength(status_label, font=sm)) + 20
    badge_x      = (W - badge_w) // 2
    draw.rounded_rectangle([badge_x, 10, badge_x+badge_w, 34], radius=10, fill=status_color)
    draw.text((badge_x+10, 14), status_label, font=sm, fill=C_BG)

    # Temperaturas
    _draw_temp_card(draw, 8,   52, 140, 100, state.extruder_temp, state.extruder_target, "BICO", fonts)
    _draw_temp_card(draw, 156, 52, 140, 100, state.bed_temp,      state.bed_target,      "MESA", fonts)

    # Card de progresso
    px, py = 304, 52
    draw.rounded_rectangle([px, py, px+168, py+100], radius=8, fill=C_SURFACE)
    draw.text((px+10, py+8),  "PROGRESSO", font=bold, fill=C_DIM)

    pct = int(state.progress * 100)
    draw.text((px+10, py+24), f"{pct}%", font=xl, fill=C_TEXT)

    if state.total_layers > 0:
        draw.text((px+10, py+60),
                  f"Camada {state.current_layer}/{state.total_layers}",
                  font=sm, fill=C_DIM)

    bx, by = px+8, py+82
    bw     = 152
    draw.rounded_rectangle([bx, by, bx+bw, by+10], radius=5, fill=C_SURFACE2)
    if pct > 0:
        draw.rounded_rectangle([bx, by, bx+int(bw*state.progress), by+10],
                                radius=5, fill=C_ACCENT)

    # Nome do arquivo
    if state.filename:
        fname = (state.filename[:38] + "…") if len(state.filename) > 38 else state.filename
        draw.text((8, 160), fname, font=sm, fill=C_DIM)

    # Botões
    buttons = [
        ("PLA 200/60",   (8,   175), C_WARM),
        ("ABS 240/100",  (166, 175), C_HOT),
        ("RESFRIAR",     (324, 175), C_DIM),
    ]
    for label, (bx, by), accent in buttons:
        bw, bh = 150, 52
        draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=8, fill=C_SURFACE2)
        draw.rounded_rectangle([bx, by, bx+bw, by+4],  radius=0, fill=accent)
        lw = int(draw.textlength(label, font=bold))
        draw.text((bx + (bw - lw) // 2, by+16), label, font=bold, fill=C_TEXT)

    # Rodapé
    draw.rectangle([0, H-28, W, H], fill=C_SURFACE)
    draw.text((12, H-20), "Moonraker API  ●  Klipper", font=sm, fill=C_DIM)

    return img
