#!/usr/bin/env python3
"""AnberHex — konwerter systemów liczbowych (HEX ↔ DEC) dla Anbernic RG40XX V.

Przelicza liczby z systemu szesnastkowego (HEX, base-16) na dziesiętny
(DEC, base-10 — powszechnie używany w Polsce) i odwrotnie. Pokazuje też
zapis dwójkowy (BIN) i ósemkowy (OCT).

Sterowanie (pad RG40XX V):
  D-pad ←/→/↑/↓   ruch po klawiaturze cyfr (podświetlenie)
  A               wstaw podświetloną cyfrę
  B               skasuj ostatnią cyfrę (backspace)
  Y               wyczyść całość
  X               przełącz kierunek (HEX→DEC / DEC→HEX)
  START           wstaw podświetloną cyfrę (alias A)
  MENU            wyjście
  POWER           ekran off/on (bez zamykania apki)

Wzorzec SDL2+PIL+evdev jak AnberMon/AnberCC (NIE SDL_INIT_JOYSTICK — grabuje
event1; PYSDL2_DLL_PATH ustawiony przez wrapper .sh).
"""
import os, sys, time, select, ctypes
from pathlib import Path

# ── Logika konwersji w hexconv.py (testowalna bez SDL, pytest + CI) ───────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hexconv import (HEX_DIGITS, DEC_DIGITS, MAX_LEN,
                     parse_value, group, conversions, derivation, _selftest)

if __name__ == '__main__' and '--selftest' in sys.argv:
    raise SystemExit(_selftest())

# ── Część GUI (importuje SDL dopiero gdy nie selftest) ────────────────────────
os.environ.pop('SDL_VIDEODRIVER', None)
import sdl2
from PIL import Image, ImageDraw, ImageFont

W, H = 640, 480
FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'

BG    = (10,  12,  20,  255)
FG    = (210, 220, 230, 255)
ACC   = (80,  180, 255, 255)
GRN   = (90,  225, 120, 255)
YEL   = (255, 210, 60,  255)
DIM   = (95,  105, 120, 255)
SEP   = (40,  50,  65,  255)
HILITE= (255, 200, 70,  255)
KEYBG = (28,  34,  48,  255)
KEYSEL= (60,  90,  140, 255)

# evdev (event1 = ANBERNIC-keys + D-pad)
EV_KEY, EV_ABS = 1, 3
BTN_A, BTN_B, BTN_X, BTN_START = 304, 305, 307, 315
# Y: na RG40XX V fizyczny przycisk Y wysyła 306 (BTN_C), nie 308 (BTN_WEST) —
# potwierdzone keylogiem. Bindujemy oba dla odporności na różnice egzemplarzy.
BTN_Y_CODES = {306, 308}
MENU_KEYS = {354, 316}
ABS_X, ABS_Y = 16, 17
POWER_KEY = 116
FB_BLANK  = '/sys/class/graphics/fb0/blank'


