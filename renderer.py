# renderer.py
import math
import random
from typing import List, Optional, Tuple

import pygame

from settings import C, clamp


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
        self.victory_img = victory_img
        self.end_img = end_img

        self.door_overlay = pygame.transform.smoothscale(door_img, (C.TEXTURE_SIZE, C.TEXTURE_SIZE))
        self.door_wall_tex = self.wall_tex.copy()
        self.door_wall_tex.blit(self.door_overlay, (0, 0))
        self.door_tex = self.door_wall_tex

        self.font = pygame.font.SysFont("consolas", 18)
        self.big_font = pygame.font.SysFont("consolas", 44, bold=True)
        self.logo_font = pygame.font.SysFont("consolas", 74, bold=True)

        self._rebuild_overlay()

    def set_screen(self, new_screen: pygame.Surface) -> None:
        self.screen = new_screen
        self._rebuild_overlay()

    def _rebuild_overlay(self) -> None:
        w, h = self.screen.get_size()
        self.vin = vignette_surface(w, h)

    @staticmethod
    def _ru_plural(n: int, one: str, two: str, five: str) -> str:
        n = abs(int(n))
        n10 = n % 10
        n100 = n % 100
        if 11 <= n100 <= 14:
            return five
        if n10 == 1:
            return one
        if 2 <= n10 <= 4:
            return two
        return five

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

    def draw_menu(self, title: str, items: List[str], selected: int, hint: str = "", famcs_logo: bool = False) -> List[pygame.Rect]:
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

    # ============================================================
    # Play render
    # ============================================================

    def draw_play(
        self,
        world,
        player,
        monsters,
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

        # ✅ ДВЕРЬ РИСУЕТСЯ ВСЕГДА (чтобы не исчезала после 3 зачёток)
        if door_plane_pos is not None:
            self._draw_door_plane(zbuffer, player, door_plane_pos, door_orientation, dim=False)

        sprites = []

        if show_monster and not is_dead:
            t_now = pygame.time.get_ticks() / 1000.0
            for m in monsters:
                if t_now >= m.active_time:
                    sprites.append(("monster", (m.x, m.y), self.monster_img, False, 1.10))

        for pos, collected in zip(zachetki, zachet_collected):
            if not collected:
                sprites.append(("zachet", pos, self.zachet_img, False, 1.0))

        def _dsq(pp: Tuple[float, float]) -> float:
            dx = pp[0] - player.x
            dy = pp[1] - player.y
            return dx * dx + dy * dy

        sprites.sort(key=lambda s: _dsq(s[1]), reverse=True)

        for _, pos, tex, dim, scale in sprites:
            self._draw_billboard(zbuffer, player, pos, tex, dim=dim, scale=scale)

        w, h = self.screen.get_size()
        frame = pygame.transform.scale(self.render, (w, h))
        self.screen.blit(frame, (0, 0))
        self.screen.blit(self.vin, (0, 0))

        for _ in range(C.NOISE_DOTS):
            xx = random.randrange(w)
            yy = random.randrange(h)
            c = random.randrange(10, 28)
            self.screen.set_at((xx, yy), (c, c, c))

        if is_dead:
            jump = pygame.transform.scale(self.monster_img, (w, h))
            self.screen.blit(jump, (0, 0))
            txt = self.big_font.render("ПЕРЕСДАЧА!", True, (240, 240, 240))
            self.screen.blit(txt, (w // 2 - txt.get_width() // 2, int(h * 0.26)))
            txt2 = self.font.render("Нажми R чтобы начать заново", True, (240, 240, 240))
            self.screen.blit(txt2, (w // 2 - txt2.get_width() // 2, int(h * 0.38)))
            return

        # HUD
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

        # ✅ Подсказка у двери: сколько ещё зачёток
        if door_pos is not None and total > 0 and (not door_open):
            dist_to_door = math.hypot(player.x - door_pos[0], player.y - door_pos[1])
            if dist_to_door < 1.15:
                remain = total - got
                if remain > 0:
                    word = self._ru_plural(remain, "зачётку", "зачётки", "зачёток")
                    msg = f"Дверь закрыта. Нужно собрать ещё {remain} {word}"
                    hint = self.font.render(msg, True, (235, 235, 235))
                    self.screen.blit(hint, (w // 2 - hint.get_width() // 2, int(h * 0.82)))

        if show_minimap:
            active_zachetki = [p for p, c in zip(zachetki, zachet_collected) if not c]
            self._draw_minimap(world, player, door_pos, active_zachetki)

    def _draw_minimap(self, world, player, door_pos, zachetki) -> None:
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

        for zpos in zachetki:
            zx = int(zpos[0] * cell)
            zy = int(zpos[1] * cell)
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

    # ============================================================
    # Raycasting
    # ============================================================

    def _cast_walls(self, world, p, zbuffer: List[float]) -> None:
        tex_w, tex_h = self.wall_tex.get_size()
        max_steps = world.w * world.h * 4

        px, py = p.x, p.y
        dirx, diry = p.dirx, p.diry
        planex, planey = p.planex, p.planey

        for x in range(C.RENDER_W):
            cameraX = 2.0 * x / C.RENDER_W - 1.0
            rayDirX = dirx + planex * cameraX
            rayDirY = diry + planey * cameraX

            mapX = int(px)
            mapY = int(py)

            deltaDistX = abs(1.0 / rayDirX) if abs(rayDirX) > 1e-12 else 1e30
            deltaDistY = abs(1.0 / rayDirY) if abs(rayDirY) > 1e-12 else 1e30

            if rayDirX < 0:
                stepX = -1
                sideDistX = (px - mapX) * deltaDistX
            else:
                stepX = 1
                sideDistX = (mapX + 1.0 - px) * deltaDistX

            if rayDirY < 0:
                stepY = -1
                sideDistY = (py - mapY) * deltaDistY
            else:
                stepY = 1
                sideDistY = (mapY + 1.0 - py) * deltaDistY

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

                # порталы по краям (как у тебя)
                if mapY < 0:
                    x_at = px + rayDirX * traveled
                    if world.portal_allows("N", x_at):
                        mapY = world.h - 1
                    else:
                        hit = True
                        cell_type = "1"
                        perp = traveled
                        break
                elif mapY >= world.h:
                    x_at = px + rayDirX * traveled
                    if world.portal_allows("S", x_at):
                        mapY = 0
                    else:
                        hit = True
                        cell_type = "1"
                        perp = traveled
                        break

                if mapX < 0:
                    y_at = py + rayDirY * traveled
                    if world.portal_allows("W", y_at):
                        mapX = world.w - 1
                    else:
                        hit = True
                        cell_type = "1"
                        perp = traveled
                        break
                elif mapX >= world.w:
                    y_at = py + rayDirY * traveled
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
                wallX = py + perp * rayDirY
            else:
                wallX = px + perp * rayDirX
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

    def _draw_door_plane(self, zbuffer: List[float], p, door_pos: Tuple[float, float], orientation: str, dim: bool = True) -> None:
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

    def _draw_billboard(self, zbuffer: List[float], p, spr_pos: Tuple[float, float], tex: pygame.Surface, dim: bool = False, scale: float = 1.0) -> None:
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
