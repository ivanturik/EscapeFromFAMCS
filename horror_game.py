import os
import math
import random
from collections import deque
from array import array

import pygame

import sys

def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


# ----------------------------
# Экран / рендер
# ----------------------------
SCREEN_W, SCREEN_H = 960, 540
RENDER_W, RENDER_H = 320, 180  # меньше = быстрее

# ----------------------------
# Управление
# ----------------------------
MOVE_SPEED = 2.6
RUN_MULT = 1.75

ROT_SPEED_KEYS = 2.2     # рад/сек для стрелок
MOUSE_SENS = 0.0025      # рад/пиксель
MOUSE_INVERT_X = False   # если у тебя снова станет "наоборот" — поставь True

# ----------------------------
# Камера / атмосфера
# ----------------------------
FOV_PLANE = 0.66
FOG_STRENGTH = 0.055
CEIL_COLOR = (205, 195, 120)
FLOOR_COLOR = (115, 105, 75)

# ----------------------------
# Текстуры
# ----------------------------
TEXTURE_SIZE = 256
SCREAM_FILE = "scream.mp3"

# ----------------------------
# Монстр
# скорость = скорости игрока с Shift
# ----------------------------
MONSTER_SPEED = MOVE_SPEED * RUN_MULT
MONSTER_SPAWN_DELAY = 1.0
KILL_DIST = 0.65

# ----------------------------
# Путь / звук
# ----------------------------
REPLAN_INTERVAL = 0.12      # чаще пересчёт пути => “ближайший путь по туннелю”
SOUND_AUDIBLE_CELLS = 22    # с какого расстояния по туннелю начинает реально расти громкость
SOUND_CURVE = 0.60          # <1 => громче уже на “не близком” расстоянии

# ----------------------------
# Оптимизация у стены (анти-лаг)
# ----------------------------
MIN_WALL_DIST = 0.18
MAX_LINEHEIGHT = RENDER_H * 4