class HexApp:
    def __init__(self):
        self.mode = 'H2D'          # HEX→DEC domyślnie
        self.inp  = ''
        self.sel  = 0
        self.dirty = True
        self._dbg = open('/mnt/data/anberhex_debug.log', 'a')
        self._dbg.write(f'\n=== START {time.strftime("%H:%M:%S")} ===\n'); self._dbg.flush()

        sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_EVENTS)
        self.win = sdl2.SDL_CreateWindow(
            b"AnberHex", sdl2.SDL_WINDOWPOS_UNDEFINED, sdl2.SDL_WINDOWPOS_UNDEFINED,
            0, 0, sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP | sdl2.SDL_WINDOW_SHOWN)
        self.ren = sdl2.SDL_CreateRenderer(self.win, -1, sdl2.SDL_RENDERER_SOFTWARE) \
                   or sdl2.SDL_CreateRenderer(self.win, -1, 0)

        self.img  = Image.new('RGBA', (W, H), BG)
        self.draw = ImageDraw.Draw(self.img)
        self.f_sm = ImageFont.truetype(FONT_PATH, 14)
        self.f_md = ImageFont.truetype(FONT_PATH, 18)
        self.f_lg = ImageFont.truetype(FONT_PATH, 26)
        self.f_xl = ImageFont.truetype(FONT_PATH, 40)
        self.f_key= ImageFont.truetype(FONT_PATH, 22)
        self.f_der= ImageFont.truetype(FONT_PATH, 13)   # panel "DZIAŁANIE"
        self._tex = None

        # evdev event1 (D-pad + przyciski) — grab z fallbackiem no-grab
        self._gp = None
        try:
            import evdev
            self._gp = evdev.InputDevice('/dev/input/event1')
            self._gp.grab()
            while select.select([self._gp.fd], [], [], 0)[0]:
                self._gp.read()
        except Exception as e:
            self._dbg.write(f'evdev grab FAIL ({e}), retry no-grab\n'); self._dbg.flush()
            try:
                import evdev as _ev
                self._gp = _ev.InputDevice('/dev/input/event1')
            except Exception as e2:
                self._dbg.write(f'evdev FAIL: {e2}\n'); self._dbg.flush()
                self._gp = None

        # event0 = POWER → toggle ekranu
        self._pwr = None
        self._screen_off = False
        try:
            import evdev as _ev2
            self._pwr = _ev2.InputDevice('/dev/input/event0')
            self._pwr.grab()
        except Exception:
            self._pwr = None

    # ── klawiatura cyfr ──────────────────────────────────────────────────────
    def palette(self):
        return HEX_DIGITS if self.mode == 'H2D' else DEC_DIGITS

    def cols(self):
        return 8 if self.mode == 'H2D' else 5   # HEX: 2×8, DEC: 2×5

    def _move(self, dx, dy):
        pal = self.palette(); n = len(pal); c = self.cols()
        if dx:
            self.sel = (self.sel + dx) % n
        if dy:
            self.sel = (self.sel + dy * c) % n
        self.dirty = True

    # ── akcje ────────────────────────────────────────────────────────────────
    def _append(self):
        if len(self.inp) < MAX_LEN:
            self.inp += self.palette()[self.sel]
            self.dirty = True

    def _backspace(self):
        self.inp = self.inp[:-1]; self.dirty = True

    def _clear(self):
        self.inp = ''; self.dirty = True

    def _toggle_mode(self):
        # Przenieś bieżącą wartość do inputu w bazie NOWEGO trybu źródłowego,
        # by od razu zobaczyć drogę odwrotną (HEX→DEC ↔ DEC→HEX tej samej liczby).
        v = parse_value(self.inp, self.mode)
        self.mode = 'D2H' if self.mode == 'H2D' else 'H2D'
        if v is None:
            self.inp = ''
        else:
            self.inp = format(v, 'X') if self.mode == 'H2D' else str(v)
        self.sel = min(self.sel, len(self.palette()) - 1)
        self.dirty = True

    def _toggle_screen(self):
        try:
            self._screen_off = not self._screen_off
            Path(FB_BLANK).write_text('4' if self._screen_off else '0')
        except Exception:
            pass

    # ── render ───────────────────────────────────────────────────────────────
    def _t(self, x, y, txt, font, color):
        self.draw.text((x, y), txt, font=font, fill=color)

    @staticmethod
    def _wrap(text, maxchars):
        """Zawijanie po spacjach do maxchars znaków (zachowuje człony ' + ')."""
        out, cur = [], ''
        for w in text.split(' '):
            if cur and len(cur) + 1 + len(w) > maxchars:
                out.append(cur); cur = w
            else:
                cur = w if not cur else cur + ' ' + w
        if cur:
            out.append(cur)
        return out

    def render(self):
        d = self.draw
        d.rectangle([(0, 0), (W, H)], fill=BG)

        src, dst = ('HEX', 'DEC') if self.mode == 'H2D' else ('DEC', 'HEX')
        src_base = '16' if src == 'HEX' else '10'
        dst_base = '10' if dst == 'DEC' else '16'

        # Tytuł
        self._t(16, 10, 'AnberHex', self.f_lg, ACC)
        self._t(200, 22, 'konwerter systemów liczbowych', self.f_sm, DIM)

        # Tryb
        self._t(16, 50, f'TRYB:  {src} (base-{src_base})  →  {dst} (base-{dst_base})',
                self.f_md, GRN)
        d.line([(0, 78), (W, 78)], fill=SEP, width=1)

        # Wejście
        self._t(16, 88, f'WEJŚCIE ({src}):', self.f_sm, DIM)
        cur = self.inp if self.inp else '_'
        self._t(16, 104, cur, self.f_lg, YEL)

        # Wynik
        conv = conversions(self.inp, self.mode)
        self._t(16, 150, f'WYNIK ({dst}):', self.f_sm, DIM)
        if conv is None:
            big = '—' if not self.inp else 'błąd'
            self._t(16, 168, big, self.f_xl, DIM if not self.inp else (235, 90, 90, 255))
        else:
            primary = conv['dec'] if dst == 'DEC' else conv['hex']
            self._t(16, 166, primary, self.f_xl, FG)
            # dodatkowe systemy
            yy = 224
            self._t(16, yy, f"DEC:  {conv['dec']}", self.f_sm, FG); yy += 18
            self._t(16, yy, f"HEX:  {conv['hex']}", self.f_sm, FG); yy += 18
            self._t(16, yy, f"BIN:  {conv['bin']}", self.f_sm, FG); yy += 18
            self._t(16, yy, f"OCT:  {conv['oct']}", self.f_sm, FG)

        # Panel DZIAŁANIE (prawa kolumna) — pełny zapis przeliczenia
        dx = 322
        d.line([(dx - 10, 84), (dx - 10, 296)], fill=SEP, width=1)
        self._t(dx, 88, f'DZIAŁANIE  ({src}→{dst}):', self.f_sm, ACC)
        deriv = derivation(self.inp, self.mode)
        dy = 112
        if not deriv:
            self._t(dx, dy, '—  (wpisz wartość)', self.f_der, DIM)
        else:
            last_i = len(deriv) - 1
            for i, ln in enumerate(deriv):
                col = YEL if ln.startswith('wzór') else (GRN if i == last_i else FG)
                for seg in self._wrap(ln, 40):
                    self._t(dx, dy, seg, self.f_der, col); dy += 17
                    if dy > 290:
                        break
                if dy > 290:
                    break

        # Klawiatura cyfr
        d.line([(0, 300), (W, 300)], fill=SEP, width=1)
        pal = self.palette(); c = self.cols()
        kx0, ky0, kw, kh, gap = 16, 312, 56, 38, 8
        for i, ch in enumerate(pal):
            row, col = divmod(i, c)
            x = kx0 + col * (kw + gap)
            y = ky0 + row * (kh + gap)
            selected = (i == self.sel)
            d.rectangle([(x, y), (x + kw, y + kh)],
                        fill=KEYSEL if selected else KEYBG,
                        outline=HILITE if selected else SEP, width=2 if selected else 1)
            tw = d.textlength(ch, font=self.f_key)
            self._t(x + (kw - tw) / 2, y + 6, ch, self.f_key,
                    HILITE if selected else FG)

        # Stopka — sterowanie
        self._t(16, H - 22,
                'A wstaw   B usuń   Y wyczyść   X kierunek   MENU wyjście',
                self.f_sm, DIM)

        # blit
        raw = self.img.tobytes()
        surf = sdl2.SDL_CreateRGBSurfaceWithFormatFrom(raw, W, H, 32, W*4,
                                                       sdl2.SDL_PIXELFORMAT_RGBA32)
        if self._tex:
            sdl2.SDL_DestroyTexture(self._tex)
        self._tex = sdl2.SDL_CreateTextureFromSurface(self.ren, surf)
        sdl2.SDL_FreeSurface(surf)
        sdl2.SDL_RenderClear(self.ren)
        sdl2.SDL_RenderCopy(self.ren, self._tex, None, None)
        sdl2.SDL_RenderPresent(self.ren)
        self.dirty = False

    # ── pętla ────────────────────────────────────────────────────────────────
    def run(self):
        ev = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(ctypes.byref(ev)):
            pass
        start_ms = sdl2.SDL_GetTicks()
        GUARD_MS = 1500   # ignoruj MENU z dmenu przez 1.5 s
        last_blank_re = 0

        while True:
            now = sdl2.SDL_GetTicks()
            guard = (now - start_ms) < GUARD_MS

            if self._screen_off and now - last_blank_re >= 200:
                try: Path(FB_BLANK).write_text('4')
                except Exception: pass
                last_blank_re = now

            if self.dirty and not self._screen_off:
                self.render()

            # drenaż eventów SDL (BT klawiatura → ignorujemy, ale czyścimy quit)
            while sdl2.SDL_PollEvent(ctypes.byref(ev)):
                if ev.type == sdl2.SDL_QUIT and not guard:
                    self.quit(); return

            # evdev pad
            if self._gp:
                if select.select([self._gp.fd], [], [], 0)[0]:
                    for e in self._gp.read():
                        if e.type == EV_KEY and e.value == 1:
                            if e.code in MENU_KEYS and not guard:
                                self.quit(); return
                            elif e.code in (BTN_A, BTN_START):
                                self._append()
                            elif e.code == BTN_B:
                                self._backspace()
                            elif e.code in BTN_Y_CODES:
                                self._clear()
                            elif e.code == BTN_X:
                                self._toggle_mode()
                        elif e.type == EV_ABS:
                            if e.code == ABS_X and e.value != 0:
                                self._move(1 if e.value > 0 else -1, 0)
                            elif e.code == ABS_Y and e.value != 0:
                                self._move(0, 1 if e.value > 0 else -1)

            if self._pwr:
                if select.select([self._pwr.fd], [], [], 0)[0]:
                    for e in self._pwr.read():
                        if e.type == EV_KEY and e.code == POWER_KEY and e.value == 1 and not guard:
                            self._toggle_screen()

            sdl2.SDL_Delay(16)

    def quit(self):
        try:
            if self._gp: self._gp.ungrab()
        except Exception: pass
        try:
            if self._pwr: self._pwr.ungrab()
        except Exception: pass
        try:
            Path(FB_BLANK).write_text('0')
        except Exception: pass
        sdl2.SDL_Quit()


if __name__ == '__main__':
    HexApp().run()
