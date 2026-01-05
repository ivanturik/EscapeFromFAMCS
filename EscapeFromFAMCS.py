import os
import sys
import math
import random
from dataclasses import dataclass
from collections import deque
from array import array
from typing import List, Optional, Tuple

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

    # Music
    MENU_MUSIC_FILE: str = "menu.mp3"

    # Gameplay
    MOVE_SPEED: float = 2.6
    RUN_MULT: float = 1.75
    ROT_SPEED_KEYS: float = 2.2
    MOUSE_SENS: float = 0.0025

    # Camera / atmosphere
    FOV_PLANE: float = 0.66
    FOG_STRENGTH: float = 0.055
    CEIL_COLOR: Tuple[int, int, int] = (205, 195, 120)
    FLOOR_COLOR: Tuple[int, int, int] = (115, 105, 75)

    # Textures / resources
    TEXTURE_SIZE: int = 256
    MONSTER_FILE: str = "trush.jpg"
    SCREAM_FILE: str = "scream.mp3"

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
# 2) World (Map + collision)
# ============================================================

class World:
    MAP: List[str] = [
        "111111111111111111111111",
        "100000000000000000000001",
        "101111011111011111011101",
        "101000010000010000010001",
        "101011110111110111110101",
        "101010000100000100000101",
        "101010111101111101111101",
        "101010100001000001000101",
        "101010101111011111011101",
        "100010100000010000010001",
        "111010111110111110111011",
        "100000100000100000100001",
        "101111101111101111101111",
        "101000001000001000001001",
        "101011111011111011111101",
        "101010000010000010000001",
        "101010111110111110111101",
        "101010100000100000100101",
        "101010101111101111101101",
        "100000001000001000000001",
        "101111111011111011111101",
        "101000000010000010000001",
        "100000000000000000000001",
        "111111111111111111111111",
    ]

    def __init__(self) -> None:
        self.h = len(self.MAP)
        self.w = len(self.MAP[0])

    def is_wall_cell(self, mx: int, my: int) -> bool:
        if mx < 0 or mx >= self.w or my < 0 or my >= self.h:
            return True
        return self.MAP[my][mx] == "1"

    def is_wall_at(self, x: float, y: float) -> bool:
        return self.is_wall_cell(int(x), int(y))


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

        self.scream_sound: Optional[pygame.mixer.Sound] = None
        self.scream_channel: Optional[pygame.mixer.Channel] = None
        self.use_music_for_scream = False
        self.scream_path = ""

        self.menu_path = ""
        self.music_playing = False

        self.music_volume = 0.65
        self.sfx_volume = 1.00

    def init(self) -> None:
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()
        except Exception:
            self.enabled = False
            return

        self.drone_channel = pygame.mixer.Channel(0)
        self.scream_channel = pygame.mixer.Channel(1)

        self.drone = self._make_drone()
        self.scream_path = resource_path(C.SCREAM_FILE)
        self.menu_path = resource_path(C.MENU_MUSIC_FILE)

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

        # scream channel
        if self.scream_channel is not None:
            self.scream_channel.set_volume(self.sfx_volume)

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

    # ---------- Drone (game ambience) ----------
    def start_drone(self) -> None:
        if not self.enabled or self.drone is None or self.drone_channel is None:
            return
        if not self.drone_channel.get_busy():
            self.drone_channel.play(self.drone, loops=-1)
        self.set_game_drone_dynamic(self.drone_dynamic)

    def stop_drone(self) -> None:
        if self.drone_channel is not None:
            self.drone_channel.stop()

    def set_game_drone_dynamic(self, vol01: float) -> None:
        # vol01 — то, что ты считал по дистанции; сверху умножаем на sfx_volume
        self.drone_dynamic = clamp(vol01, 0.0, 1.0)
        if not self.enabled or self.drone_channel is None:
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


