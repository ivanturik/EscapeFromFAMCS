# world.py
import random
import math
from dataclasses import dataclass
from collections import deque
from typing import List, Tuple, Any

from pathfinding import DIRS4


@dataclass(frozen=True)
class MapSpec:
    grid: List[str]
    wrap_portals: Tuple[Tuple[str, float, float], ...] = tuple()


BASE_MAP_VARIANTS: Tuple[MapSpec, ...] = (
    MapSpec(
        grid=[
            "111111011111111",
            "100000000100001",
            "101111110101101",
            "101000010101001",
            "101011010101101",
            "101010010001001",
            "101010011101101",
            "101000000001001",
            "101111011101101",
            "100000010000001",
            "111111011111111",
        ],
        wrap_portals=(("N", 6.0, 7.0), ("S", 6.0, 7.0)),
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


def generate_maze_grid(w: int, h: int, loop_chance: float = 0.07, room_attempts: int = 22) -> List[str]:
    w = _odd(max(w, 25))
    h = _odd(max(h, 25))

    g = [["1"] * w for _ in range(h)]

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

    for _ in range(room_attempts):
        rw = random.randrange(3, 8)
        rh = random.randrange(3, 8)
        x0 = random.randrange(1, w - rw - 1)
        y0 = random.randrange(1, h - rh - 1)
        for yy in range(y0, y0 + rh):
            for xx in range(x0, x0 + rw):
                g[yy][xx] = "0"

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

    for x in range(w):
        g[0][x] = "1"
        g[h - 1][x] = "1"
    for y in range(h):
        g[y][0] = "1"
        g[y][w - 1] = "1"

    # убрать изолированные острова
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
            for dx, dy in DIRS4:
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


MAP_VARIANTS: Tuple[MapSpec, ...] = BASE_MAP_VARIANTS + tuple(generate_maze_spec() for _ in range(6))


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

    def is_wall_cell(self, mx: int, my: int) -> bool:
        return self.cell_at(mx, my) == "1"

    def is_blocking_cell(self, mx: int, my: int) -> bool:
        cell = self.cell_at(mx, my)
        return cell in ("1", "D")

    def is_wall_at(self, x: float, y: float) -> bool:
        return self.is_blocking_cell(int(x), int(y))

    def collides_circle(self, x: float, y: float, r: float) -> bool:
        for ox in (-r, r):
            for oy in (-r, r):
                if self.is_blocking_cell(int(x + ox), int(y + oy)):
                    return True
        return False

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

    def apply_wrap(self, obj: Any) -> None:
        if not self.wrap_portals:
            return

        edge = 0.35
        wrapped = False

        if obj.y < edge and self.portal_allows("N", obj.x):
            obj.y += (self.h - 1)
            wrapped = True
        elif obj.y > (self.h - edge) and self.portal_allows("S", obj.x):
            obj.y -= (self.h - 1)
            wrapped = True

        if obj.x < edge and self.portal_allows("W", obj.y):
            obj.x += (self.w - 1)
            wrapped = True
        elif obj.x > (self.w - edge) and self.portal_allows("E", obj.y):
            obj.x -= (self.w - 1)
            wrapped = True

        if wrapped:
            obj.x, obj.y = self._snap_to_open(obj.x, obj.y)
