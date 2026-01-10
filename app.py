# app.py
import os
from typing import Any, Dict, Optional, Tuple, List
from collections import deque

import pygame

from settings import C, RuntimeConfig, clamp, resource_path
from renderer import Renderer, make_backrooms_wall_texture
from audio_system import AudioSystem
from world import World
from states import State, MenuState
from pathfinding import DIRS4


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
        self.monster_img = self._load_image_safe(C.MONSTER_FILE, alpha=False, convert=True, scale=(C.TEXTURE_SIZE, C.TEXTURE_SIZE))
        self.heart_img = self._load_image_safe(C.HEART_IMG, alpha=True)
        self.zachet_img = self._load_image_safe(C.ZACHET_IMG, alpha=True)
        self.door_img = self._load_image_safe(C.DOOR_IMG, alpha=True)
        self.victory_img = self._load_image_safe(C.VICTORY_IMG, alpha=False)
        self.end_img = self._load_image_safe(C.END_IMG, alpha=False)

        # Audio
        self.audio = AudioSystem()
        self.audio.init()
        self.audio.apply_volumes(self.cfg.music_volume, self.cfg.sfx_volume)

        # Renderer
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
        self.screen = self._create_screen()
        self.renderer.set_screen(self.screen)

    def _config_dir(self) -> str:
        if getattr(__import__("sys"), "frozen", False):
            import sys
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def _config_path(self) -> str:
        return os.path.join(self._config_dir(), "settings.json")

    def _savegame_path(self) -> str:
        return os.path.join(self._config_dir(), "savegame.json")

    def _load_image_safe(
        self,
        fname: str,
        alpha: bool = False,
        convert: bool = True,
        fallback_size: Tuple[int, int] = (64, 64),
        scale: Optional[Tuple[int, int]] = None,
    ) -> pygame.Surface:
        path = resource_path(fname)
        if not os.path.exists(path):
            print(f"Warning: {fname} not found. Using fallback.")
            surf = pygame.Surface(fallback_size, pygame.SRCALPHA if alpha else 0)
            surf.fill((255, 0, 255, 255) if alpha else (255, 0, 255))
            return surf.convert_alpha() if alpha and convert else (surf.convert() if convert else surf)

        try:
            img = pygame.image.load(path)
            if scale is not None:
                img = pygame.transform.smoothscale(img, scale)
            if convert:
                return img.convert_alpha() if alpha else img.convert()
            return img
        except Exception as e:
            print(f"Warning: failed to load {fname}: {e}. Using fallback.")
            surf = pygame.Surface(fallback_size, pygame.SRCALPHA if alpha else 0)
            surf.fill((255, 0, 255, 255) if alpha else (255, 0, 255))
            return surf.convert_alpha() if alpha and convert else (surf.convert() if convert else surf)

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

    @staticmethod
    def find_empty_cell(world: World, prefer: Tuple[int, int]) -> Tuple[float, float]:
        w, h = world.w, world.h
        px, py = prefer

        def walkable(x: int, y: int) -> bool:
            return (0 <= x < w and 0 <= y < h and not world.is_blocking_cell(x, y))

        def bfs_component(sx: int, sy: int, visited: set) -> List[Tuple[int, int]]:
            q = deque([(sx, sy)])
            visited.add((sx, sy))
            comp: List[Tuple[int, int]] = []
            while q:
                x, y = q.popleft()
                comp.append((x, y))
                for dx, dy in DIRS4:
                    nx, ny = x + dx, y + dy
                    if walkable(nx, ny) and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        q.append((nx, ny))
            return comp

        visited: set = set()
        comps: List[List[Tuple[int, int]]] = []
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                if walkable(x, y) and (x, y) not in visited:
                    comps.append(bfs_component(x, y, visited))

        if not comps:
            return 2.5, 2.5

        largest = max(comps, key=len)

        prefer_comp = None
        if walkable(px, py):
            for comp in comps:
                if (px, py) in comp:
                    prefer_comp = comp
                    break

        min_ok = max(80, int(w * h * 0.12))
        chosen = prefer_comp if (prefer_comp is not None and len(prefer_comp) >= min_ok) else largest

        def open_neighbors(x: int, y: int) -> int:
            c = 0
            for dx, dy in DIRS4:
                if walkable(x + dx, y + dy):
                    c += 1
            return c

        good = [(x, y) for (x, y) in chosen if open_neighbors(x, y) >= 2]
        pool = good if good else chosen

        x, y = pool[__import__("random").choice(range(len(pool)))]
        return x + 0.5, y + 0.5

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