def compute_dist_map(world: World, px: int, py: int) -> List[List[int]]:
    dist = [[-1] * world.w for _ in range(world.h)]
    q = deque()
    dist[py][px] = 0
    q.append((px, py))

    while q:
        x, y = q.popleft()
        d = dist[y][x]
        for dx, dy in DIRS4:
            nx, ny = x + dx, y + dy
            if 0 <= nx < world.w and 0 <= ny < world.h and dist[ny][nx] == -1 and not world.is_wall_cell(nx, ny):
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
    def __init__(self, screen: pygame.Surface, wall_tex: pygame.Surface, monster_img: pygame.Surface):
        self.screen = screen
        self.render = pygame.Surface((C.RENDER_W, C.RENDER_H))
        self.wall_tex = wall_tex
        self.monster_img = monster_img
        self._rebuild_overlay()

        self.font = pygame.font.SysFont("consolas", 18)
        self.big_font = pygame.font.SysFont("consolas", 44, bold=True)

    def set_screen(self, new_screen: pygame.Surface) -> None:
        self.screen = new_screen
        self._rebuild_overlay()

    def _rebuild_overlay(self) -> None:
        w, h = self.screen.get_size()
        self.vin = vignette_surface(w, h)

    def draw_play(self, world: World, player: Player, monster: Monster, show_monster: bool, is_dead: bool) -> None:
        self.render.fill(C.CEIL_COLOR)
        pygame.draw.rect(self.render, C.FLOOR_COLOR, (0, C.RENDER_H // 2, C.RENDER_W, C.RENDER_H // 2))

        zbuffer = [1e9] * C.RENDER_W
        self._cast_walls(world, player, zbuffer)

        if show_monster and not is_dead:
            self._draw_sprite(zbuffer, player, (monster.x, monster.y))

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

        self.screen.blit(
            self.font.render("WASD — движение | мышь/←→ — поворот | Shift — бег | R — заново | Esc — меню", True, (10, 10, 10)),
            (12, 10),
        )

        if is_dead:
            # persistent screamer until restart
            jump = pygame.transform.scale(self.monster_img, (w, h))
            self.screen.blit(jump, (0, 0))
            txt = self.big_font.render("ПЕРЕСДАЧА!", True, (240, 240, 240))
            self.screen.blit(txt, (w // 2 - txt.get_width() // 2, int(h * 0.26)))
            txt2 = self.font.render("Нажми R чтобы начать заново", True, (240, 240, 240))
            self.screen.blit(txt2, (w // 2 - txt2.get_width() // 2, int(h * 0.38)))

    def draw_menu(self, title: str, items: List[str], selected: int, hint: str) -> List[pygame.Rect]:
        w, h = self.screen.get_size()
        self.screen.fill((10, 10, 10))

        tfont = pygame.font.SysFont("consolas", 46, bold=True)
        mfont = pygame.font.SysFont("consolas", 26)
        sfont = pygame.font.SysFont("consolas", 18)

        t = tfont.render(title, True, (220, 220, 220))
        self.screen.blit(t, (w // 2 - t.get_width() // 2, int(h * 0.18)))

        base_y = int(h * 0.36)
        rects: List[pygame.Rect] = []
        for i, it in enumerate(items):
            col = (255, 235, 120) if i == selected else (170, 170, 170)
            s = mfont.render(it, True, col)
            r = s.get_rect()
            r.center = (w // 2, base_y + i * 40 + 12)
            self.screen.blit(s, r.topleft)
            rects.append(r)

        hh = sfont.render(hint, True, (130, 130, 130))
        self.screen.blit(hh, (w // 2 - hh.get_width() // 2, int(h * 0.88)))

        return rects


    def _cast_walls(self, world: World, p: Player, zbuffer: List[float]) -> None:
        tex_w, tex_h = self.wall_tex.get_size()

        for x in range(C.RENDER_W):
            cameraX = 2.0 * x / C.RENDER_W - 1.0
            rayDirX = p.dirx + p.planex * cameraX
            rayDirY = p.diry + p.planey * cameraX

            mapX = int(p.x)
            mapY = int(p.y)

            deltaDistX = abs(1.0 / rayDirX) if rayDirX != 0 else 1e30
            deltaDistY = abs(1.0 / rayDirY) if rayDirY != 0 else 1e30

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
            for _ in range(128):
                if sideDistX < sideDistY:
                    sideDistX += deltaDistX
                    mapX += stepX
                    side = 0
                else:
                    sideDistY += deltaDistY
                    mapY += stepY
                    side = 1
                if world.is_wall_cell(mapX, mapY):
                    hit = True
                    break
            if not hit:
                continue

            if side == 0:
                perp = (mapX - p.x + (1 - stepX) / 2) / (rayDirX if rayDirX != 0 else 1e-6)
            else:
                perp = (mapY - p.y + (1 - stepY) / 2) / (rayDirY if rayDirY != 0 else 1e-6)

            perp = max(perp, C.MIN_WALL_DIST)
            zbuffer[x] = perp

            line_h = int(C.RENDER_H / perp)
            line_h = min(line_h, C.RENDER_H * C.MAX_LINEHEIGHT_MULT)

            draw_start = -line_h // 2 + C.RENDER_H // 2
            draw_end = line_h // 2 + C.RENDER_H // 2
            draw_start = max(0, draw_start)
            draw_end = min(C.RENDER_H - 1, draw_end)

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

            col = self.wall_tex.subsurface((texX, 0, 1, tex_h))
            col_scaled = pygame.transform.scale(col, (1, visible_h))

            shade_mul = 0.78 if side == 1 else 1.0
            fog_factor = math.exp(-C.FOG_STRENGTH * perp * 22.0)
            mul = int(255 * fog_factor * shade_mul)
            mul = int(clamp(mul, 20, 255))

            col_scaled = col_scaled.copy()
            col_scaled.fill((mul, mul, mul), special_flags=pygame.BLEND_MULT)
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
                    self.sel = i
                    break

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(self.items)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(self.items)
            elif event.key == pygame.K_RETURN:
                self._activate(app)
            elif event.key == pygame.K_ESCAPE:
                app.running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, r in enumerate(self.item_rects):
                if r.collidepoint(mx, my):
                    self.sel = i
                    self._activate(app)
                    break

    def _activate(self, app: "App") -> None:
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
            hint="↑/↓ выбрать | Enter подтвердить | Esc выход | ЛКМ клик",
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
                    self.sel = i
                    break

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, r in enumerate(self.item_rects):
                if r.collidepoint(mx, my):
                    self.sel = i
                    # toggle / apply
                    if self.sel in (0, 1, 5):
                        self._toggle(app)
                    else:
                        self._change(app, +1)
                    return

        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_UP, pygame.K_w):
            self.sel = (self.sel - 1) % 6
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.sel = (self.sel + 1) % 6

        elif event.key in (pygame.K_LEFT, pygame.K_a):
            self._change(app, -1)

        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._change(app, +1)

        elif event.key == pygame.K_RETURN:
            self._toggle(app)

        elif event.key == pygame.K_ESCAPE:
            app.change_state(MenuState())

    # в handle_event: self.sel = (self.sel + 1) % 6   и (self.sel - 1) % 6

    def _change(self, app: "App", direction: int) -> None:
        cfg = app.cfg
        step = 0.05  # 5%
        if self.sel == 0:
            cfg.invert_mouse_x = not cfg.invert_mouse_x
        elif self.sel == 1:
            cfg.fullscreen = not cfg.fullscreen
            app.apply_video_settings()
        elif self.sel == 2:
            if not cfg.fullscreen:
                cfg.set_res_index(cfg.res_index() + direction)
                app.apply_video_settings()
        elif self.sel == 3:
            cfg.music_volume = clamp(cfg.music_volume + direction * step, 0.0, 1.0)
        elif self.sel == 4:
            cfg.sfx_volume = clamp(cfg.sfx_volume + direction * step, 0.0, 1.0)
        elif self.sel == 5:
            pass

        app.audio.apply_volumes(cfg.music_volume, cfg.sfx_volume)
        app.save_config()

    def _toggle(self, app: "App") -> None:
        cfg = app.cfg
        if self.sel == 0:
            cfg.invert_mouse_x = not cfg.invert_mouse_x
        elif self.sel == 1:
            cfg.fullscreen = not cfg.fullscreen
            app.apply_video_settings()
        elif self.sel == 5:
            app.change_state(MenuState())

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
            hint="↑/↓ выбрать | ←/→ изменить | Enter toggle | Esc назад | ЛКМ клик",
        )



class PlayState(State):
    STATE_PLAY = "play"
    STATE_DEAD = "dead"

    def __init__(self) -> None:
        self.world = World()
        self.player = Player()
        self.monster = Monster()
        self.state = self.STATE_PLAY
        self.dead_time = 0.0

        self._reset_needed = True

    def on_enter(self, app: "App") -> None:
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)
        pygame.mouse.get_rel()
        app.audio.stop_menu_music()
        app.audio.start_drone()
        self.reset(app)

    def on_exit(self, app: "App") -> None:
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)

    def reset(self, app: "App") -> None:
        self.player.x, self.player.y = app.find_empty_cell(self.world, (2, 2))
        self.player.dirx, self.player.diry = 1.0, 0.0
        self.player.planex, self.player.planey = 0.0, C.FOV_PLANE

        self.monster.x, self.monster.y = app.find_empty_cell(self.world, (self.world.w - 3, self.world.h - 3))
        self.monster.active_time = pygame.time.get_ticks() / 1000.0 + C.MONSTER_SPAWN_DELAY
        self.monster.next_replan = 0.0
        self.monster.target = None
        self.monster.tunnel_dist_cells = 999

        self.state = self.STATE_PLAY
        self.dead_time = 0.0

        app.audio.stop_scream()
        app.audio.set_game_drone_dynamic(0.1)


        pygame.mouse.get_rel()

    def handle_event(self, app: "App", event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                app.change_state(MenuState())
            elif event.key == pygame.K_r:
                self.reset(app)

    def update(self, app: "App", dt: float, t: float) -> None:
        keys = pygame.key.get_pressed()

        # mouse rotate
        mx, _ = pygame.mouse.get_rel()
        if app.cfg.invert_mouse_x:
            ang_mouse = +mx * C.MOUSE_SENS
        else:
            ang_mouse = -mx * C.MOUSE_SENS

        if abs(ang_mouse) > 1e-9:
            self.player.rotate(ang_mouse)


        # arrows rotate (optional)
        if keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]:
            angk = C.ROT_SPEED_KEYS * dt
            angk = +angk if keys[pygame.K_LEFT] else -angk
            self.player.rotate(angk)

        if self.state != self.STATE_PLAY:
            app.audio.set_game_drone_dynamic(0.06)
            return


        # movement
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

        nx = self.player.x + moveX
        ny = self.player.y + moveY
        if not self.world.is_wall_cell(int(nx), int(self.player.y)):
            self.player.x = nx
        if not self.world.is_wall_cell(int(self.player.x), int(ny)):
            self.player.y = ny

        # monster logic
        if t < self.monster.active_time:
            app.audio.set_game_drone_dynamic(0.10)
            return

        # tunnel replan
        if t >= self.monster.next_replan:
            self.monster.next_replan = t + C.REPLAN_INTERVAL

            px_cell, py_cell = int(self.player.x), int(self.player.y)
            dist_map = compute_dist_map(self.world, px_cell, py_cell)

            mx_cell, my_cell = int(self.monster.x), int(self.monster.y)
            d = dist_map[my_cell][mx_cell]
            self.monster.tunnel_dist_cells = d if d != -1 else 999

            nxt = pick_next_cell_for_monster(dist_map, mx_cell, my_cell)
            if nxt is not None:
                self.monster.target = (nxt[0] + 0.5, nxt[1] + 0.5)
            else:
                self.monster.target = (self.player.x, self.player.y)

        # drone volume by tunnel distance
        if self.monster.tunnel_dist_cells >= 999:
            app.audio.set_game_drone_dynamic(0.06)
        else:
            v = 1.0 - (self.monster.tunnel_dist_cells / C.SOUND_AUDIBLE_CELLS)
            v = clamp(v, 0.0, 1.0)
            v = v ** C.SOUND_CURVE
            app.audio.set_game_drone_dynamic(0.06 + 0.94 * v)


        # move monster toward target
        if self.monster.target is None:
            self.monster.target = (self.player.x, self.player.y)

        tx, ty = self.monster.target
        mdx = tx - self.monster.x
        mdy = ty - self.monster.y
        md = math.hypot(mdx, mdy) + 1e-9

        step = (C.MOVE_SPEED * C.RUN_MULT) * dt  # скорость "как человек с shift"
        mx_try = self.monster.x + (mdx / md) * step
        my_try = self.monster.y + (mdy / md) * step

        if not self.world.is_wall_cell(int(mx_try), int(self.monster.y)):
            self.monster.x = mx_try
        if not self.world.is_wall_cell(int(self.monster.x), int(my_try)):
            self.monster.y = my_try

        if math.hypot(self.monster.x - tx, self.monster.y - ty) < 0.18:
            self.monster.target = None

        # kill
        if math.hypot(self.player.x - self.monster.x, self.player.y - self.monster.y) < C.KILL_DIST:
            self.state = self.STATE_DEAD
            self.dead_time = t
            app.audio.play_scream()

    def draw(self, app: "App") -> None:
        t = pygame.time.get_ticks() / 1000.0
        show_monster = t >= self.monster.active_time
        is_dead = (self.state == self.STATE_DEAD)
        app.renderer.draw_play(self.world, self.player, self.monster, show_monster, is_dead)


# ============================================================
# 9) App (DI container + main loop)
# ============================================================

class App:
    def __init__(self) -> None:
        pygame.init()
        self.cfg = RuntimeConfig()
        self.load_config()

        self.screen = self._create_screen()
        pygame.display.set_caption("ESCAPE FROM FAMCS")

        self.clock = pygame.time.Clock()
        self.running = True

        # Assets
        self.wall_tex = make_backrooms_wall_texture(C.TEXTURE_SIZE)
        self.monster_img = self._load_monster()

        # Subsystems
        self.audio = AudioSystem()
        self.audio.init()
        self.audio.apply_volumes(self.cfg.music_volume, self.cfg.sfx_volume)

        self.renderer = Renderer(self.screen, self.wall_tex, self.monster_img)

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


    def _load_monster(self) -> pygame.Surface:
        path = resource_path(C.MONSTER_FILE)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Не найден '{C.MONSTER_FILE}'. Ожидается по пути:\n{path}")
        img = pygame.image.load(path).convert()
        img = pygame.transform.smoothscale(img, (C.TEXTURE_SIZE, C.TEXTURE_SIZE))
        return img

    @staticmethod
    def find_empty_cell(world: World, prefer: Tuple[int, int]) -> Tuple[float, float]:
        px, py = prefer
        if not world.is_wall_cell(px, py):
            return px + 0.5, py + 0.5
        for y in range(1, world.h - 1):
            for x in range(1, world.w - 1):
                if not world.is_wall_cell(x, y):
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
    # Windows:
    # pyinstaller --noconfirm --onefile --windowed --name TrushHORROR ^
    #   --add-data "trush.jpg;." --add-data "scream.mp3;." horror_game.py
    #
    # macOS:
    # pyinstaller --noconfirm --windowed --name TrushHORROR \
    #   --add-data "trush.jpg:." --add-data "scream.mp3:." horror_game.py
    App().run()