# ----------------------------
# Карта (0 = проход, 1 = стена)
# ----------------------------
WORLD_MAP = [
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
MAP_H = len(WORLD_MAP)
MAP_W = len(WORLD_MAP[0])

def is_wall(mx, my):
    if mx < 0 or mx >= MAP_W or my < 0 or my >= MAP_H:
        return True
    return WORLD_MAP[my][mx] == "1"

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

# ----------------------------
# Текстура "обои backrooms"
# ----------------------------
def make_backrooms_wall_texture(size=256):
    surf = pygame.Surface((size, size))
    surf.fill((210, 198, 120))
    for x in range(0, size, 18):
        col = (200 + random.randint(-8, 8), 190 + random.randint(-8, 8), 115 + random.randint(-8, 8))
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

# ----------------------------
# Звук (без файлов): гул + визг
# ----------------------------
def init_audio():
    pygame.mixer.pre_init(44100, -16, 1, 512)
    pygame.mixer.init()

def sound_drone(duration=3.5, sr=44100):
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
    snd.set_volume(0.10)
    return snd

def sound_scream(duration=0.45, sr=44100):
    n = int(duration * sr)
    samples = array("h")
    for i in range(n):
        t = i / sr
        f = 320 + 900 * (t / duration)
        env = max(0.0, 1.0 - (t / duration)) ** 0.4
        v = (0.8 * math.sin(2 * math.pi * f * t) + 0.2 * (random.random() * 2 - 1)) * env
        v = clamp(v, -1.0, 1.0)
        samples.append(int(v * 32767))
    snd = pygame.mixer.Sound(buffer=samples.tobytes())
    snd.set_volume(0.9)
    return snd

# ----------------------------
# Виньетка
# ----------------------------
def vignette_surface(w, h):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w / 2, h / 2
    maxd = math.hypot(cx, cy)
    for y in range(h):
        for x in range(w):
            d = math.hypot(x - cx, y - cy) / maxd
            a = int(170 * (d ** 1.8))
            surf.set_at((x, y), (0, 0, 0, a))
    return surf

# ----------------------------
# BFS по сетке (короткий путь по туннелю)
# ----------------------------
DIRS4 = [(1,0),(-1,0),(0,1),(0,-1)]

def compute_dist_map(px, py):
    dist = [[-1] * MAP_W for _ in range(MAP_H)]
    q = deque()
    dist[py][px] = 0
    q.append((px, py))
    while q:
        x, y = q.popleft()
        d = dist[y][x]
        for dx, dy in DIRS4:
            nx, ny = x + dx, y + dy
            if 0 <= nx < MAP_W and 0 <= ny < MAP_H and dist[ny][nx] == -1 and not is_wall(nx, ny):
                dist[ny][nx] = d + 1
                q.append((nx, ny))
    return dist

def pick_next_cell_for_monster(dist, mx, my):
    best = None
    best_d = 10**9
    for dx, dy in DIRS4:
        nx, ny = mx + dx, my + dy
        if 0 <= nx < MAP_W and 0 <= ny < MAP_H and dist[ny][nx] != -1:
            if dist[ny][nx] < best_d:
                best_d = dist[ny][nx]
                best = (nx, ny)
    return best

# ----------------------------
# Спрайт в raycasting (billboard)
# ----------------------------
def draw_sprite(render, zbuffer, sprite_img, player, cam, sprite_pos):
    posX, posY, dirX, dirY = player
    planeX, planeY = cam
    sprX = sprite_pos[0] - posX
    sprY = sprite_pos[1] - posY

    inv_det = 1.0 / (planeX * dirY - dirX * planeY + 1e-9)
    transformX = inv_det * (dirY * sprX - dirX * sprY)
    transformY = inv_det * (-planeY * sprX + planeX * sprY)

    if transformY <= 0.06:
        return

    sprite_screen_x = int((RENDER_W / 2) * (1 + transformX / transformY))
    sprite_h = abs(int(RENDER_H / transformY))
    sprite_h = clamp(sprite_h, 6, RENDER_H * 3)
    sprite_w = sprite_h

    draw_start_y = -sprite_h // 2 + RENDER_H // 2
    draw_end_y = sprite_h // 2 + RENDER_H // 2
    draw_start_y = max(0, draw_start_y)
    draw_end_y = min(RENDER_H - 1, draw_end_y)

    draw_start_x = -sprite_w // 2 + sprite_screen_x
    draw_end_x = sprite_w // 2 + sprite_screen_x

    spr_scaled = pygame.transform.smoothscale(sprite_img, (sprite_w, sprite_h))

    fog_factor = math.exp(-FOG_STRENGTH * transformY * 22.0)
    mul = int(255 * fog_factor)
    mul = clamp(mul, 35, 255)
    spr_scaled = spr_scaled.copy()
    spr_scaled.fill((mul, mul, mul), special_flags=pygame.BLEND_MULT)

    vis_h = draw_end_y - draw_start_y
    if vis_h <= 0:
        return

    offset_y = draw_start_y - (-sprite_h // 2 + RENDER_H // 2)

    for stripe in range(draw_start_x, draw_end_x):
        if stripe < 0 or stripe >= RENDER_W:
            continue
        if transformY >= zbuffer[stripe]:
            continue

        tx = stripe - draw_start_x
        if 0 <= tx < sprite_w:
            col = spr_scaled.subsurface((tx, offset_y, 1, vis_h))
            render.blit(col, (stripe, draw_start_y))

# ----------------------------
# Main
# ----------------------------
def main():
    init_audio()
    pygame.init()

    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Backrooms 3D — Tunnel distance sound + Same run speed monster")
    clock = pygame.time.Clock()

    pygame.event.set_grab(True)
    pygame.mouse.set_visible(False)
    pygame.mouse.get_rel()

    render = pygame.Surface((RENDER_W, RENDER_H))
    wall_tex = make_backrooms_wall_texture(TEXTURE_SIZE)

    monster_path = resource_path("trush.jpg")
    if not os.path.exists(monster_path):
        raise FileNotFoundError(f"Не найден 'trush.jpg'. Ожидается по пути:\n{monster_path}")

    monster_img = pygame.image.load(monster_path).convert()
    monster_img = pygame.transform.smoothscale(monster_img, (TEXTURE_SIZE, TEXTURE_SIZE))

    vin = vignette_surface(SCREEN_W, SCREEN_H)
    font = pygame.font.SysFont("consolas", 18)
    big_font = pygame.font.SysFont("consolas", 44, bold=True)

    drone = sound_drone()
    drone.play(loops=-1)

    # отдельный канал для крика, чтобы не терялся
    scream_channel = pygame.mixer.Channel(1)
    scream_channel.set_volume(1.0)

    # грузим scream.mp3 (и для .py, и для .exe)
    scream_path = resource_path(SCREAM_FILE)
    if not os.path.exists(scream_path):
        raise FileNotFoundError(f"Не найден '{SCREAM_FILE}'. Ожидается по пути:\n{scream_path}")

    scream_sound = None
    use_music = False

    # Пытаемся как Sound (обычно быстро)
    try:
        scream_sound = pygame.mixer.Sound(scream_path)
        scream_sound.set_volume(1.0)
    except Exception:
        # Если MP3 не поддерживается как Sound — будем играть через mixer.music
        use_music = True

    STATE_PLAY = "play"
    STATE_DEAD = "dead"
    state = STATE_PLAY
    dead_time = 0.0

    # Игрок
    posX, posY = 2.5, 2.5
    dirX, dirY = 1.0, 0.0
    planeX, planeY = 0.0, FOV_PLANE

    # Монстр
    monX, monY = 0.0, 0.0
    mon_active_time = 0.0
    next_replan_time = 0.0
    mon_target = None
    path_dist_cells = 999

    def find_empty_cell(prefer=(2, 2)):
        px, py = prefer
        if not is_wall(px, py):
            return px + 0.5, py + 0.5
        for y in range(1, MAP_H - 1):
            for x in range(1, MAP_W - 1):
                if not is_wall(x, y):
                    return x + 0.5, y + 0.5
        return 2.5, 2.5

    def reset():
        nonlocal state, dead_time
        nonlocal posX, posY, dirX, dirY, planeX, planeY
        nonlocal monX, monY, mon_active_time, next_replan_time, mon_target, path_dist_cells

        posX, posY = find_empty_cell((2, 2))
        dirX, dirY = 1.0, 0.0
        planeX, planeY = 0.0, FOV_PLANE

        monX, monY = find_empty_cell((MAP_W - 3, MAP_H - 3))
        mon_active_time = pygame.time.get_ticks() / 1000.0 + MONSTER_SPAWN_DELAY
        next_replan_time = 0.0
        mon_target = None
        path_dist_cells = 999

        state = STATE_PLAY
        dead_time = 0.0
        drone.set_volume(0.10)
        scream_channel.stop()
        pygame.mixer.music.stop()

    reset()

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        if dt > 0.05:
            dt = 0.05
        t = pygame.time.get_ticks() / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            running = False
        if keys[pygame.K_r]:
            reset()

        # ----------------------------
        # Поворот мышью (вправо = вправо)
        # ----------------------------
        mx, my = pygame.mouse.get_rel()
        if MOUSE_INVERT_X:
            mx = -mx

        ang = mx * MOUSE_SENS
        if abs(ang) > 1e-8:
            cos_a, sin_a = math.cos(ang), math.sin(ang)
            oldDirX = dirX
            dirX = dirX * cos_a - dirY * sin_a
            dirY = oldDirX * sin_a + dirY * cos_a
            oldPlaneX = planeX
            planeX = planeX * cos_a - planeY * sin_a
            planeY = oldPlaneX * sin_a + planeY * cos_a

        # Стрелки тоже поворачивают
        if keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]:
            angk = ROT_SPEED_KEYS * dt
            angk = +angk if keys[pygame.K_LEFT] else -angk
            cos_a, sin_a = math.cos(angk), math.sin(angk)
            oldDirX = dirX
            dirX = dirX * cos_a - dirY * sin_a
            dirY = oldDirX * sin_a + dirY * cos_a
            oldPlaneX = planeX
            planeX = planeX * cos_a - planeY * sin_a
            planeY = oldPlaneX * sin_a + planeY * cos_a

        # ----------------------------
        # Игровая логика
        # ----------------------------
        if state == STATE_PLAY:
            speed = MOVE_SPEED * (RUN_MULT if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else 1.0)

            moveX = moveY = 0.0
            if keys[pygame.K_w]:
                moveX += dirX * speed * dt
                moveY += dirY * speed * dt
            if keys[pygame.K_s]:
                moveX -= dirX * speed * dt
                moveY -= dirY * speed * dt
            if keys[pygame.K_a]:
                moveX -= planeX * speed * dt
                moveY -= planeY * speed * dt
            if keys[pygame.K_d]:
                moveX += planeX * speed * dt
                moveY += planeY * speed * dt

            nx = posX + moveX
            ny = posY + moveY
            if not is_wall(int(nx), int(posY)):
                posX = nx
            if not is_wall(int(posX), int(ny)):
                posY = ny

            # Монстр активируется
            if t >= mon_active_time:
                # пересчёт "короткого пути по туннелю" + следующей клетки
                if t >= next_replan_time:
                    next_replan_time = t + REPLAN_INTERVAL

                    px_cell, py_cell = int(posX), int(posY)
                    dist_map = compute_dist_map(px_cell, py_cell)

                    mx_cell, my_cell = int(monX), int(monY)
                    d = dist_map[my_cell][mx_cell]
                    path_dist_cells = d if d != -1 else 999

                    nxt = pick_next_cell_for_monster(dist_map, mx_cell, my_cell)
                    if nxt is not None:
                        mon_target = (nxt[0] + 0.5, nxt[1] + 0.5)
                    else:
                        mon_target = (posX, posY)

                # громкость по "туннельной" дистанции
                if path_dist_cells >= 999:
                    drone.set_volume(0.06)
                else:
                    v = 1.0 - (path_dist_cells / SOUND_AUDIBLE_CELLS)
                    v = clamp(v, 0.0, 1.0)
                    v = v ** SOUND_CURVE   # чтобы было громче уже на НЕ близком расстоянии
                    drone.set_volume(0.06 + 0.94 * v)

                # движение монстра к цели
                if mon_target is None:
                    mon_target = (posX, posY)

                tx, ty = mon_target
                mdx = tx - monX
                mdy = ty - monY
                md = math.hypot(mdx, mdy) + 1e-9

                step = MONSTER_SPEED * dt
                mx_try = monX + (mdx / md) * step
                my_try = monY + (mdy / md) * step

                if not is_wall(int(mx_try), int(monY)):
                    monX = mx_try
                if not is_wall(int(monX), int(my_try)):
                    monY = my_try

                if math.hypot(monX - tx, monY - ty) < 0.18:
                    mon_target = None

                # смерть по реальной близости
                if math.hypot(posX - monX, posY - monY) < KILL_DIST:
                    state = STATE_DEAD
                    dead_time = t

                    # приглушаем фон, чтобы крик был сильнее
                    drone.set_volume(0.0)

                    # играем scream.mp3
                    if not use_music and scream_sound is not None:
                        scream_channel.stop()
                        scream_channel.play(scream_sound)
                    else:
                        pygame.mixer.music.stop()
                        pygame.mixer.music.load(scream_path)
                        pygame.mixer.music.play(0)

            else:
                drone.set_volume(0.10)

        else:
            drone.set_volume(0.06)

        # ----------------------------
        # Рендер: потолок / пол
        # ----------------------------
        render.fill(CEIL_COLOR)
        pygame.draw.rect(render, FLOOR_COLOR, (0, RENDER_H // 2, RENDER_W, RENDER_H // 2))

        # ----------------------------
        # Raycasting стен
        # ----------------------------
        zbuffer = [1e9] * RENDER_W
        tex_w, tex_h = wall_tex.get_size()

        for x in range(RENDER_W):
            cameraX = 2.0 * x / RENDER_W - 1.0
            rayDirX = dirX + planeX * cameraX
            rayDirY = dirY + planeY * cameraX

            mapX = int(posX)
            mapY = int(posY)

            deltaDistX = abs(1.0 / rayDirX) if rayDirX != 0 else 1e30
            deltaDistY = abs(1.0 / rayDirY) if rayDirY != 0 else 1e30

            if rayDirX < 0:
                stepX = -1
                sideDistX = (posX - mapX) * deltaDistX
            else:
                stepX = 1
                sideDistX = (mapX + 1.0 - posX) * deltaDistX

            if rayDirY < 0:
                stepY = -1
                sideDistY = (posY - mapY) * deltaDistY
            else:
                stepY = 1
                sideDistY = (mapY + 1.0 - posY) * deltaDistY

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
                if is_wall(mapX, mapY):
                    hit = True
                    break
            if not hit:
                continue

            if side == 0:
                perpWallDist = (mapX - posX + (1 - stepX) / 2) / (rayDirX if rayDirX != 0 else 1e-6)
            else:
                perpWallDist = (mapY - posY + (1 - stepY) / 2) / (rayDirY if rayDirY != 0 else 1e-6)

            perpWallDist = max(perpWallDist, MIN_WALL_DIST)
            zbuffer[x] = perpWallDist

            lineHeight = int(RENDER_H / perpWallDist)
            lineHeight = min(lineHeight, MAX_LINEHEIGHT)

            drawStart = -lineHeight // 2 + RENDER_H // 2
            drawEnd = lineHeight // 2 + RENDER_H // 2
            if drawStart < 0:
                drawStart = 0
            if drawEnd >= RENDER_H:
                drawEnd = RENDER_H - 1

            if side == 0:
                wallX = posY + perpWallDist * rayDirY
            else:
                wallX = posX + perpWallDist * rayDirX
            wallX -= math.floor(wallX)

            texX = int(wallX * tex_w)
            if side == 0 and rayDirX > 0:
                texX = tex_w - texX - 1
            if side == 1 and rayDirY < 0:
                texX = tex_w - texX - 1
            texX = clamp(texX, 0, tex_w - 1)

            visible_h = drawEnd - drawStart
            if visible_h <= 0:
                continue

            col = wall_tex.subsurface((texX, 0, 1, tex_h))
            col_scaled = pygame.transform.scale(col, (1, visible_h))

            shade_mul = 0.78 if side == 1 else 1.0
            fog_factor = math.exp(-FOG_STRENGTH * perpWallDist * 22.0)
            mul = int(255 * fog_factor * shade_mul)
            mul = clamp(mul, 20, 255)

            col_scaled = col_scaled.copy()
            col_scaled.fill((mul, mul, mul), special_flags=pygame.BLEND_MULT)
            render.blit(col_scaled, (x, drawStart))

        # ----------------------------
        # Монстр
        # ----------------------------
        if t >= mon_active_time and state == STATE_PLAY:
            draw_sprite(
                render,
                zbuffer,
                monster_img,
                (posX, posY, dirX, dirY),
                (planeX, planeY),
                (monX, monY),
            )

        # ----------------------------
        # Вывод
        # ----------------------------
        frame = pygame.transform.scale(render, (SCREEN_W, SCREEN_H))
        screen.blit(frame, (0, 0))
        screen.blit(vin, (0, 0))

        for _ in range(80):
            xx = random.randrange(SCREEN_W)
            yy = random.randrange(SCREEN_H)
            c = random.randrange(10, 28)
            screen.set_at((xx, yy), (c, c, c))

        screen.blit(font.render("WASD — движение | мышь/←→ — поворот | Shift — бег | R — заново | Esc — выход", True, (10, 10, 10)), (12, 10))

        if state == STATE_DEAD:
            # Всегда показываем скример, пока не нажмут R
            jump = pygame.transform.scale(monster_img, (SCREEN_W, SCREEN_H))
            screen.blit(jump, (0, 0))

            txt = big_font.render("ПЕРЕСДАЧА!", True, (240, 240, 240))
            screen.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2, 140))
            txt2 = font.render("Нажми R чтобы начать заново", True, (240, 240, 240))
            screen.blit(txt2, (SCREEN_W // 2 - txt2.get_width() // 2, 210))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
