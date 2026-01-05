import os
import sys
import math
import random
from dataclasses import dataclass
from collections import deque
from array import array
from typing import List, Optional, Tuple, Dict, Any

import pygame


# ============================================================
# 0) Helpers
# ============================================================

def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# ============================================================
# 1) Constants + Runtime Config
# ============================================================

@dataclass(frozen=True)
class Const:
    # Render (low-res internal buffer for speed)
    RENDER_W: int = 320
    RENDER_H: int = 180
    FPS: int = 60

    # Music / audio
    MENU_MUSIC_FILE: str = "audio/menu.wav"
    AMBIENT_FILE: str = "audio/ambient.wav"
    SCREAM_FILE: str = "audio/scream.wav"
    END_FILE: str = "audio/end.wav"
    VICTORY_FILE: str = "audio/victory.wav"
    UI_CLICK_FILE: str = "audio/ui_click.wav"
    UI_HOVER_FILE: str = "audio/ui_hover.wav"
    SEAL_PICKUP_FILE: str = "audio/seal_pickup.wav"

    # Gameplay
    MOVE_SPEED: float = 2.6
    RUN_MULT: float = 1.75
    ROT_SPEED_KEYS: float = 2.2
    MOUSE_SENS: float = 0.0025
    PLAYER_RADIUS: float = 0.28

    # Camera / atmosphere
    FOV_PLANE: float = 0.66
    FOG_STRENGTH: float = 0.055
    CEIL_COLOR: Tuple[int, int, int] = (205, 195, 120)
    FLOOR_COLOR: Tuple[int, int, int] = (115, 105, 75)

    # Textures / resources
    TEXTURE_SIZE: int = 256
    MONSTER_FILE: str = "img/trush.jpg"
    END_IMG: str = "img/end.jpg"
    VICTORY_IMG: str = "img/victory.jpg"
    HEART_IMG: str = "img/heart.png"
    ZACHET_IMG: str = "img/zachetka.png"
    DOOR_IMG: str = "img/door.png"
    LEV_IMG: str = "img/Lev.jpg"
    PRAV_IMG: str = "img/Prav.jpg"

    # Monster
    MONSTER_SPAWN_DELAY: float = 1.0
    KILL_DIST: float = 0.65

    # Tunnel distance / audio curve
    REPLAN_INTERVAL: float = 0.12
    SOUND_AUDIBLE_CELLS: int = 22
    SOUND_CURVE: float = 0.60

    # Wall anti-lag
    MIN_WALL_DIST: float = 0.18
    MAX_LINEHEIGHT_MULT: int = 4

    # UI noise
    NOISE_DOTS: int = 80


C = Const()


@dataclass
class RuntimeConfig:
    fullscreen: bool = True           # <- по умолчанию: во весь экран
    window_size: Tuple[int, int] = (960, 540)
    invert_mouse_x: bool = False

    music_volume: float = 0.1  
    sfx_volume: float = 1.00

    # список разрешений для оконного режима
    resolutions: Tuple[Tuple[int, int], ...] = (
        (960, 540),
        (1280, 720),
        (1600, 900),
        (1920, 1080),
    )

    def res_index(self) -> int:
        try:
            return self.resolutions.index(self.window_size)
        except ValueError:
            return 0

    def set_res_index(self, idx: int) -> None:
        idx = idx % len(self.resolutions)
        self.window_size = self.resolutions[idx]


# ============================================================
# 1.5) Map definitions
# ============================================================

@dataclass(frozen=True)
class MapSpec:
    grid: List[str]
    wrap_portals: Tuple[Tuple[str, float, float], ...] = tuple()


BASE_MAP_VARIANTS: Tuple[MapSpec, ...] = (
    MapSpec(
        grid=[
            "111111011111111",  # <- дырка сверху (x=6)
            "100000000100001",
            "101111110101101",
            "101000010101001",
            "101011010101101",
            "101010010001001",
            "101010011101101",
            "101000000001001",
            "101111011101101",
            "100000010000001",
            "111111011111111",  # <- дырка снизу (x=6)
        ],
        wrap_portals=(("N", 6.0, 7.0), ("S", 6.0, 7.0)),  # <- сверху<->снизу
    ),
    MapSpec(
        grid=[
            "1111111111111111111111111111111",
            "1000000000000000000000000000001",
            "1001110111110111110111110111001",
            "1000101010101010101010101010001",
            "1000000000000000000000000000001",
            "1000000000000000000000000000001",
            "1001110111111111110111110111001",
            "1000010000001000000100000000001",
            "1000010000001000000100000000001",
            "1111111111101010101111111111111",
            "1001110111110111110111110111001",
            "1000010000001000000100000000001",
            "1000010000001000000100000000001",
            "1000010000001000000100000000001",
            "1001110111110111110111110111001",
            "1000101010101010101010101010001",
            "1000000000000000000000000000001",
            "1000000000000000000000000000001",
            "1111111111111111111111111111111",
        ],
    ),
    MapSpec(
        grid=[
            "1111111111111111111111111111111",
            "1010000100001001010000100001001",
            "1010000100001000010000100001001",
            "1011111111111101111110111111001",
            "1000000000000000000000000000001",
            "1010000100001000010000100001001",
            "1010000100001000010000100001001",
            "1010000100001000010000100001001",
            "1001111011000001000000111111001",
            "1010000100000001000000100001001",
            "1010000100001111111000100001001",
            "1010000100000001000000100001001",
            "1000000000000001000000000000001",
            "1011111111111101111110111111001",
            "1010000100001000010000100001001",
            "1010000100001000010000100001001",
            "1000000000000000000000000000001",
            "1010000100001000010000100001001",
            "1010000100001000010000100001001",
            "1010000100001001010000100001001",
            "1111111111111111111111111111111",
        ],
    ),
    MapSpec(
        grid=[
            "111111100000111111",
            "100000000000000001",
            "101111010111110101",
            "101001010100010101",
            "101001010100010101",
            "101001010111010101",
            "101001010001010101",
            "101001010001010101",
            "100001000001000001",
            "101001011111010101",
            "101001000000010101",
            "101001111110010101",
            "101000000010010101",
            "101111110010010101",
            "100000000000000001",
            "111111100000111111",
        ],
        wrap_portals=(("N", 7.5, 10.5), ("S", 7.5, 10.5)),
    ),
    MapSpec(
        grid=[
            "111111111111111111111111111111111",
            "100100000001000000010000000100001",
            "101110001001100010011000100110101",
            "100100000001000000010000000100001",
            "100100000001000000010000000100001",
            "100011001000100010001000100110001",
            "100100000001000000010000000100001",
            "100100000001000000000000000100001",
            "100110001001100000001000100110001",
            "111111000001000000000000000111111",
            "100000000000000000000000000000001",
            "100110001001100010011100100110001",
            "100100000001000000010000000100001",
            "100100000001000000010000000100001",
            "100110001001101010111000100110001",
            "100000000000000000000000000000001",
            "100100000001000000010000000100001",
            "100100000001000000010000000100001",
            "111111111111111111111111111111111",
        ],
    ),
)


def _odd(n: int) -> int:
    return n if (n % 2 == 1) else n + 1


