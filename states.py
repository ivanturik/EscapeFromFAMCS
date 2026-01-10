# states.py
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

import pygame

from settings import C, clamp
from world import World, MAP_VARIANTS
from entities import Player, Monster
from pathfinding import compute_dist_map, pick_next_cell_for_monster, DIRS4

if TYPE_CHECKING:
    from app import App


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

    def _set_selected(self, app: "App", idx: int) -> None:
        if idx != self.sel:
            self.sel = idx
            app.audio.play_ui_hover()

    def _change(self, app: "App", direction: int) -> None:
        cfg = app.cfg
        step = 0.05
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

        # мышь: аккумулируем rel
        self._mouse_dx = 0.0
        self._mouse_smooth = 0.0

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
            ) = self._pick_door(pick_reachable)

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

        px_cell, py_cell = int(self.player.x), int(self.player.y)
        dist_map = compute_dist_map(self.world, px_cell, py_cell, self.world.is_blocking_cell)

        candidates: List[Tuple[int, int, int]] = []
        for y, row in enumerate(dist_map):
            for x, d in enumerate(row):
                if d >= 0 and not self.world.is_blocking_cell(x, y):
                    candidates.append((d, x, y))

        if not candidates:
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
            return all(math.hypot(cx - ax, cy - ay) > 4.0 for ax, ay in avoid)

        far = [(d, x, y) for (d, x, y) in candidates if d >= min_d and far_ok(x, y)]
        pool = far if far else [(d, x, y) for (d, x, y) in candidates if far_ok(x, y)]
        if not pool:
            pool = candidates

        pool.sort(reverse=True)

        for _ in range(self.monster_count):
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

    def _pick_door(self, pick_unique: Any) -> Tuple[Tuple[float, float], Tuple[float, float], Tuple[int, int], str]:
        tries = 0
        while tries < 250:
            trigger = pick_unique((self.world.w - 3, self.world.h - 3), [self.spawn_point])
            mx, my = int(trigger[0]), int(trigger[1])

            if self.world.is_wall_cell(mx, my):
                tries += 1
                continue

            candidates = [
                (-1, 0, "vertical"),
                (1, 0, "vertical"),
                (0, -1, "horizontal"),
                (0, 1, "horizontal"),
            ]
            random.shuffle(candidates)

            for dx, dy, ori in candidates:
                wx, wy = mx + dx, my + dy
                if self.world.is_wall_cell(wx, wy):
                    door_trigger = (mx + 0.5, my + 0.5)

                    if ori == "vertical":
                        plane_x = float(mx) if dx == -1 else float(mx + 1)
                        plane_y = my + 0.5
                        door_plane = (plane_x, plane_y)
                    else:
                        plane_y = float(my) if dy == -1 else float(my + 1)
                        plane_x = mx + 0.5
                        door_plane = (plane_x, plane_y)

                    door_cell = (wx, wy)
                    return door_trigger, door_plane, door_cell, ori

            tries += 1

        mx, my = 2, 2
        door_trigger = (mx + 0.5, my + 0.5)
        door_plane = (mx + 1.0, my + 0.5)
        door_cell = (mx + 1, my)
        return door_trigger, door_plane, door_cell, "vertical"

    def handle_event(self, app: "App", event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._mouse_dx += event.rel[0]

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

        mx = self._mouse_dx
        self._mouse_dx = 0.0
        mx = clamp(mx, -120.0, 120.0)
        self._mouse_smooth = 0.6 * self._mouse_smooth + 0.4 * mx
        mx = self._mouse_smooth

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

        if not self.world.collides_circle(nx, self.player.y, r):
            self.player.x = nx
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

            self.world.apply_wrap(m)

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
        self.door_trigger = tuple(data.get("door_trigger", self.door_trigger))  # type: ignore
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

    def draw(self, app: "App") -> None:
        items = self.items.copy()
        if self.notice:
            items.append(self.notice)
        self.item_rects = app.renderer.draw_menu(title="Paused", items=items, selected=self.sel, hint="")


class DeathScreamerState(State):
    def __init__(self, play_state: PlayState, duration: Optional[float] = None) -> None:
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

    def draw(self, app: "App") -> None:
        app.renderer.draw_fullscreen_image(app.end_img, "You failed")
