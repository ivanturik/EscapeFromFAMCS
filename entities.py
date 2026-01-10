# entities.py
import math
from dataclasses import dataclass
from typing import Optional, Tuple

from settings import C


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