def generate_maze_grid(w: int, h: int,
                       loop_chance: float = 0.07,
                       room_attempts: int = 22) -> List[str]:
    w = _odd(max(w, 25))
    h = _odd(max(h, 25))

    g = [["1"] * w for _ in range(h)]

    # DFS/backtracker: пути шириной 1 клетка, стены тоже 1 клетка
    sx, sy = 1, 1
    g[sy][sx] = "0"
    stack = [(sx, sy)]
    dirs = [(2, 0), (-2, 0), (0, 2), (0, -2)]

    while stack:
        x, y = stack[-1]
        neigh = []
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            if 1 <= nx < w - 1 and 1 <= ny < h - 1 and g[ny][nx] == "1":
                neigh.append((nx, ny, dx, dy))

        if neigh:
            nx, ny, dx, dy = random.choice(neigh)
            g[y + dy // 2][x + dx // 2] = "0"
            g[ny][nx] = "0"
            stack.append((nx, ny))
        else:
            stack.pop()

    # “комнатки” чтобы лабиринт был менее “ниточный”
    for _ in range(room_attempts):
        rw = random.randrange(3, 8)
        rh = random.randrange(3, 8)
        x0 = random.randrange(1, w - rw - 1)
        y0 = random.randrange(1, h - rh - 1)
        for yy in range(y0, y0 + rh):
            for xx in range(x0, x0 + rw):
                g[yy][xx] = "0"

    # петли (убираем часть стен, чтобы было больше вариантов путей)
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if g[y][x] != "1":
                continue
            if random.random() > loop_chance:
                continue
            if g[y][x - 1] == "0" and g[y][x + 1] == "0":
                g[y][x] = "0"
            elif g[y - 1][x] == "0" and g[y + 1][x] == "0":
                g[y][x] = "0"

    # жёсткая рамка из стен
    for x in range(w):
        g[0][x] = "1"
        g[h - 1][x] = "1"
    for y in range(h):
        g[y][0] = "1"
        g[y][w - 1] = "1"

    # --- убираем изолированные "острова" (иначе спавн может попасть в камеру без выходов) ---
    dirs4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    start = None
    for yy in range(1, h - 1):
        for xx in range(1, w - 1):
            if g[yy][xx] == "0":
                start = (xx, yy)
                break
        if start:
            break

    if start:
        q = deque([start])
        seen = {start}
        while q:
            x, y = q.popleft()
            for dx, dy in dirs4:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and g[ny][nx] == "0" and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    q.append((nx, ny))

        for yy in range(1, h - 1):
            for xx in range(1, w - 1):
                if g[yy][xx] == "0" and (xx, yy) not in seen:
                    g[yy][xx] = "1"

    return ["".join(row) for row in g]


def generate_maze_spec(min_size: int = 45, max_size: int = 65) -> MapSpec:
    w = _odd(random.randrange(min_size, max_size + 1))
    h = _odd(random.randrange(min_size, max_size + 1))
    return MapSpec(grid=generate_maze_grid(w, h))


# Добавим несколько больших карт + оставим твои ручные варианты
MAP_VARIANTS: Tuple[MapSpec, ...] = BASE_MAP_VARIANTS + tuple(generate_maze_spec() for _ in range(6))

# ============================================================
# 2) World (Map + collision)
# ============================================================

class World:
    def __init__(self, map_spec: MapSpec) -> None:
        self.MAP = [list(row) for row in map_spec.grid]
        self.h = len(self.MAP)
        self.w = len(self.MAP[0])
        self.wrap_portals = list(map_spec.wrap_portals)

    def portal_allows(self, direction: str, coord: float) -> bool:
        for d, a, b in self.wrap_portals:
            if d == direction and a <= coord <= b:
                return True
        return False

    def cell_at(self, mx: int, my: int) -> str:
        if 0 <= mx < self.w and 0 <= my < self.h:
            return self.MAP[my][mx]
        return "1"

    def _snap_to_open(self, x: float, y: float) -> Tuple[float, float]:
        mx, my = int(x), int(y)
        if 0 <= mx < self.w and 0 <= my < self.h and not self.is_blocking_cell(mx, my):
            return x, y

        for rad in range(1, 4):
            for dy in range(-rad, rad + 1):
                for dx in range(-rad, rad + 1):
                    nx, ny = mx + dx, my + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h and not self.is_blocking_cell(nx, ny):
                        return nx + 0.5, ny + 0.5
        return x, y

    def is_wall_cell(self, mx: int, my: int) -> bool:
        return self.cell_at(mx, my) == "1"

    def is_blocking_cell(self, mx: int, my: int) -> bool:
        cell = self.cell_at(mx, my)
        return cell in ("1", "D")

    def is_wall_at(self, x: float, y: float) -> bool:
        return self.is_blocking_cell(int(x), int(y))

    def collides_circle(self, x: float, y: float, r: float) -> bool:
        # 4 угла "круга" (достаточно надёжно для grid-карт)
        for ox in (-r, r):
            for oy in (-r, r):
                if self.is_blocking_cell(int(x + ox), int(y + oy)):
                    return True
        return False

    def apply_wrap(self, player: "Player") -> None:
        if not self.wrap_portals:
            return

        edge = 0.35
        wrapped = False

        if player.y < edge and self.portal_allows("N", player.x):
            player.y += (self.h - 1)
            wrapped = True
        elif player.y > (self.h - edge) and self.portal_allows("S", player.x):
            player.y -= (self.h - 1)
            wrapped = True

        if player.x < edge and self.portal_allows("W", player.y):
            player.x += (self.w - 1)
            wrapped = True
        elif player.x > (self.w - edge) and self.portal_allows("E", player.y):
            player.x -= (self.w - 1)
            wrapped = True

        if wrapped:
            player.x, player.y = self._snap_to_open(player.x, player.y)


# ============================================================
# 3) Backrooms wall texture (procedural)
# ============================================================

def make_backrooms_wall_texture(size: int = 256) -> pygame.Surface:
    surf = pygame.Surface((size, size))
    surf.fill((210, 198, 120))

    for x in range(0, size, 18):
        col = (
            200 + random.randint(-8, 8),
            190 + random.randint(-8, 8),
            115 + random.randint(-8, 8),
        )
        pygame.draw.rect(surf, col, (x, 0, 6, size))

    for _ in range(1400):
        x = random.randrange(size)
        y = random.randrange(size)
        d = random.randrange(1, 4)
        c = random.randrange(140, 205)
        surf.fill((c, c - 8, c - 40), (x, y, d, d))

    for _ in range(9000):
        x = random.randrange(size)
        y = random.randrange(size)
        c = random.randrange(160, 220)
        surf.set_at((x, y), (c, c - 10, c - 55))

    return surf.convert()


# ============================================================
# 4) Audio (drone synth + scream.mp3)
# ============================================================

class AudioSystem:
    def __init__(self) -> None:
        self.enabled = True

        self.drone: Optional[pygame.mixer.Sound] = None
        self.drone_channel: Optional[pygame.mixer.Channel] = None
        self.drone_dynamic = 0.10  # базовый уровень (до умножения на sfx_volume)

        self.ambient_sound: Optional[pygame.mixer.Sound] = None
        self.ambient_channel: Optional[pygame.mixer.Channel] = None

        self.scream_sound: Optional[pygame.mixer.Sound] = None
        self.scream_channel: Optional[pygame.mixer.Channel] = None
        self.use_music_for_scream = False
        self.scream_path = ""

        self.menu_path = ""
        self.music_playing = False

        self.music_volume = 0.65
        self.sfx_volume = 1.00

        self.ui_hover_sound: Optional[pygame.mixer.Sound] = None
        self.ui_click_sound: Optional[pygame.mixer.Sound] = None
        self.pickup_sound: Optional[pygame.mixer.Sound] = None
        self.victory_sound: Optional[pygame.mixer.Sound] = None
        self.end_sound: Optional[pygame.mixer.Sound] = None

    @staticmethod
    def _load_sound(path: str) -> Optional[pygame.mixer.Sound]:
        if not os.path.exists(path):
            return None
        try:
            return pygame.mixer.Sound(path)
        except Exception:
            return None

    def init(self) -> None:
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()
        except Exception:
            self.enabled = False
            return

        self.drone_channel = pygame.mixer.Channel(0)
        self.scream_channel = pygame.mixer.Channel(1)
        self.ambient_channel = pygame.mixer.Channel(2)

        # UI can reuse an auto-assigned channel

        self.drone = self._make_drone()
        self.ambient_sound = self._load_sound(resource_path(C.AMBIENT_FILE))
        self.scream_path = resource_path(C.SCREAM_FILE)
        self.menu_path = resource_path(C.MENU_MUSIC_FILE)

        self.ui_hover_sound = self._load_sound(resource_path(C.UI_HOVER_FILE))
        self.ui_click_sound = self._load_sound(resource_path(C.UI_CLICK_FILE))
        self.pickup_sound = self._load_sound(resource_path(C.SEAL_PICKUP_FILE))
        self.victory_sound = self._load_sound(resource_path(C.VICTORY_FILE))
        self.end_sound = self._load_sound(resource_path(C.END_FILE))

        self._load_scream()

    def apply_volumes(self, music_volume: float, sfx_volume: float) -> None:
        self.music_volume = clamp(music_volume, 0.0, 1.0)
        self.sfx_volume = clamp(sfx_volume, 0.0, 1.0)

        # music
        if self.enabled:
            try:
                pygame.mixer.music.set_volume(self.music_volume)
            except Exception:
                pass

        # drone channel volume обновится при set_game_drone_dynamic
        self.set_game_drone_dynamic(self.drone_dynamic)

        if self.ambient_channel is not None:
            self.ambient_channel.set_volume(0.25 * self.sfx_volume)
        if self.ambient_sound is not None:
            try:
                self.ambient_sound.set_volume(0.25 * self.sfx_volume)
            except Exception:
                pass

        # scream channel
        if self.scream_channel is not None:
            self.scream_channel.set_volume(self.sfx_volume)

        # ui
        if self.ui_hover_sound is not None:
            self.ui_hover_sound.set_volume(self.sfx_volume)
        if self.ui_click_sound is not None:
            self.ui_click_sound.set_volume(self.sfx_volume)
        if self.pickup_sound is not None:
            self.pickup_sound.set_volume(self.sfx_volume)
        if self.victory_sound is not None:
            self.victory_sound.set_volume(self.sfx_volume)
        if self.end_sound is not None:
            self.end_sound.set_volume(self.sfx_volume)

    def play_ui_hover(self) -> None:
        self._play_sfx(self.ui_hover_sound)

    def play_ui_click(self) -> None:
        self._play_sfx(self.ui_click_sound)

    def play_pickup(self) -> None:
        self._play_sfx(self.pickup_sound)

    def play_victory(self) -> None:
        self._play_sfx(self.victory_sound)

    def play_end(self) -> None:
        self._play_sfx(self.end_sound)

    def _play_sfx(self, snd: Optional[pygame.mixer.Sound]) -> None:
        if not self.enabled or snd is None:
            return
        try:
            snd.set_volume(self.sfx_volume)
            snd.play()
        except Exception:
            return

        # ui
        if self.ui_hover_sound is not None:
            self.ui_hover_sound.set_volume(self.sfx_volume)
        if self.ui_click_sound is not None:
            self.ui_click_sound.set_volume(self.sfx_volume)
        if self.pickup_sound is not None:
            self.pickup_sound.set_volume(self.sfx_volume)
        if self.victory_sound is not None:
            self.victory_sound.set_volume(self.sfx_volume)
        if self.end_sound is not None:
            self.end_sound.set_volume(self.sfx_volume)

    def play_ui_hover(self) -> None:
        self._play_sfx(self.ui_hover_sound)

    def play_ui_click(self) -> None:
        self._play_sfx(self.ui_click_sound)

    def play_pickup(self) -> None:
        self._play_sfx(self.pickup_sound)

    def play_victory(self) -> None:
        self._play_sfx(self.victory_sound)

    def play_end(self) -> None:
        self._play_sfx(self.end_sound)

    def _play_sfx(self, snd: Optional[pygame.mixer.Sound]) -> None:
        if not self.enabled or snd is None:
            return
        try:
            snd.set_volume(self.sfx_volume)
            snd.play()
        except Exception:
            return

        # ui
        if self.ui_hover_sound is not None:
            self.ui_hover_sound.set_volume(self.sfx_volume)
        if self.ui_click_sound is not None:
            self.ui_click_sound.set_volume(self.sfx_volume)

    def play_ui_hover(self) -> None:
        self._play_sfx(self.ui_hover_sound)

    def play_ui_click(self) -> None:
        self._play_sfx(self.ui_click_sound)

    def _play_sfx(self, snd: Optional[pygame.mixer.Sound]) -> None:
        if not self.enabled or snd is None:
            return
        try:
            snd.set_volume(self.sfx_volume)
            snd.play()
        except Exception:
            return

    # ---------- Menu music ----------
    def play_menu_music(self) -> None:
        if not self.enabled:
            return
        if not os.path.exists(self.menu_path):
            return

        # не перезагружать лишний раз
        if self.music_playing:
            return

        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(self.menu_path)
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(-1)  # loop forever
            self.music_playing = True
        except Exception:
            self.music_playing = False

    def stop_menu_music(self) -> None:
        if not self.enabled:
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.music_playing = False

    # ---------- Drone / ambient (game ambience) ----------
    def start_drone(self) -> None:
        if not self.enabled:
            return
        # ambient file has priority; drone is fallback
        if self.ambient_sound is not None and self.ambient_channel is not None:
            if not self.ambient_channel.get_busy():
                self.ambient_channel.play(self.ambient_sound, loops=-1)
            self.ambient_channel.set_volume(0.25 * self.sfx_volume)
            return

        if self.drone is None or self.drone_channel is None:
            return
        if not self.drone_channel.get_busy():
            self.drone_channel.play(self.drone, loops=-1)
        self.set_game_drone_dynamic(self.drone_dynamic)

    def stop_drone(self) -> None:
        if self.ambient_channel is not None:
            self.ambient_channel.stop()
        if self.drone_channel is not None:
            self.drone_channel.stop()

    def set_game_drone_dynamic(self, vol01: float) -> None:
        # vol01 — то, что ты считал по дистанции; сверху умножаем на sfx_volume
        self.drone_dynamic = clamp(vol01, 0.0, 1.0)
        if not self.enabled:
            return
        if self.ambient_channel is not None and self.ambient_channel.get_busy():
            self.ambient_channel.set_volume(0.25 * self.sfx_volume)
            return
        if self.drone_channel is None:
            return
        self.drone_channel.set_volume(self.drone_dynamic * self.sfx_volume)

    # ---------- Scream ----------
    def play_scream(self) -> None:
        if not self.enabled:
            return

        self.stop_drone()
        # если scream пойдёт через music fallback — остановим menu музыку
        if self.use_music_for_scream:
            self.stop_menu_music()

        if not self.use_music_for_scream and self.scream_sound is not None and self.scream_channel is not None:
            self.scream_channel.set_volume(self.sfx_volume)
            self.scream_channel.stop()
            self.scream_channel.play(self.scream_sound)
            return

        # fallback: music (если Sound(mp3) не поддерживается)
        try:
            if os.path.exists(self.scream_path):
                pygame.mixer.music.stop()
                pygame.mixer.music.load(self.scream_path)
                pygame.mixer.music.set_volume(self.sfx_volume)  # важно: это SFX
                pygame.mixer.music.play(0)
        except Exception:
            pass

    def stop_scream(self) -> None:
        if not self.enabled:
            return
        if self.scream_channel is not None:
            self.scream_channel.stop()
        # если scream играл через music — тоже стоп
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.music_playing = False

    # ---------- Internals ----------
    def _make_drone(self, duration: float = 3.5, sr: int = 44100) -> pygame.mixer.Sound:
        n = int(duration * sr)
        samples = array("h")
        for i in range(n):
            t = i / sr
            a = 0.35 * math.sin(2 * math.pi * 48 * t)
            b = 0.20 * math.sin(2 * math.pi * (55 + 2.2 * math.sin(2 * math.pi * 0.35 * t)) * t)
            noise = 0.08 * (random.random() * 2 - 1)
            v = (a + b + noise) * 0.9
            v = clamp(v, -1.0, 1.0)
            samples.append(int(v * 32767))
        snd = pygame.mixer.Sound(buffer=samples.tobytes())
        return snd

    def _load_scream(self) -> None:
        self.use_music_for_scream = False
        self.scream_sound = None

        # try Sound(mp3)
        try:
            if os.path.exists(self.scream_path):
                self.scream_sound = pygame.mixer.Sound(self.scream_path)
                self.use_music_for_scream = False
                return
        except Exception:
            pass

        # fallback: use music
        try:
            if os.path.exists(self.scream_path):
                pygame.mixer.music.load(self.scream_path)
                self.use_music_for_scream = True
        except Exception:
            self.use_music_for_scream = True



# ============================================================
# 5) Pathfinding (BFS distance map)
# ============================================================

DIRS4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def compute_dist_map(
    world: World,
    px: int,
    py: int,
    is_blocking: Optional[Any] = None,
) -> List[List[int]]:
    if is_blocking is None:
        is_blocking = world.is_wall_cell

    dist = [[-1] * world.w for _ in range(world.h)]
    q = deque()
    dist[py][px] = 0
    q.append((px, py))

    while q:
        x, y = q.popleft()
        d = dist[y][x]
        for dx, dy in DIRS4:
            nx, ny = x + dx, y + dy
            if 0 <= nx < world.w and 0 <= ny < world.h and dist[ny][nx] == -1 and not is_blocking(nx, ny):
                dist[ny][nx] = d + 1
                q.append((nx, ny))
    return dist


def pick_next_cell_for_monster(dist: List[List[int]], mx: int, my: int) -> Optional[Tuple[int, int]]:
    best = None
    best_d = 10**9
    for dx, dy in DIRS4:
        nx, ny = mx + dx, my + dy
        if 0 <= ny < len(dist) and 0 <= nx < len(dist[0]):
            d = dist[ny][nx]
            if d != -1 and d < best_d:
                best_d = d
                best = (nx, ny)
    return best


# ============================================================
# 6) Entities
# ============================================================

@dataclass
class Player:
    x: float = 2.5
    y: float = 2.5
    dirx: float = 1.0
    diry: float = 0.0
    planex: float = 0.0
    planey: float = C.FOV_PLANE

    def rotate(self, ang: float) -> None:
        cos_a, sin_a = math.cos(ang), math.sin(ang)
        old_dirx = self.dirx
        self.dirx = self.dirx * cos_a - self.diry * sin_a
        self.diry = old_dirx * sin_a + self.diry * cos_a

        old_planex = self.planex
        self.planex = self.planex * cos_a - self.planey * sin_a
        self.planey = old_planex * sin_a + self.planey * cos_a


@dataclass
class Monster:
    x: float = 0.0
    y: float = 0.0
    active_time: float = 0.0
    next_replan: float = 0.0
    target: Optional[Tuple[float, float]] = None
    tunnel_dist_cells: int = 999


# ============================================================
# 7) Renderer (raycasting + sprite billboard)
# ============================================================

def vignette_surface(w: int, h: int) -> pygame.Surface:
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w / 2, h / 2
    maxd = math.hypot(cx, cy)
    for y in range(h):
        for x in range(w):
            d = math.hypot(x - cx, y - cy) / maxd
            a = int(170 * (d ** 1.8))
            surf.set_at((x, y), (0, 0, 0, a))
    return surf


class Renderer:
    def __init__(
        self,
        screen: pygame.Surface,
        wall_tex: pygame.Surface,
        monster_img: pygame.Surface,
        heart_img: pygame.Surface,
        zachet_img: pygame.Surface,
        door_img: pygame.Surface,
        victory_img: pygame.Surface,
        end_img: pygame.Surface,
    ):
        self.screen = screen
        self.render = pygame.Surface((C.RENDER_W, C.RENDER_H))
        self.wall_tex = wall_tex
        self.monster_img = monster_img
        self.heart_img = heart_img
        self.zachet_img = zachet_img
        self.door_img = door_img
        self.door_overlay = pygame.transform.smoothscale(door_img, (C.TEXTURE_SIZE, C.TEXTURE_SIZE))
        self.door_wall_tex = self.wall_tex.copy()          # фон — стена
        self.door_wall_tex.blit(self.door_overlay, (0, 0)) # дверь поверх стены (alpha ок)
        self.door_tex = self.door_wall_tex
        self.victory_img = victory_img
        self.end_img = end_img
        self._rebuild_overlay()

        self.font = pygame.font.SysFont("consolas", 18)
        self.big_font = pygame.font.SysFont("consolas", 44, bold=True)
        self.logo_font = pygame.font.SysFont("consolas", 74, bold=True)

    def set_screen(self, new_screen: pygame.Surface) -> None:
        self.screen = new_screen
        self._rebuild_overlay()

    def _rebuild_overlay(self) -> None:
        w, h = self.screen.get_size()
        self.vin = vignette_surface(w, h)

    def draw_play(
        self,
        world: World,
        player: Player,
        monsters: List[Monster],
        show_monster: bool,
        is_dead: bool,
        door_pos: Optional[Tuple[float, float]] = None,
        door_plane_pos: Optional[Tuple[float, float]] = None,
        door_orientation: str = "vertical",
        door_open: bool = False,
        zachetki: List[Tuple[float, float]] = [],
        zachet_collected: List[bool] = [],
        lives: int = 3,
        show_minimap: bool = False,
    ) -> None:
        self.render.fill(C.CEIL_COLOR)
        pygame.draw.rect(self.render, C.FLOOR_COLOR, (0, C.RENDER_H // 2, C.RENDER_W, C.RENDER_H // 2))

        zbuffer = [1e9] * C.RENDER_W
        self._cast_walls(world, player, zbuffer)

        if (not door_open) and (door_plane_pos is not None):
            self._draw_door_plane(
                zbuffer,
                player,
                door_plane_pos,
                door_orientation,
                dim=False,
            )

        sprites = []

        # монстры (только активные)
        if show_monster and not is_dead:
            t_now = pygame.time.get_ticks() / 1000.0
            for m in monsters:
                if t_now >= m.active_time:
                    sprites.append(("monster", (m.x, m.y), self.monster_img, False, 1.10))

        # зачётки
        for pos, collected in zip(zachetki, zachet_collected):
            if not collected:
                sprites.append(("zachet", pos, self.zachet_img, False, 1.0))

        # сортировка: дальние -> ближние
        def _dsq(pp: Tuple[float, float]) -> float:
            dx = pp[0] - player.x
            dy = pp[1] - player.y
            return dx * dx + dy * dy

        sprites.sort(key=lambda s: _dsq(s[1]), reverse=True)

        for _, pos, tex, dim, scale in sprites:
            self._draw_billboard(zbuffer, player, pos, tex, dim=dim, scale=scale)


        # upscale to screen
        w, h = self.screen.get_size()
        frame = pygame.transform.scale(self.render, (w, h))
        self.screen.blit(frame, (0, 0))
        self.screen.blit(self.vin, (0, 0))

        # subtle noise
        for _ in range(C.NOISE_DOTS):
            xx = random.randrange(w)
            yy = random.randrange(h)
            c = random.randrange(10, 28)
            self.screen.set_at((xx, yy), (c, c, c))

        if is_dead:
            # persistent screamer until restart
            jump = pygame.transform.scale(self.monster_img, (w, h))
            self.screen.blit(jump, (0, 0))
            txt = self.big_font.render("ПЕРЕСДАЧА!", True, (240, 240, 240))
            self.screen.blit(txt, (w // 2 - txt.get_width() // 2, int(h * 0.26)))
            txt2 = self.font.render("Нажми R чтобы начать заново", True, (240, 240, 240))
            self.screen.blit(txt2, (w // 2 - txt2.get_width() // 2, int(h * 0.38)))
            return

        # HUD (lives + zachetki)
        heart = pygame.transform.smoothscale(self.heart_img, (28, 28))
        for i in range(max(0, lives)):
            self.screen.blit(heart, (12 + i * 32, 12))

        icon = pygame.transform.smoothscale(self.zachet_img, (34, 34))
        total = len(zachet_collected)
        got = sum(1 for c in zachet_collected if c)
        for i in range(total):
            mul = 255 if zachet_collected[i] else 110
            shaded = icon.copy()
            shaded.fill((mul, mul, mul, 255), special_flags=pygame.BLEND_MULT)
            self.screen.blit(shaded, (12 + i * 40, 50))
        if total:
            txt = self.font.render(f"{got}/{total}", True, (230, 230, 230))
            self.screen.blit(txt, (12, 90))

        if show_minimap:
            active_zachetki = [p for p, c in zip(zachetki, zachet_collected) if not c]
            self._draw_minimap(world, player, door_pos, active_zachetki)

    def _draw_minimap(
        self,
        world: World,
        player: Player,
        door_pos: Optional[Tuple[float, float]],
        zachetki: List[Tuple[float, float]],
    ) -> None:
        target = 220
        cell = max(1, min(target // max(world.w, 1), target // max(world.h, 1)))
        map_w = cell * world.w
        map_h = cell * world.h

        surf = pygame.Surface((map_w, map_h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 110))

        for y in range(world.h):
            for x in range(world.w):
                if world.is_wall_cell(x, y):
                    pygame.draw.rect(surf, (35, 35, 35, 230), (x * cell, y * cell, cell, cell))

        if door_pos is not None:
            dx = int(door_pos[0] * cell)
            dy = int(door_pos[1] * cell)
            pygame.draw.circle(surf, (40, 140, 255, 240), (dx, dy), max(2, cell // 2))

        for zachetka_pos in zachetki:
            zx = int(zachetka_pos[0] * cell)
            zy = int(zachetka_pos[1] * cell)
            pygame.draw.circle(surf, (250, 200, 70, 240), (zx, zy), max(2, cell // 2))

        px = int(player.x * cell)
        py = int(player.y * cell)
        pygame.draw.circle(surf, (255, 80, 80, 255), (px, py), max(2, cell // 2))
        dir_len = max(cell, 6)
        pygame.draw.line(
            surf,
            (255, 200, 200, 255),
            (px, py),
            (int(px + player.dirx * dir_len), int(py + player.diry * dir_len)),
            2,
        )

        w, _ = self.screen.get_size()
        self.screen.blit(surf, (w - map_w - 12, 12))

    @staticmethod
    def _text_with_outlines(
        text: str,
        font: pygame.font.Font,
        inner_color: Tuple[int, int, int],
        outline_layers: List[Tuple[Tuple[int, int, int], int]],
    ) -> pygame.Surface:
        base = font.render(text, True, inner_color)
        pad = max((r for _, r in outline_layers), default=0)
        surf = pygame.Surface((base.get_width() + pad * 2, base.get_height() + pad * 2), pygame.SRCALPHA)

        for color, rad in outline_layers:
            outline = font.render(text, True, color)
            offsets = [
                (-rad, 0),
                (rad, 0),
                (0, -rad),
                (0, rad),
                (-rad, -rad),
                (-rad, rad),
                (rad, -rad),
                (rad, rad),
            ]
            for dx, dy in offsets:
                surf.blit(outline, (pad + dx, pad + dy))

        surf.blit(base, (pad, pad))
        return surf

    def draw_menu(
        self,
        title: str,
        items: List[str],
        selected: int,
        hint: str = "",
        famcs_logo: bool = False,
    ) -> List[pygame.Rect]:
        w, h = self.screen.get_size()
        self.screen.fill((10, 10, 10))

        tfont = pygame.font.SysFont("consolas", 46, bold=True)
        mfont = pygame.font.SysFont("consolas", 26)
        sfont = pygame.font.SysFont("consolas", 18)

        title_y = int(h * 0.18)
        if famcs_logo:
            top = tfont.render("ESCAPE FROM", True, (220, 220, 220))
            self.screen.blit(top, (w // 2 - top.get_width() // 2, title_y - 30))

            famcs = self._text_with_outlines(
                "FAMCS",
                self.logo_font,
                (255, 255, 255),
                [((0, 120, 255), 4), ((255, 140, 0), 2)],
            )
            self.screen.blit(famcs, (w // 2 - famcs.get_width() // 2, title_y))
        else:
            t = tfont.render(title, True, (220, 220, 220))
            self.screen.blit(t, (w // 2 - t.get_width() // 2, title_y))

        base_y = int(h * 0.36)
        rects: List[pygame.Rect] = []
        for i, it in enumerate(items):
            col = (255, 235, 120) if i == selected else (170, 170, 170)
            s = mfont.render(it, True, col)
            r = s.get_rect()
            r.center = (w // 2, base_y + i * 40 + 12)
            self.screen.blit(s, r.topleft)
            rects.append(r)

        if hint:
            hh = sfont.render(hint, True, (130, 130, 130))
            self.screen.blit(hh, (w // 2 - hh.get_width() // 2, int(h * 0.88)))

        return rects

    def draw_fullscreen_image(self, img: pygame.Surface, caption: str = "") -> None:
        w, h = self.screen.get_size()
        scaled = pygame.transform.scale(img, (w, h))
        self.screen.blit(scaled, (0, 0))
        if caption:
            txt = self.big_font.render(caption, True, (240, 240, 240))
            self.screen.blit(txt, (w // 2 - txt.get_width() // 2, int(h * 0.82)))


    def _cast_walls(self, world: World, p: Player, zbuffer: List[float]) -> None:
        tex_w, tex_h = self.wall_tex.get_size()
        max_steps = world.w * world.h * 4

        for x in range(C.RENDER_W):
            cameraX = 2.0 * x / C.RENDER_W - 1.0
            rayDirX = p.dirx + p.planex * cameraX
            rayDirY = p.diry + p.planey * cameraX

            mapX = int(p.x)
            mapY = int(p.y)

            deltaDistX = abs(1.0 / rayDirX) if abs(rayDirX) > 1e-12 else 1e30
            deltaDistY = abs(1.0 / rayDirY) if abs(rayDirY) > 1e-12 else 1e30

            if rayDirX < 0:
                stepX = -1
                sideDistX = (p.x - mapX) * deltaDistX
            else:
                stepX = 1
                sideDistX = (mapX + 1.0 - p.x) * deltaDistX

            if rayDirY < 0:
                stepY = -1
                sideDistY = (p.y - mapY) * deltaDistY
            else:
                stepY = 1
                sideDistY = (mapY + 1.0 - p.y) * deltaDistY

            hit = False
            side = 0
            cell_type = "1"
            perp = 1e9

            for _ in range(max_steps):
                if sideDistX < sideDistY:
                    sideDistX += deltaDistX
                    mapX += stepX
                    side = 0
                    traveled = sideDistX - deltaDistX
                else:
                    sideDistY += deltaDistY
                    mapY += stepY
                    side = 1
                    traveled = sideDistY - deltaDistY

                if mapY < 0:
                    x_at = p.x + rayDirX * traveled
                    if world.portal_allows("N", x_at):
                        mapY = world.h - 1
                    else:
                        hit = True
                        cell_type = "1"
                        perp = traveled
                        break
                elif mapY >= world.h:
                    x_at = p.x + rayDirX * traveled
                    if world.portal_allows("S", x_at):
                        mapY = 0
                    else:
                        hit = True
                        cell_type = "1"
                        perp = traveled
                        break

                if mapX < 0:
                    y_at = p.y + rayDirY * traveled
                    if world.portal_allows("W", y_at):
                        mapX = world.w - 1
                    else:
                        hit = True
                        cell_type = "1"
                        perp = traveled
                        break
                elif mapX >= world.w:
                    y_at = p.y + rayDirY * traveled
                    if world.portal_allows("E", y_at):
                        mapX = 0
                    else:
                        hit = True
                        cell_type = "1"
                        perp = traveled
                        break

                cell_type = world.cell_at(mapX, mapY)
                if cell_type in ("1", "D"):
                    hit = True
                    perp = traveled
                    break

            if not hit:
                continue

            perp = max(perp, C.MIN_WALL_DIST)
            zbuffer[x] = perp

            line_h = int(C.RENDER_H / perp)
            line_h = min(line_h, C.RENDER_H * C.MAX_LINEHEIGHT_MULT)

            draw_start = max(0, -line_h // 2 + C.RENDER_H // 2)
            draw_end = min(C.RENDER_H - 1, line_h // 2 + C.RENDER_H // 2)

            if side == 0:
                wallX = p.y + perp * rayDirY
            else:
                wallX = p.x + perp * rayDirX
            wallX -= math.floor(wallX)

            texX = int(wallX * tex_w)
            if side == 0 and rayDirX > 0:
                texX = tex_w - texX - 1
            if side == 1 and rayDirY < 0:
                texX = tex_w - texX - 1
            texX = int(clamp(texX, 0, tex_w - 1))

            visible_h = draw_end - draw_start
            if visible_h <= 0:
                continue

            tex = self.door_wall_tex if cell_type == "D" else self.wall_tex
            col = tex.subsurface((texX, 0, 1, tex_h))
            col_scaled = pygame.transform.scale(col, (1, visible_h))

            shade_mul = 0.78 if side == 1 else 1.0
            fog_factor = math.exp(-C.FOG_STRENGTH * perp * 22.0)
            mul = int(clamp(int(255 * fog_factor * shade_mul), 20, 255))

            col_scaled = col_scaled.copy()
            col_scaled.fill((mul, mul, mul), special_flags=pygame.BLEND_MULT)
            self.render.blit(col_scaled, (x, draw_start))

    def _draw_door_plane(
        self,
        zbuffer: List[float],
        p: Player,
        door_pos: Tuple[float, float],
        orientation: str,
        dim: bool = True,
    ) -> None:
        tex_w, tex_h = self.door_tex.get_size()
        door_x, door_y = door_pos
        half = 0.5
        for x in range(C.RENDER_W):
            cameraX = 2.0 * x / C.RENDER_W - 1.0
            rayDirX = p.dirx + p.planex * cameraX
            rayDirY = p.diry + p.planey * cameraX

            if orientation == "vertical":
                if abs(rayDirX) < 1e-6:
                    continue
                t = (door_x - p.x) / rayDirX
                hit_y = p.y + t * rayDirY
                tex_coord = hit_y - (door_y - half)
            else:
                if abs(rayDirY) < 1e-6:
                    continue
                t = (door_y - p.y) / rayDirY
                hit_x = p.x + t * rayDirX
                tex_coord = hit_x - (door_x - half)

            if t <= 0:
                continue
            if tex_coord < 0 or tex_coord > (half * 2):
                continue

            perp = max(t - 1e-4, 1e-4)
            lineHeight = int(abs(C.RENDER_H / perp))
            lineHeight = int(clamp(lineHeight, 4, C.RENDER_H * C.MAX_LINEHEIGHT_MULT))
            draw_start = -lineHeight // 2 + C.RENDER_H // 2
            draw_end = draw_start + lineHeight
            visible_h = draw_end - draw_start
            if visible_h <= 0:
                continue

            texX = int(clamp(tex_coord / (half * 2) * tex_w, 0, tex_w - 1))
            col = self.door_tex.subsurface((texX, 0, 1, tex_h))
            col_scaled = pygame.transform.scale(col, (1, visible_h))

            shade_mul = 0.85 if orientation == "vertical" else 0.92
            fog_factor = math.exp(-C.FOG_STRENGTH * perp * 22.0)
            mul = int(255 * fog_factor * shade_mul)
            mul = int(clamp(mul, 35 if dim else 80, 255))
            col_scaled = col_scaled.copy()
            col_scaled.fill((mul, mul, mul), special_flags=pygame.BLEND_MULT)

            if perp <= zbuffer[x] + 1e-6:
                self.render.blit(col_scaled, (x, draw_start))

    def _draw_sprite(self, zbuffer: List[float], p: Player, spr_pos: Tuple[float, float]) -> None:
        sprX = spr_pos[0] - p.x
        sprY = spr_pos[1] - p.y

        inv_det = 1.0 / (p.planex * p.diry - p.dirx * p.planey + 1e-9)
        transformX = inv_det * (p.diry * sprX - p.dirx * sprY)
        transformY = inv_det * (-p.planey * sprX + p.planex * sprY)

        if transformY <= 0.06:
            return

        screen_x = int((C.RENDER_W / 2) * (1 + transformX / transformY))

        sprite_h = int(abs(C.RENDER_H / transformY))
        sprite_h = int(clamp(sprite_h, 6, C.RENDER_H * 3))
        sprite_w = sprite_h

        start_y = -sprite_h // 2 + C.RENDER_H // 2
        end_y = start_y + sprite_h
        start_x = -sprite_w // 2 + screen_x
        end_x = start_x + sprite_w

        # clip Y
        clip_sy = max(0, start_y)
        clip_ey = min(C.RENDER_H, end_y)
        if clip_ey <= clip_sy:
            return
        offset_y = clip_sy - start_y
        vis_h = clip_ey - clip_sy

        tex_scaled = pygame.transform.smoothscale(self.monster_img, (sprite_w, sprite_h))

        # fog sprite
        fog_factor = math.exp(-C.FOG_STRENGTH * transformY * 22.0)
        mul = int(255 * fog_factor)
        mul = int(clamp(mul, 35, 255))
        tex_scaled = tex_scaled.copy()
        tex_scaled.fill((mul, mul, mul), special_flags=pygame.BLEND_MULT)

        # clip X
        clip_sx = max(0, start_x)
        clip_ex = min(C.RENDER_W, end_x)

        for stripe in range(clip_sx, clip_ex):
            if transformY >= zbuffer[stripe]:
                continue
            tx = stripe - start_x
            if 0 <= tx < sprite_w:
                col = tex_scaled.subsurface((tx, offset_y, 1, vis_h))
                self.render.blit(col, (stripe, clip_sy))

    def _draw_billboard(
        self,
        zbuffer: List[float],
        p: Player,
        spr_pos: Tuple[float, float],
        tex: pygame.Surface,
        dim: bool = False,
        scale: float = 1.0,
    ) -> None:
        sprX = spr_pos[0] - p.x
        sprY = spr_pos[1] - p.y

        inv_det = 1.0 / (p.planex * p.diry - p.dirx * p.planey + 1e-9)
        transformX = inv_det * (p.diry * sprX - p.dirx * sprY)
        transformY = inv_det * (-p.planey * sprX + p.planex * sprY)

        if transformY <= 0.06:
            return

        screen_x = int((C.RENDER_W / 2) * (1 + transformX / transformY))

        sprite_h = int(abs(C.RENDER_H / transformY) * scale)
        sprite_h = int(clamp(sprite_h, 6, C.RENDER_H * 2))
        sprite_w = sprite_h

        start_y = -sprite_h // 2 + C.RENDER_H // 2
        end_y = start_y + sprite_h
        start_x = -sprite_w // 2 + screen_x
        end_x = start_x + sprite_w

        clip_sy = max(0, start_y)
        clip_ey = min(C.RENDER_H, end_y)
        if clip_ey <= clip_sy:
            return
        offset_y = clip_sy - start_y
        vis_h = clip_ey - clip_sy

        tex_scaled = pygame.transform.smoothscale(tex, (sprite_w, sprite_h))
        fog_factor = math.exp(-C.FOG_STRENGTH * transformY * 22.0)
        mul = int(255 * fog_factor)
        mul = int(clamp(mul, 80 if dim else 120, 255))
        tex_scaled = tex_scaled.copy()
        tex_scaled.fill((mul, mul, mul), special_flags=pygame.BLEND_MULT)

        clip_sx = max(0, start_x)
        clip_ex = min(C.RENDER_W, end_x)

        for stripe in range(clip_sx, clip_ex):
            if transformY >= zbuffer[stripe]:
                continue
            tx = stripe - start_x
            if 0 <= tx < sprite_w:
                col = tex_scaled.subsurface((tx, offset_y, 1, vis_h))
                self.render.blit(col, (stripe, clip_sy))


# ============================================================
# 8) States (Menu / Settings / Play)
# ============================================================

class State:
    def on_enter(self, app: "App") -> None:
        pass

    def on_exit(self, app: "App") -> None:
        pass

    def handle_event(self, app: "App", event: pygame.event.Event) -> None:
        pass

    def update(self, app: "App", dt: float, t: float) -> None:
        pass

    def draw(self, app: "App") -> None:
        pass


class MenuState(State):
    def __init__(self) -> None:
        self.items = ["Start", "Settings", "Quit"]
        self.sel = 0
        self.item_rects: List[pygame.Rect] = []


    def on_enter(self, app: "App") -> None:
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)
        app.audio.stop_drone()
        app.audio.play_menu_music()


    def handle_event(self, app: "App", event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            for i, r in enumerate(self.item_rects):
                if r.collidepoint(mx, my):
                    self._set_selected(app, i)
                    break

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self._set_selected(app, (self.sel - 1) % len(self.items))
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._set_selected(app, (self.sel + 1) % len(self.items))
            elif event.key == pygame.K_RETURN:
                self._activate(app)
            elif event.key == pygame.K_ESCAPE:
                app.running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, r in enumerate(self.item_rects):
                if r.collidepoint(mx, my):
                    self._set_selected(app, i)
                    self._activate(app)
                    break

    def _set_selected(self, app: "App", idx: int) -> None:
        if idx != self.sel:
            self.sel = idx
            app.audio.play_ui_hover()

    def _activate(self, app: "App") -> None:
        app.audio.play_ui_click()
        if self.sel == 0:
            app.change_state(PlayState())
        elif self.sel == 1:
            app.change_state(SettingsState())
        elif self.sel == 2:
            app.running = False


    def draw(self, app: "App") -> None:
        self.item_rects = app.renderer.draw_menu(
            title="ESCAPE FROM FAMCS",
            items=self.items,
            selected=self.sel,
            hint="",
            famcs_logo=True,
        )

        


class SettingsState(State):
    def __init__(self) -> None:
        self.sel = 0
        self.item_rects: List[pygame.Rect] = []


    def on_enter(self, app: "App") -> None:
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)
        app.audio.stop_drone()
        app.audio.play_menu_music()


    def handle_event(self, app: "App", event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            for i, r in enumerate(self.item_rects):
                if r.collidepoint(mx, my):
                    self._set_selected(app, i)
                    break

        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
            mx, my = event.pos
            for i, r in enumerate(self.item_rects):
                if r.collidepoint(mx, my):
                    self._set_selected(app, i)
                    # toggle / apply
                    if self.sel in (0, 1, 5):
                        self._toggle(app)
                    else:
                        direction = +1 if event.button == 1 else -1
                        self._change(app, direction)
                    return

        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_UP, pygame.K_w):
            self._set_selected(app, (self.sel - 1) % 6)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._set_selected(app, (self.sel + 1) % 6)

        elif event.key in (pygame.K_LEFT, pygame.K_a):
            self._change(app, -1)

        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._change(app, +1)

        elif event.key == pygame.K_RETURN:
            self._toggle(app)

        elif event.key == pygame.K_ESCAPE:
            app.change_state(MenuState())

    # в handle_event: self.sel = (self.sel + 1) % 6   и (self.sel - 1) % 6

    def _set_selected(self, app: "App", idx: int) -> None:
        if idx != self.sel:
            self.sel = idx
            app.audio.play_ui_hover()

    def _change(self, app: "App", direction: int) -> None:
        cfg = app.cfg
        step = 0.05  # 5%
        changed = False
        if self.sel == 0:
            cfg.invert_mouse_x = not cfg.invert_mouse_x
            changed = True
        elif self.sel == 1:
            cfg.fullscreen = not cfg.fullscreen
            app.apply_video_settings()
            changed = True
        elif self.sel == 2:
            if not cfg.fullscreen:
                before = cfg.window_size
                cfg.set_res_index(cfg.res_index() + direction)
                changed = cfg.window_size != before
                if changed:
                    app.apply_video_settings()
        elif self.sel == 3:
            new_mv = clamp(cfg.music_volume + direction * step, 0.0, 1.0)
            changed = new_mv != cfg.music_volume
            cfg.music_volume = new_mv
        elif self.sel == 4:
            new_sv = clamp(cfg.sfx_volume + direction * step, 0.0, 1.0)
            changed = new_sv != cfg.sfx_volume
            cfg.sfx_volume = new_sv
        elif self.sel == 5:
            pass

        if changed:
            app.audio.play_ui_click()
            app.audio.apply_volumes(cfg.music_volume, cfg.sfx_volume)
            app.save_config()

    def _toggle(self, app: "App") -> None:
        cfg = app.cfg
        changed = False
        if self.sel == 0:
            cfg.invert_mouse_x = not cfg.invert_mouse_x
            changed = True
        elif self.sel == 1:
            cfg.fullscreen = not cfg.fullscreen
            app.apply_video_settings()
            changed = True
        elif self.sel == 5:
            app.audio.play_ui_click()
            app.change_state(MenuState())
            return

        if changed:
            app.audio.play_ui_click()
            app.audio.apply_volumes(cfg.music_volume, cfg.sfx_volume)
            app.save_config()


    def draw(self, app: "App") -> None:
        mv = int(app.cfg.music_volume * 100)
        sv = int(app.cfg.sfx_volume * 100)

        items = [
            f"Mouse invert X: {'ON' if app.cfg.invert_mouse_x else 'OFF'}",
            f"Fullscreen: {'ON' if app.cfg.fullscreen else 'OFF'}",
            f"Resolution: {app.cfg.window_size[0]}x{app.cfg.window_size[1]}{' (only windowed)' if app.cfg.fullscreen else ''}",
            f"Music volume: {mv}%",
            f"SFX volume: {sv}%",
            "Back",
        ]

        self.item_rects = app.renderer.draw_menu(
            title="Settings",
            items=items,
            selected=self.sel,
            hint="",
        )



class PlayState(State):
    STATE_PLAY = "play"
    STATE_DEAD = "dead"

    def __init__(self) -> None:
        self.map_index = 0
        self.world = World(MAP_VARIANTS[self.map_index])
        self.player = Player()
        self.monsters: List[Monster] = [Monster()]
        self.state = self.STATE_PLAY
        self.dead_time = 0.0

        self.lives = 3
        self.spawn_point: Tuple[float, float] = (2.5, 2.5)
        self.door_trigger: Tuple[float, float] = (0.0, 0.0)
        self.door_plane: Tuple[float, float] = (0.0, 0.0)
        self.door_cell: Tuple[int, int] = (0, 0)
        self.door_orientation: str = "vertical"
        self.zachetki: List[Tuple[float, float]] = []
        self.zachet_collected: List[bool] = []
        self.door_open = False
        self.initialized = False
        self.monster_count = 1

    def on_enter(self, app: "App") -> None:
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)
        pygame.mouse.get_rel()
        app.audio.stop_menu_music()
        app.audio.start_drone()
        if not self.initialized:
            self.start_new_run(app)
            self.initialized = True

    def on_exit(self, app: "App") -> None:
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)
        app.audio.stop_drone()

    def start_new_run(self, app: "App") -> None:
        attempts = 0
        while attempts < 10:
            self.map_index = random.randrange(len(MAP_VARIANTS))
            self.world = World(MAP_VARIANTS[self.map_index])

            # largest map gets two monsters
            areas = [len(m.grid) * len(m.grid[0]) for m in MAP_VARIANTS]
            max_area = max(areas)
            self.monster_count = 2 if areas[self.map_index] == max_area else 1

            self.spawn_point = app.find_empty_cell(self.world, (2, 2))
            spawn_cell = (int(self.spawn_point[0]), int(self.spawn_point[1]))
            dist_map = compute_dist_map(self.world, spawn_cell[0], spawn_cell[1])

            reachable_cells = [
                (x, y)
                for y, row in enumerate(dist_map)
                for x, d in enumerate(row)
                if d != -1 and not self.world.is_wall_cell(x, y)
            ]

            def pick_reachable(prefer: Tuple[int, int], avoid: List[Tuple[float, float]]) -> Tuple[float, float]:
                candidates = [
                    (x, y)
                    for x, y in reachable_cells
                    if all(math.hypot(x + 0.5 - ax, y + 0.5 - ay) > 2.0 for ax, ay in avoid)
                ]
                if not candidates:
                    candidates = reachable_cells
                random.shuffle(candidates)
                candidates.sort(key=lambda c: math.hypot(c[0] + 0.5 - prefer[0], c[1] + 0.5 - prefer[1]))
                cx, cy = candidates[0]
                return cx + 0.5, cy + 0.5

            (
                self.door_trigger,
                self.door_plane,
                self.door_cell,
                self.door_orientation,
            ) = self._pick_door(app, pick_reachable)

            self.zachetki = []
            for prefer in ((self.world.w // 2, self.world.h // 2), (2, self.world.h - 3), (self.world.w - 3, 2)):
                self.zachetki.append(pick_reachable(prefer, [self.spawn_point, self.door_trigger] + self.zachetki))

            sanity_map = compute_dist_map(
                self.world, spawn_cell[0], spawn_cell[1], lambda mx, my: self.world.cell_at(mx, my) == "1"
            )
            targets = [self.door_trigger, *self.zachetki]
            if any(sanity_map[int(ty)][int(tx)] == -1 for tx, ty in targets):
                attempts += 1
                continue
            self.zachet_collected = [False] * len(self.zachetki)
            self.lives = 3
            self.door_open = False
            self._respawn(app, reset_zachetka=False)
            return

        raise RuntimeError("Failed to generate reachable layout")

    def _respawn(self, app: "App", reset_zachetka: bool = False) -> None:
        self.player.x, self.player.y = self.spawn_point
        self.player.dirx, self.player.diry = 1.0, 0.0
        self.player.planex, self.player.planey = 0.0, C.FOV_PLANE

        self.monsters = []
        
        # dist-map от игрока: монстр обязан быть в достижимой области (с учётом закрытой двери)
        px_cell, py_cell = int(self.player.x), int(self.player.y)
        dist_map = compute_dist_map(self.world, px_cell, py_cell, self.world.is_blocking_cell)

        candidates: List[Tuple[int, int, int]] = []  # (d, x, y)
        for y, row in enumerate(dist_map):
            for x, d in enumerate(row):
                if d >= 0 and not self.world.is_blocking_cell(x, y):
                    candidates.append((d, x, y))

        if not candidates:
            # fallback (почти не должно случаться)
            candidates = [(0, int(self.player.x) + 1, int(self.player.y) + 1)]

        dmax = max(d for d, _, _ in candidates)
        min_d = max(6, int(dmax * 0.45))
        min_d = min(min_d, dmax)

        avoid = [self.spawn_point, self.door_trigger] + self.zachetki
        taken = set()

        def far_ok(x: int, y: int) -> bool:
            cx, cy = x + 0.5, y + 0.5
            if (x, y) in taken:
                return False
            # не рядом со спавном/дверью/зачётками
            return all(math.hypot(cx - ax, cy - ay) > 4.0 for ax, ay in avoid)

        # сначала берём дальние, иначе — любые достижимые
        far = [(d, x, y) for (d, x, y) in candidates if d >= min_d and far_ok(x, y)]
        pool = far if far else [(d, x, y) for (d, x, y) in candidates if far_ok(x, y)]
        if not pool:
            pool = candidates

        pool.sort(reverse=True)  # самые дальние впереди

        for i in range(self.monster_count):
            # небольшая случайность: выбираем из "верхушки" дальних
            top = pool[:max(8, len(pool) // 10)]
            d, x, y = random.choice(top)
            taken.add((x, y))

            m = Monster()
            m.x, m.y = x + 0.5, y + 0.5
            now = pygame.time.get_ticks() / 1000.0
            m.active_time = now + C.MONSTER_SPAWN_DELAY + random.uniform(0.0, 0.4)
            m.next_replan = 0.0
            m.target = None
            m.tunnel_dist_cells = 999
            self.monsters.append(m)

            # обновим pool, чтобы второй монстр не попал туда же
            pool = [(dd, xx, yy) for (dd, xx, yy) in pool if (xx, yy) not in taken]
            if not pool:
                pool = candidates

        if reset_zachetka:
            self.zachet_collected = [False] * len(self.zachet_collected)
            self.door_open = False

        self.state = self.STATE_PLAY
        self.dead_time = 0.0

        app.audio.stop_scream()
        app.audio.set_game_drone_dynamic(0.25)
        app.audio.start_drone()
        pygame.mouse.get_rel()

    def _pick_door(
        self,
        app: "App",
        pick_unique: Any,
    ) -> Tuple[Tuple[float, float], Tuple[float, float], Tuple[int, int], str]:
        tries = 0
        while tries < 250:
            # берём ДОСТИЖИМУЮ пустую клетку (рядом с ней и будет дверь)
            trigger = pick_unique((self.world.w - 3, self.world.h - 3), [self.spawn_point])
            mx, my = int(trigger[0]), int(trigger[1])

            if self.world.is_wall_cell(mx, my):
                tries += 1
                continue

            # ищем соседнюю стену — в неё и встраиваем дверь
            # (door_cell = бывшая "1", которую заменим на "D")
            candidates = [
                (-1, 0, "vertical"),   # стена слева -> плоскость x = mx
                (1, 0, "vertical"),    # стена справа -> плоскость x = mx + 1
                (0, -1, "horizontal"),  # стена сверху -> плоскость y = my
                (0, 1, "horizontal"),   # стена снизу -> плоскость y = my + 1
            ]
            random.shuffle(candidates)

            for dx, dy, ori in candidates:
                wx, wy = mx + dx, my + dy
                if self.world.is_wall_cell(wx, wy):
                    # триггер = центр пустой клетки
                    door_trigger = (mx + 0.5, my + 0.5)

                    # плоскость двери ровно на границе со стеной (не выступает)
                    if ori == "vertical":
                        plane_x = float(mx) if dx == -1 else float(mx + 1)
                        plane_y = my + 0.5
                        door_plane = (plane_x, plane_y)
                    else:
                        plane_y = float(my) if dy == -1 else float(my + 1)
                        plane_x = mx + 0.5
                        door_plane = (plane_x, plane_y)

                    door_cell = (wx, wy)  # клетка стены, которую заменим на 'D'
                    return door_trigger, door_plane, door_cell, ori

            tries += 1

        # fallback: как получится
        mx, my = 2, 2
        door_trigger = (mx + 0.5, my + 0.5)
        door_plane = (mx + 1.0, my + 0.5)
        door_cell = (mx + 1, my)
        return door_trigger, door_plane, door_cell, "vertical"

    def handle_event(self, app: "App", event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                app.change_state(PauseState(self))
            elif event.key == pygame.K_r:
                self.start_new_run(app)
            elif event.key == pygame.K_m:
                app.show_minimap = not app.show_minimap

    def _handle_pickups(self, app: "App") -> None:
        for i, pos in enumerate(self.zachetki):
            if not self.zachet_collected[i]:
                if math.hypot(self.player.x - pos[0], self.player.y - pos[1]) < 0.6:
                    self.zachet_collected[i] = True
                    app.audio.play_pickup()

        self.door_open = all(self.zachet_collected)

        if self.door_open:
            if math.hypot(self.player.x - self.door_trigger[0], self.player.y - self.door_trigger[1]) < 0.85:
                app.change_state(VictoryState())

    def lose_life(self, app: "App") -> None:
        self.lives -= 1
        if self.lives <= 0:
            app.change_state(GameOverState())
            return
        app.change_state(DeathScreamerState(self))

    def update(self, app: "App", dt: float, t: float) -> None:
        keys = pygame.key.get_pressed()

        mx, _ = pygame.mouse.get_rel()
        rot_dir = -1.0 if app.cfg.invert_mouse_x else 1.0
        ang_mouse = rot_dir * mx * C.MOUSE_SENS

        if abs(ang_mouse) > 1e-9:
            self.player.rotate(ang_mouse)

        if keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]:
            angk = C.ROT_SPEED_KEYS * dt * rot_dir
            angk = +angk if keys[pygame.K_LEFT] else -angk
            self.player.rotate(angk)

        if self.state != self.STATE_PLAY:
            app.audio.set_game_drone_dynamic(0.10)
            return

        speed = C.MOVE_SPEED * (C.RUN_MULT if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else 1.0)

        moveX = moveY = 0.0
        if keys[pygame.K_w]:
            moveX += self.player.dirx * speed * dt
            moveY += self.player.diry * speed * dt
        if keys[pygame.K_s]:
            moveX -= self.player.dirx * speed * dt
            moveY -= self.player.diry * speed * dt
        if keys[pygame.K_a]:
            moveX -= self.player.planex * speed * dt
            moveY -= self.player.planey * speed * dt
        if keys[pygame.K_d]:
            moveX += self.player.planex * speed * dt
            moveY += self.player.planey * speed * dt

        r = C.PLAYER_RADIUS

        nx = self.player.x + moveX
        ny = self.player.y + moveY

        # X отдельно (скольжение вдоль стен)
        if not self.world.collides_circle(nx, self.player.y, r):
            self.player.x = nx

        # Y отдельно
        if not self.world.collides_circle(self.player.x, ny, r):
            self.player.y = ny

        self.world.apply_wrap(self.player)

        self._handle_pickups(app)

        if t < min(m.active_time for m in self.monsters):
            app.audio.set_game_drone_dynamic(0.25)
            return

        px_cell, py_cell = int(self.player.x), int(self.player.y)
        dist_map = compute_dist_map(self.world, px_cell, py_cell, self.world.is_blocking_cell)

        min_dist = 999
        for m in self.monsters:
            if t < m.active_time:
                continue
            if t >= m.next_replan:
                m.next_replan = t + C.REPLAN_INTERVAL

                mx_cell, my_cell = int(m.x), int(m.y)
                d = dist_map[my_cell][mx_cell]
                m.tunnel_dist_cells = d if d != -1 else 999

                nxt = pick_next_cell_for_monster(dist_map, mx_cell, my_cell)
                if nxt is not None:
                    m.target = (nxt[0] + 0.5, nxt[1] + 0.5)
                else:
                    m.target = (self.player.x, self.player.y)

            min_dist = min(min_dist, m.tunnel_dist_cells)

            if m.target is None:
                m.target = (self.player.x, self.player.y)

            tx, ty = m.target
            mdx = tx - m.x
            mdy = ty - m.y
            md = math.hypot(mdx, mdy) + 1e-9

            step = C.MOVE_SPEED * dt
            mx_try = m.x + (mdx / md) * step
            my_try = m.y + (mdy / md) * step

            if not self.world.is_blocking_cell(int(mx_try), int(m.y)):
                m.x = mx_try
            if not self.world.is_blocking_cell(int(m.x), int(my_try)):
                m.y = my_try

            self.world.apply_wrap(m)  # type: ignore[arg-type]

            if math.hypot(m.x - tx, m.y - ty) < 0.18:
                m.target = None

            if math.hypot(self.player.x - m.x, self.player.y - m.y) < C.KILL_DIST:
                self.lose_life(app)
                return

        if min_dist >= 999:
            app.audio.set_game_drone_dynamic(0.12)
        else:
            v = 1.0 - (min_dist / C.SOUND_AUDIBLE_CELLS)
            v = clamp(v, 0.0, 1.0)
            v = v ** C.SOUND_CURVE
            app.audio.set_game_drone_dynamic(0.12 + 0.88 * v)

    def serialize(self) -> Dict[str, Any]:
        return {
            "state": "play",
            "player": {
                "x": self.player.x,
                "y": self.player.y,
                "dirx": self.player.dirx,
                "diry": self.player.diry,
                "planex": self.player.planex,
                "planey": self.player.planey,
            },
            "monsters": [
                {
                    "x": m.x,
                    "y": m.y,
                    "active_time": m.active_time,
                    "next_replan": m.next_replan,
                    "tunnel_dist_cells": m.tunnel_dist_cells,
                }
                for m in self.monsters
            ],
            "lives": self.lives,
            "spawn_point": self.spawn_point,
            "zachetki": self.zachetki,
            "door_pos": self.door_trigger,
            "door_trigger": self.door_trigger,
            "door_plane": self.door_plane,
            "door_cell": self.door_cell,
            "door_orientation": self.door_orientation,
            "zachet_collected": self.zachet_collected,
            "door_open": self.door_open,
            "map_index": self.map_index,
        }

    def load_from_data(self, data: Dict[str, Any]) -> None:
        p = data.get("player", {})
        self.player = Player(
            x=float(p.get("x", self.player.x)),
            y=float(p.get("y", self.player.y)),
            dirx=float(p.get("dirx", self.player.dirx)),
            diry=float(p.get("diry", self.player.diry)),
            planex=float(p.get("planex", self.player.planex)),
            planey=float(p.get("planey", self.player.planey)),
        )
        self.map_index = int(data.get("map_index", self.map_index)) % len(MAP_VARIANTS)
        self.world = World(MAP_VARIANTS[self.map_index])
        monsters_data = data.get("monsters", [])
        self.monsters = []
        for m in monsters_data:
            self.monsters.append(
                Monster(
                    x=float(m.get("x", 0.0)),
                    y=float(m.get("y", 0.0)),
                    active_time=float(m.get("active_time", pygame.time.get_ticks() / 1000.0)),
                    next_replan=float(m.get("next_replan", 0.0)),
                    target=None,
                    tunnel_dist_cells=int(m.get("tunnel_dist_cells", 999)),
                )
            )
        if not self.monsters:
            self.monsters = [Monster()]
        self.lives = int(data.get("lives", self.lives))
        self.spawn_point = tuple(data.get("spawn_point", self.spawn_point))  # type: ignore
        self.zachetki = [tuple(z) for z in data.get("zachetki", self.zachetki)]  # type: ignore
        self.door_trigger = tuple(  # type: ignore
            data.get("door_trigger", data.get("door_pos", self.door_trigger))
        )
        self.door_plane = tuple(data.get("door_plane", self.door_plane))  # type: ignore
        door_cell_raw = data.get("door_cell", self.door_cell)
        self.door_cell = (int(door_cell_raw[0]), int(door_cell_raw[1])) if door_cell_raw else self.door_cell
        self.door_orientation = str(data.get("door_orientation", self.door_orientation))
        self.zachet_collected = [bool(z) for z in data.get("zachet_collected", self.zachet_collected)]
        if not self.zachet_collected:
            self.zachet_collected = [False] * len(self.zachetki)
        self.door_open = bool(data.get("door_open", self.door_open or all(self.zachet_collected)))
        self.monster_count = max(1, len(self.monsters))
        self.state = self.STATE_PLAY

    def draw(self, app: "App") -> None:
        t = pygame.time.get_ticks() / 1000.0
        show_monster = any(t >= m.active_time for m in self.monsters)
        is_dead = (self.state == self.STATE_DEAD)
        app.renderer.draw_play(
            self.world,
            self.player,
            self.monsters,
            show_monster,
            is_dead,
            door_pos=self.door_trigger,
            door_plane_pos=self.door_plane,
            door_orientation=self.door_orientation,
            door_open=self.door_open,
            zachetki=self.zachetki,
            zachet_collected=self.zachet_collected,
            lives=self.lives,
            show_minimap=app.show_minimap,
        )


class PauseState(State):
    def __init__(self, play_state: PlayState) -> None:
        self.play_state = play_state
        self.items = ["Resume", "Save", "Load", "Exit to menu"]
        self.sel = 0
        self.item_rects: List[pygame.Rect] = []
        self.notice: str = ""

    def on_enter(self, app: "App") -> None:
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)
        app.audio.stop_drone()
        app.audio.stop_menu_music()

    def on_exit(self, app: "App") -> None:
        self.notice = ""

    def _set_selected(self, app: "App", idx: int) -> None:
        if idx != self.sel:
            self.sel = idx
            app.audio.play_ui_hover()

    def _activate(self, app: "App") -> None:
        app.audio.play_ui_click()
        if self.sel == 0:
            app.change_state(self.play_state)
            app.audio.start_drone()
        elif self.sel == 1:
            app.save_game(self.play_state.serialize())
            self.notice = "Saved"
        elif self.sel == 2:
            data = app.load_game()
            if data:
                self.play_state.load_from_data(data)
                app.change_state(self.play_state)
                app.audio.start_drone()
                return
            else:
                self.notice = "No save"
        elif self.sel == 3:
            app.change_state(MenuState())

    def handle_event(self, app: "App", event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            for i, r in enumerate(self.item_rects):
                if r.collidepoint(mx, my):
                    self._set_selected(app, i)
                    break

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, r in enumerate(self.item_rects):
                if r.collidepoint(mx, my):
                    self._set_selected(app, i)
                    self._activate(app)
                    return

        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            self._set_selected(app, (self.sel - 1) % len(self.items))
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._set_selected(app, (self.sel + 1) % len(self.items))
        elif event.key == pygame.K_RETURN:
            self._activate(app)
        elif event.key == pygame.K_ESCAPE:
            app.change_state(self.play_state)
            app.audio.start_drone()

    def update(self, app: "App", dt: float, t: float) -> None:
        pass

    def draw(self, app: "App") -> None:
        items = self.items.copy()
        if self.notice:
            items.append(self.notice)
        self.item_rects = app.renderer.draw_menu(
            title="Paused",
            items=items,
            selected=self.sel,
            hint="",
        )


class DeathScreamerState(State):
    def __init__(self, play_state: "PlayState", duration: Optional[float] = None) -> None:
        self.play_state = play_state
        self.duration = duration if duration is not None else random.uniform(0.8, 1.2)
        self.start_time = 0.0

    def on_enter(self, app: "App") -> None:
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)
        self.start_time = pygame.time.get_ticks() / 1000.0
        app.audio.stop_drone()
        app.audio.stop_menu_music()
        app.audio.play_scream()

    def handle_event(self, app: "App", event: pygame.event.Event) -> None:
        pass

    def update(self, app: "App", dt: float, t: float) -> None:
        if (t - self.start_time) >= self.duration:
            self.play_state._respawn(app)
            app.change_state(self.play_state)

    def draw(self, app: "App") -> None:
        app.renderer.draw_fullscreen_image(app.monster_img, "")


class VictoryState(State):
    def on_enter(self, app: "App") -> None:
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)
        app.audio.stop_drone()
        app.audio.stop_menu_music()
        app.audio.play_victory()

    def handle_event(self, app: "App", event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            app.change_state(MenuState())
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            app.change_state(MenuState())

    def update(self, app: "App", dt: float, t: float) -> None:
        pass

    def draw(self, app: "App") -> None:
        app.renderer.draw_fullscreen_image(app.victory_img, "ESCAPE FROM FAMCS")


class GameOverState(State):
    def on_enter(self, app: "App") -> None:
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)
        app.audio.stop_drone()
        app.audio.stop_menu_music()
        app.audio.play_end()

    def handle_event(self, app: "App", event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            app.change_state(MenuState())
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            app.change_state(MenuState())

    def update(self, app: "App", dt: float, t: float) -> None:
        pass

    def draw(self, app: "App") -> None:
        app.renderer.draw_fullscreen_image(app.end_img, "You failed")


# ============================================================
# 9) App (DI container + main loop)
# ============================================================

class App:
    def __init__(self) -> None:
        pygame.init()
        self.cfg = RuntimeConfig()
        self.load_config()

        self.show_minimap = False

        self.screen = self._create_screen()
        pygame.display.set_caption("ESCAPE FROM FAMCS")

        self.clock = pygame.time.Clock()
        self.running = True

        # Assets
        self.wall_tex = make_backrooms_wall_texture(C.TEXTURE_SIZE)
        self.monster_img = self._load_monster()
        self.heart_img = self._load_image_alpha(C.HEART_IMG)
        self.zachet_img = self._load_image_alpha(C.ZACHET_IMG)
        self.door_img = self._load_image_alpha(C.DOOR_IMG)
        self.victory_img = self._load_image(C.VICTORY_IMG)
        self.end_img = self._load_image(C.END_IMG)

        # Subsystems
        self.audio = AudioSystem()
        self.audio.init()
        self.audio.apply_volumes(self.cfg.music_volume, self.cfg.sfx_volume)

        self.renderer = Renderer(
            self.screen,
            self.wall_tex,
            self.monster_img,
            self.heart_img,
            self.zachet_img,
            self.door_img,
            self.victory_img,
            self.end_img,
        )

        # State machine
        self.state: State = MenuState()
        self.state.on_enter(self)

    def _create_screen(self) -> pygame.Surface:
        if self.cfg.fullscreen:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        return pygame.display.set_mode(self.cfg.window_size)

    def apply_video_settings(self) -> None:
        # recreate display surface
        self.screen = self._create_screen()
        self.renderer.set_screen(self.screen)

    def _config_dir(self) -> str:
        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))


    def _config_path(self) -> str:
        return os.path.join(self._config_dir(), "settings.json")

    def _savegame_path(self) -> str:
        return os.path.join(self._config_dir(), "savegame.json")

    def _savegame_path(self) -> str:
        return os.path.join(self._config_dir(), "savegame.json")

    def load_config(self) -> None:
        path = self._config_path()
        if not os.path.exists(path):
            return
        try:
            import json
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.cfg.fullscreen = bool(data.get("fullscreen", self.cfg.fullscreen))
            ws = data.get("window_size", list(self.cfg.window_size))
            if isinstance(ws, (list, tuple)) and len(ws) == 2:
                self.cfg.window_size = (int(ws[0]), int(ws[1]))

            self.cfg.invert_mouse_x = bool(data.get("invert_mouse_x", self.cfg.invert_mouse_x))

            mv = float(data.get("music_volume", self.cfg.music_volume))
            sv = float(data.get("sfx_volume", self.cfg.sfx_volume))
            self.cfg.music_volume = clamp(mv, 0.0, 1.0)
            self.cfg.sfx_volume = clamp(sv, 0.0, 1.0)

        except Exception:
            # если json битый — просто игнорируем
            return

    def save_config(self) -> None:
        path = self._config_path()
        try:
            import json
            data = {
                "fullscreen": self.cfg.fullscreen,
                "window_size": list(self.cfg.window_size),
                "invert_mouse_x": self.cfg.invert_mouse_x,
                "music_volume": float(self.cfg.music_volume),
                "sfx_volume": float(self.cfg.sfx_volume),
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            return

    def save_game(self, data: Dict[str, Any]) -> None:
        path = self._savegame_path()
        try:
            import json

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            return

    def load_game(self) -> Optional[Dict[str, Any]]:
        path = self._savegame_path()
        if not os.path.exists(path):
            return None
        try:
            import json

            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None


    def _load_monster(self) -> pygame.Surface:
        path = resource_path(C.MONSTER_FILE)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Не найден '{C.MONSTER_FILE}'. Ожидается по пути:\n{path}")
        img = pygame.image.load(path).convert()
        img = pygame.transform.smoothscale(img, (C.TEXTURE_SIZE, C.TEXTURE_SIZE))
        return img

    def _load_image(self, fname: str) -> pygame.Surface:
        path = resource_path(fname)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Не найден '{fname}'. Ожидается по пути:\n{path}")
        return pygame.image.load(path).convert()

    def _load_image_alpha(self, fname: str) -> pygame.Surface:
        path = resource_path(fname)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Не найден '{fname}'. Ожидается по пути:\n{path}")
        return pygame.image.load(path).convert_alpha()

    def _load_image(self, fname: str) -> pygame.Surface:
        path = resource_path(fname)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Не найден '{fname}'. Ожидается по пути:\n{path}")
        return pygame.image.load(path).convert()

    def _load_image_alpha(self, fname: str) -> pygame.Surface:
        path = resource_path(fname)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Не найден '{fname}'. Ожидается по пути:\n{path}")
        return pygame.image.load(path).convert_alpha()

    @staticmethod
    def find_empty_cell(world: World, prefer: Tuple[int, int]) -> Tuple[float, float]:
        px, py = prefer
        if not world.is_blocking_cell(px, py):
            return px + 0.5, py + 0.5
        for y in range(1, world.h - 1):
            for x in range(1, world.w - 1):
                if not world.is_blocking_cell(x, y):
                    return x + 0.5, y + 0.5
        return 2.5, 2.5

    def change_state(self, new_state: State) -> None:
        self.state.on_exit(self)
        self.state = new_state
        self.state.on_enter(self)

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(C.FPS) / 1000.0
            if dt > 0.05:
                dt = 0.05
            t = pygame.time.get_ticks() / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    self.state.handle_event(self, event)

            self.state.update(self, dt, t)
            self.state.draw(self)
            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    # Packaging notes:
    # Windows (one folder to keep assets in img/ and audio/):
    # pyinstaller --noconfirm --windowed --name "ESCAPE FROM FAMCS" ^
    #   --add-data "img;img" --add-data "audio;audio" EscapeFromFAMCS.py
    #
    # macOS:
    # pyinstaller --noconfirm --windowed --name "ESCAPE FROM FAMCS" \
    #   --add-data "img:img" --add-data "audio:audio" EscapeFromFAMCS.py
    App().run()
