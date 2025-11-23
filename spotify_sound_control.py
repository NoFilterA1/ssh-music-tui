import curses
import subprocess
import threading
import time
import select
import os
import shutil
from pathlib import Path

PLAYER = "spotify"
HAVE_PLAYERCTL = shutil.which("playerctl") is not None

def is_termux():
    return "com.termux" in os.environ.get("PREFIX", "")

def run_async(func, *args, **kwargs):
    threading.Thread(target=lambda: func(*args, **kwargs), daemon=True).start()

# --- НОВАЯ ЛОГИКА ГРОМКОСТИ ЧЕРЕЗ PLAYERCTL ---

def get_volume():
    """Получает громкость через playerctl (0.0 - 1.0)."""
    if HAVE_PLAYERCTL:
        try:
            # playerctl возвращает число типа 0.55 для 55%
            vol_str = subprocess.check_output(
                ['playerctl', '-p', PLAYER, 'volume'],
                text=True, timeout=1
            ).strip()
            # Если плеер ничего не вернул или вернул пустоту
            if not vol_str:
                return 0
            return int(float(vol_str) * 100)
        except Exception:
            pass
    return 0

def set_volume(percent):
    """Устанавливает громкость через playerctl."""
    if HAVE_PLAYERCTL:
        try:
            # playerctl принимает значение от 0.0 до 1.0
            vol_float = max(0, min(100, percent)) / 100.0
            subprocess.call(
                ['playerctl', '-p', PLAYER, 'volume', str(vol_float)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

# -----------------------------------------------

def playerctl_cmd(cmd):
    if HAVE_PLAYERCTL:
        try:
            subprocess.call(['playerctl', '-p', PLAYER, cmd],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
        except Exception:
            pass

def get_current_track():
    if HAVE_PLAYERCTL:
        try:
            return subprocess.check_output(
                ['playerctl', '-p', PLAYER, 'metadata', '--format', '{{artist}} - {{title}}'],
                text=True, timeout=2
            ).strip()
        except Exception:
            return "Spotify not active"
    return "Demo Artist - Demo Track"

class CavaReader(threading.Thread):
    def __init__(self, bars_count=50):
        super().__init__(daemon=True)
        self.bars_count = bars_count
        self.running = True
        self.data = []
        self.lock = threading.Lock()
        self.fifo_path = Path(f"/tmp/cava_fifo_{os.getpid()}")
        self.proc = None
        self.available = shutil.which("cava") is not None and not is_termux()
        if self.available:
            self.start_cava()

    def start_cava(self):
        try:
            if self.fifo_path.exists():
                self.fifo_path.unlink()
            os.mkfifo(self.fifo_path)
            config_path = Path(f"/tmp/cava_config_{os.getpid()}")
            cava_config = f"""
[general]
bars = {self.bars_count}
[output]
method = raw
raw_target = {self.fifo_path}
data_format = ascii
"""
            with open(config_path, "w") as f:
                f.write(cava_config)
            self.proc = subprocess.Popen(["cava", "-p", str(config_path)])
        except Exception:
            self.available = False

    def run(self):
        if not self.available:
            return
        try:
            with open(self.fifo_path, "r") as f:
                while self.running:
                    ready, _, _ = select.select([f], [], [], 0.05)
                    if ready:
                        line = f.readline().strip()
                        if line:
                            bars = list(map(int, line.split(";")[:-1]))
                            with self.lock:
                                self.data = bars
        except Exception:
            pass

    def get_bars(self):
        with self.lock:
            return self.data.copy()

    def stop(self):
        self.running = False
        if self.proc:
            self.proc.terminate()
            self.proc.wait(timeout=2)
        if self.fifo_path.exists():
            try:
                self.fifo_path.unlink()
            except Exception:
                pass

class Button:
    def __init__(self, text, callback):
        self.text = text
        self.callback = callback
        self.x1 = self.x2 = self.y1 = self.y2 = 0
        self.hover = False

    def set_position(self, x, y, width=None, height=2):
        w = width if width else len(self.text)
        self.x1 = x
        self.x2 = x + w - 1
        self.y1 = y
        self.y2 = y + height - 1

    def contains(self, mx, my):
        return self.x1 <= mx <= self.x2 and self.y1 <= my <= self.y2

def draw_ui(stdscr, cava_data, volume, track, buttons, scroll_index, max_track_len):
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    if h < 15 or w < 40:
        stdscr.addstr(0, 0, "Terminal too small")
        stdscr.noutrefresh()
        curses.doupdate()
        return

    panel_height = 7
    cava_height = h - panel_height - 1

    if cava_data:
        for i, val in enumerate(cava_data):
            col = int(i * (w / len(cava_data)))
            bar_height = int(val / 5)
            for y in range(cava_height):
                stdscr.addstr(y, col, "│", curses.color_pair(7))
                if y >= cava_height - bar_height:
                    stdscr.addstr(y, col, "█", curses.color_pair(6))
    else:
        stdscr.addstr(0, 0, "[No CAVA]")

    stdscr.hline(cava_height, 0, "-", w)

    track_line = cava_height + 1
    left_btn, track_btn, right_btn = buttons[:3]

    if len(track) > max_track_len:
        start = scroll_index
        display_track = (track + "   " + track)[start:start + max_track_len]
    else:
        display_track = track

    total_len = len(left_btn.text) + 4 + len(display_track) + 4 + len(right_btn.text)
    start_x = (w - total_len) // 2

    color = curses.color_pair(4 if left_btn.hover else 5)
    stdscr.addstr(track_line, start_x, f" {left_btn.text} ", color)
    left_btn.set_position(start_x, track_line, width=len(left_btn.text) + 2)

    tx = start_x + len(left_btn.text) + 4
    color = curses.color_pair(4 if track_btn.hover else 5)
    stdscr.addstr(track_line, tx, f" {display_track} ", color)
    track_btn.set_position(tx, track_line, width=len(display_track) + 2)

    rx = tx + len(display_track) + 4
    color = curses.color_pair(4 if right_btn.hover else 5)
    stdscr.addstr(track_line, rx, f" {right_btn.text} ", color)
    right_btn.set_position(rx, track_line, width=len(right_btn.text) + 2)

    vol_line = track_line + 3
    minus_btn, plus_btn = buttons[3], buttons[4]
    vol_str = f"{volume}%"
    total_len = len(minus_btn.text) + 4 + len(vol_str) + 4 + len(plus_btn.text)
    start_x = (w - total_len) // 2

    color = curses.color_pair(4 if minus_btn.hover else 5)
    stdscr.addstr(vol_line, start_x, f" {minus_btn.text} ", color)
    minus_btn.set_position(start_x, vol_line, width=len(minus_btn.text) + 2)

    vx = start_x + len(minus_btn.text) + 4
    stdscr.addstr(vol_line, vx, vol_str)

    px = vx + len(vol_str) + 4
    color = curses.color_pair(4 if plus_btn.hover else 5)
    stdscr.addstr(vol_line, px, f" {plus_btn.text} ", color)
    plus_btn.set_position(px, vol_line, width=len(plus_btn.text) + 2)

    stdscr.noutrefresh()
    curses.doupdate()

def main(stdscr):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(5, curses.COLOR_WHITE, -1)
    curses.init_pair(6, curses.COLOR_RED, -1)
    curses.init_pair(7, curses.COLOR_WHITE, -1)

    stdscr.nodelay(True)
    stdscr.timeout(50)
    curses.mousemask(-1)

    bars_count = 50
    cava = CavaReader(bars_count)
    cava.start()

    volume = get_volume()
    track = get_current_track()
    last_update = 0

    max_track_len = 30
    scroll_delay = 0.3
    scroll_pause = 2.0
    scroll_index = 0
    scroll_timer = time.time()
    scrolling = False

    buttons = [
        Button("<", lambda: run_async(playerctl_cmd, "previous")),
        Button("TRACK", lambda: run_async(playerctl_cmd, "play-pause")),
        Button(">", lambda: run_async(playerctl_cmd, "next")),
        # Обновляем громкость в интерфейсе сразу после нажатия
        Button("  -  ", lambda: run_async(lambda: (set_volume(volume - 5)))),
        Button("  +  ", lambda: run_async(lambda: (set_volume(volume + 5)))),
    ]

    try:
        while True:
            now = time.time()
            # Обновляем состояние чаще (раз в 0.5 сек), чтобы громкость не лагала
            if now - last_update > 0.5:
                volume = get_volume()
                track = get_current_track()
                last_update = now

            if len(track) > max_track_len:
                if not scrolling:
                    if time.time() - scroll_timer > scroll_pause:
                        scrolling = True
                        scroll_timer = time.time()
                else:
                    if time.time() - scroll_timer > scroll_delay:
                        scroll_index = (scroll_index + 1) % (len(track) + 3)
                        scroll_timer = time.time()
            else:
                scroll_index = 0
                scrolling = False

            bars = cava.get_bars()
            draw_ui(stdscr, bars, volume, track, buttons, scroll_index, max_track_len)

            try:
                key = stdscr.getch()
            except curses.error:
                key = None

            if key == curses.KEY_MOUSE:
                try:
                    _, mx, my, _, bstate = curses.getmouse()
                    if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED | curses.BUTTON1_DOUBLE_CLICKED):
                        for b in buttons:
                            if b.contains(mx, my):
                                b.callback()
                                # Костыль для мгновенного отклика UI на громкость
                                if "+" in b.text: volume = min(100, volume + 5)
                                if "-" in b.text: volume = max(0, volume - 5)
                                time.sleep(0.1)
                                break
                    
                    for b in buttons:
                        b.hover = b.contains(mx, my)
                except Exception:
                    pass
            elif key == curses.KEY_LEFT:
                bars_count = max(5, bars_count - 5)
                cava.stop()
                cava = CavaReader(bars_count)
                cava.start()
            elif key == curses.KEY_RIGHT:
                bars_count = min(200, bars_count + 5)
                cava.stop()
                cava = CavaReader(bars_count)
                cava.start()
            elif key in (ord('q'), ord('Q'), 27):
                break

    finally:
        cava.stop()

if __name__ == "__main__":
    if is_termux():
        os.environ.setdefault("TERM", "xterm-256color")
        os.environ.setdefault("NCURSES_NO_UTF8_ACS", "1")
    curses.wrapper(main)
