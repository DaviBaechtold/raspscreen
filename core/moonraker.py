"""
Cliente assíncrono para a API do Moonraker.
WebSocket para telemetria em tempo real + HTTP para ações pontuais.
"""
import asyncio
import json
import socket
import requests
import websockets
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class PrinterState:
    status: str = "disconnected"
    extruder_temp: float = 0.0
    extruder_target: float = 0.0
    bed_temp: float = 0.0
    bed_target: float = 0.0
    progress: float = 0.0
    current_layer: int = 0
    total_layers: int = 0
    filename: str = ""
    local_ip: str = ""


class MoonrakerClient:
    SUBSCRIBED_OBJECTS = {
        "extruder":       ["temperature", "target"],
        "heater_bed":     ["temperature", "target"],
        "print_stats":    ["state", "filename", "current_layer", "total_layer"],
        "display_status": ["progress"],
        "toolhead":       ["position"],
    }

    STATUS_MAP = {
        "standby":  "idle",
        "printing": "printing",
        "paused":   "paused",
        "error":    "error",
        "complete": "idle",
    }

    def __init__(self, host: str = "localhost", port: int = 7125):
        self.base_url = f"http://{host}:{port}"
        self.ws_url   = f"ws://{host}:{port}/websocket"
        self.state    = PrinterState()
        self._on_update: Optional[Callable] = None
        self._req_id  = 1

    def on_update(self, callback: Callable[[PrinterState], None]):
        self._on_update = callback

    def _notify(self):
        if self._on_update:
            self._on_update(self.state)

    def _resolve_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self.state.local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            self.state.local_ip = "?.?.?.?"

    def send_gcode(self, script: str) -> bool:
        try:
            r = requests.post(
                f"{self.base_url}/printer/gcode/script",
                json={"script": script},
                timeout=5,
            )
            return r.status_code == 200
        except requests.RequestException:
            return False

    def preheat_pla(self):
        self.send_gcode("PREHEAT_PLA")

    def preheat_abs(self):
        self.send_gcode("PREHEAT_ABS")

    def cooldown(self):
        self.send_gcode("COOLDOWN")

    def _apply_update(self, data: dict):
        if "extruder" in data:
            e = data["extruder"]
            self.state.extruder_temp   = e.get("temperature", self.state.extruder_temp)
            self.state.extruder_target = e.get("target",      self.state.extruder_target)

        if "heater_bed" in data:
            b = data["heater_bed"]
            self.state.bed_temp   = b.get("temperature", self.state.bed_temp)
            self.state.bed_target = b.get("target",      self.state.bed_target)

        if "print_stats" in data:
            ps = data["print_stats"]
            if "state" in ps:
                self.state.status = self.STATUS_MAP.get(ps["state"], self.state.status)
            self.state.filename      = ps.get("filename",      self.state.filename)
            self.state.current_layer = ps.get("current_layer") or self.state.current_layer
            self.state.total_layers  = ps.get("total_layer")   or self.state.total_layers

        if "display_status" in data:
            self.state.progress = data["display_status"].get("progress", self.state.progress)

    async def _subscribe(self, ws):
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "method":  "printer.objects.subscribe",
            "params":  {"objects": self.SUBSCRIBED_OBJECTS},
            "id":      self._req_id,
        }))
        self._req_id += 1

    async def run(self):
        """Loop principal com reconexão automática."""
        self._resolve_local_ip()

        while True:
            try:
                async with websockets.connect(self.ws_url, ping_interval=20) as ws:
                    await self._subscribe(ws)
                    async for raw in ws:
                        msg    = json.loads(raw)
                        method = msg.get("method", "")

                        if method == "notify_status_update":
                            self._apply_update(msg["params"][0])
                            self._notify()
                        elif method == "notify_klippy_ready":
                            self.state.status = "idle"
                            self._notify()
                        elif method == "notify_klippy_disconnect":
                            self.state.status = "disconnected"
                            self._notify()

            except Exception:
                self.state.status = "disconnected"
                self._notify()
                await asyncio.sleep(5)
