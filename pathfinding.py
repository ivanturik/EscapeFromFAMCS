# pathfinding.py
from collections import deque
from typing import Any, List, Optional, Tuple

DIRS4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def compute_dist_map(
    world: Any,
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
