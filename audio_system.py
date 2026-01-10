# audio_system.py
import os
import math
import random
from array import array
from typing import Optional

import pygame

from settings import C, clamp, resource_path


class AudioSystem:
    def __init__(self) -> None:
        self.enabled = True

        self.drone: Optional[pygame.mixer.Sound] = None
        self.drone_channel: Optional[pygame.mixer.Channel] = None
        self.drone_dynamic = 0.10

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

        if self.enabled:
            try:
                pygame.mixer.music.set_volume(self.music_volume)
            except Exception:
                pass

        self.set_game_drone_dynamic(self.drone_dynamic)

        if self.ambient_channel is not None:
            self.ambient_channel.set_volume(0.25 * self.sfx_volume)

        if self.scream_channel is not None:
            self.scream_channel.set_volume(self.sfx_volume)

        for snd in (self.ui_hover_sound, self.ui_click_sound, self.pickup_sound, self.victory_sound, self.end_sound):
            if snd is not None:
                try:
                    snd.set_volume(self.sfx_volume)
                except Exception:
                    pass

    def _play_sfx(self, snd: Optional[pygame.mixer.Sound]) -> None:
        if not self.enabled or snd is None:
            return
        try:
            snd.set_volume(self.sfx_volume)
            snd.play()
        except Exception:
            return

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

    # ---------- Menu music ----------
    def play_menu_music(self) -> None:
        if not self.enabled:
            return
        if not os.path.exists(self.menu_path):
            return
        if self.music_playing:
            return
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(self.menu_path)
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(-1)
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

    # ---------- Drone / ambient ----------
    def start_drone(self) -> None:
        if not self.enabled:
            return
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
        if self.use_music_for_scream:
            self.stop_menu_music()

        if (not self.use_music_for_scream) and self.scream_sound is not None and self.scream_channel is not None:
            self.scream_channel.set_volume(self.sfx_volume)
            self.scream_channel.stop()
            self.scream_channel.play(self.scream_sound)
            return

        try:
            if os.path.exists(self.scream_path):
                pygame.mixer.music.stop()
                pygame.mixer.music.load(self.scream_path)
                pygame.mixer.music.set_volume(self.sfx_volume)
                pygame.mixer.music.play(0)
        except Exception:
            pass

    def stop_scream(self) -> None:
        if not self.enabled:
            return
        if self.scream_channel is not None:
            self.scream_channel.stop()
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

        try:
            if os.path.exists(self.scream_path):
                self.scream_sound = pygame.mixer.Sound(self.scream_path)
                self.use_music_for_scream = False
                return
        except Exception:
            pass

        try:
            if os.path.exists(self.scream_path):
                pygame.mixer.music.load(self.scream_path)
                self.use_music_for_scream = True
        except Exception:
            self.use_music_for_scream = True
