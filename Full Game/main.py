"""
NEON RUNNER - a 3D endless runner built with the Ursina Engine.

Run:      pip install ursina
          python main.py

Controls: A / D or Left / Right   change lane
          SPACE (or W / Up)       jump
          S or Down               slide (press in mid-air to slam down + slide)
          R                       instant restart
          M                       mute      - / =   music volume
          TAB                     back to menu
"""
import random

from ursina import *

import config as C
from audio_manager import AudioManager
from effects import Particles, SpeedLines
from player import Player
from storage import load_high_score, save_high_score
from ui import UI
from world import World

MENU, PLAYING, GAME_OVER = "menu", "playing", "game_over"


class Game(Entity):
    """Owns the game state machine; Ursina calls update()/input() on it automatically."""

    def __init__(self):
        super().__init__()
        self.high_score = load_high_score()
        self.audio = AudioManager()
        self.fx = Particles()
        self.speed_lines = SpeedLines()
        self.world = World()
        self.player = Player(self.audio, self.fx)
        self.ui = UI(on_start=self.start_game, on_restart=self.start_game)

        self.run_distance = 0.0
        self.speed = C.MENU_SPEED
        self.shake = 0.0
        self._run_id = 0
        self._manual_collision = False       # switches on if Ursina's intersects() ever fails
        self._setup_camera()
        self.to_menu()

    # ------------------------------------------------------------ setup
    def _setup_camera(self):
        camera.position = Vec3(*C.CAM_POS)       # behind and above the runner
        camera.rotation_x = C.CAM_PITCH          # look down at the track
        camera.fov = C.CAM_FOV
        try:
            camera.clip_plane_near = 0.5         # better depth precision on the far track
            camera.clip_plane_far = 400
        except Exception:
            pass

    # ------------------------------------------------------------ state transitions
    def to_menu(self):
        self.state = MENU
        self._run_id += 1
        self.speed = C.MENU_SPEED
        self.world.reset(spawn=False)            # empty track behind the menu
        self.player.reset()
        self.fx.clear()
        self.audio.stop_music()
        self.ui.show_menu(self.high_score)

    def start_game(self):
        """Also used as the instant-restart: resets score, speed, world, player and music."""
        if self.state == MENU:
            self.audio.play("start")
        self._run_id += 1
        self.run_distance = 0.0
        self.speed = C.BASE_SPEED
        self.shake = 0.0
        self.world.reset(spawn=True)
        self.player.reset()
        self.fx.clear()
        self.audio.play_music(restart=True)      # restarts the BGM loop from the top
        self.state = PLAYING
        self.ui.show_hud(self.high_score)

    def _crash(self):
        self.state = GAME_OVER
        self.player.die()
        self.audio.stop_music()
        self.audio.play("crash")
        invoke(self._game_over_jingle, self._run_id, delay=0.6)
        self.fx.burst(Vec3(self.player.x, 1.0, 0), 45)
        self.shake = 0.7
        self.ui.flash()

        final = int(self.run_distance)
        new_best = final > self.high_score
        if new_best:
            self.high_score = final
            save_high_score(final)
        self.ui.show_game_over(final, self.high_score, new_best)

    def _game_over_jingle(self, run_id):
        if self.state == GAME_OVER and run_id == self._run_id:    # ignore if already restarted
            self.audio.play("game_over")

    # ------------------------------------------------------------ collision
    def _collides(self):
        """Ursina BoxCollider test; falls back to a manual AABB test if intersects() errors."""
        if not self._manual_collision:
            try:
                return bool(self.player.intersects(traverse_target=self.world.root).hit)
            except Exception as exc:
                print(f"[collision] intersects() failed ({exc}); using manual AABB test")
                self._manual_collision = True
        p = self.player
        px0, px1 = p.x - 0.35, p.x + 0.35
        py0, py1 = p.y, p.y + 1.9 * p.scale_y
        for hb in self.world.hitboxes():
            wp, ws = hb.world_position, hb.world_scale
            hx, hy, hz = ws.x * 0.46, ws.y * 0.46, ws.z * 0.46
            if (abs(wp.x - (px0 + px1) / 2) < hx + 0.35 and
                    wp.y - hy < py1 and wp.y + hy > py0 and
                    abs(wp.z) < hz + 0.35):
                return True
        return False

    # ------------------------------------------------------------ main loop
    def update(self):
        dt = min(time.dt, 0.05)                  # clamp lag spikes
        world_speed = 0.0

        if self.state == PLAYING:
            self.speed = min(C.MAX_SPEED, C.BASE_SPEED + C.SPEED_PER_METER * self.run_distance)
            self.run_distance += self.speed * dt
            difficulty = min(1.0, self.run_distance / C.DIFFICULTY_METERS)
            self.world.update(dt, self.speed, difficulty, spawn=True)
            self.player.tick(dt, self.speed)
            world_speed = self.speed
            if self._collides():
                self._crash()
            else:
                self.ui.update_hud(int(self.run_distance), self.speed)
        elif self.state == MENU:
            self.world.update(dt, C.MENU_SPEED, 0.0, spawn=False)
            self.player.tick(dt, C.MENU_SPEED)
            world_speed = C.MENU_SPEED
        else:                                    # GAME_OVER: world frozen, player topples
            self.player.tick(dt, 0)

        self.fx.update(dt, world_speed)
        self.speed_lines.update(dt, world_speed, self.state == PLAYING)
        self._update_camera(dt)

    def _update_camera(self, dt):
        p = self.player
        camera.x = lerp(camera.x, p.x * C.CAM_FOLLOW_X, min(1.0, dt * 6))
        target_y = C.CAM_POS[1] + p.y * 0.4 - (0.6 if p.sliding else 0.0)
        camera.y = lerp(camera.y, target_y, min(1.0, dt * 5))
        t = (self.speed - C.BASE_SPEED) / (C.MAX_SPEED - C.BASE_SPEED)
        camera.fov = lerp(camera.fov, C.CAM_FOV + clamp(t, 0, 1) * 12, min(1.0, dt * 2))
        if self.shake > 0:                       # crash shake
            camera.x += random.uniform(-1, 1) * self.shake * 0.4
            camera.y += random.uniform(-1, 1) * self.shake * 0.4
            self.shake = max(0.0, self.shake - dt * 1.5)

    # ------------------------------------------------------------ input
    def input(self, key):
        if key == "m":
            self.ui.set_muted(self.audio.toggle_mute())
        elif key == "-":
            self.audio.set_music_volume(self.audio.music_volume - 0.1)
        elif key in ("=", "+"):
            self.audio.set_music_volume(self.audio.music_volume + 0.1)

        if self.state == MENU:
            if key in ("space", "enter"):
                self.start_game()
        elif self.state == GAME_OVER:
            if key in ("r", "enter"):
                self.start_game()
            elif key == "tab":
                self.to_menu()
        elif self.state == PLAYING:
            if key == "r":
                self.start_game()                # instant restart
            elif key == "tab":
                self.to_menu()
            elif key in ("a", "left arrow"):
                self.player.move_lane(-1)
            elif key in ("d", "right arrow"):
                self.player.move_lane(1)
            elif key in ("space", "w", "up arrow"):
                self.player.jump()
            elif key in ("s", "down arrow"):
                self.player.slide()


def main():
    try:
        app = Ursina(title="Neon Runner", borderless=False, development_mode=False)
    except TypeError:                            # older Ursina versions
        app = Ursina(title="Neon Runner", borderless=False)
    window.color = color.hsv(255, 0.7, 0.12)
    try:
        window.exit_button.visible = False
        window.fps_counter.enabled = C.SHOW_FPS
    except Exception:
        pass
    Game()
    app.run()


if __name__ == "__main__":
    main()
