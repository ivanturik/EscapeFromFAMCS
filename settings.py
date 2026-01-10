# settings.py
import os
import sys
from dataclasses import dataclass
from typing import Tuple


def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


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
    fullscreen: bool = True
    window_size: Tuple[int, int] = (960, 540)
    invert_mouse_x: bool = False

    music_volume: float = 0.10
    sfx_volume: float = 1.00

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
