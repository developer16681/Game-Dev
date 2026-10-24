"""All on-screen UI: HUD, start menu, game-over panel, crash flash."""
from ursina import *

NEON = color.hsv(185, 0.85, 1)
PINK = color.hsv(320, 0.85, 1)
RED = color.hsv(355, 0.85, 1)
GOLD = color.hsv(48, 0.85, 1)
DIM = color.hsv(260, 0.6, 0.10, 0.72)


class UI:
    def __init__(self, on_start, on_restart):
        # full-screen flash used on crash (behind all other UI)
        self.flash_overlay = Entity(parent=camera.ui, model="quad", scale=(4, 3),
                                    color=color.hsv(0, 0, 0, 0), z=2)

        # ---------------- HUD
        self.hud = Entity(parent=camera.ui)
        self.score_text = Text("0 m", parent=self.hud, position=(-0.86, 0.47),
                               origin=(-0.5, 0.5), scale=2.2, color=color.white)
        self.best_text = Text("BEST 0", parent=self.hud, position=(0.86, 0.47),
                              origin=(0.5, 0.5), scale=1.4, color=GOLD)
        self.speed_text = Text("", parent=self.hud, position=(-0.86, 0.39),
                               origin=(-0.5, 0.5), scale=1.1, color=NEON)
        self.mute_text = Text("", parent=self.hud, position=(0.86, 0.41),
                              origin=(0.5, 0.5), scale=1.1, color=RED)
        Text("A/D or ←/→ move   SPACE jump   S or ↓ slide   R restart   M mute",
             parent=self.hud, position=(0, -0.47), origin=(0, 0), scale=0.9,
             color=color.hsv(0, 0, 1, 0.6))

        # ---------------- start menu
        self.menu = Entity(parent=camera.ui)
        Entity(parent=self.menu, model="quad", scale=(4, 3), color=DIM, z=1)
        Text("NEON RUNNER", parent=self.menu, y=0.27, origin=(0, 0), scale=4, color=NEON)
        Text("Jump the hurdles  •  Slide under the bars  •  Dodge the walls",
             parent=self.menu, y=0.15, origin=(0, 0), scale=1.2, color=color.white)
        self.menu_best = Text("BEST 0 m", parent=self.menu, y=0.06, origin=(0, 0),
                              scale=1.6, color=GOLD)
        Button(text="START", parent=self.menu, scale=(0.26, 0.08), y=-0.07,
               color=color.hsv(185, 0.8, 0.55), highlight_color=color.hsv(185, 0.8, 0.9),
               on_click=on_start)
        Text("press SPACE or ENTER", parent=self.menu, y=-0.16, origin=(0, 0),
             scale=1.0, color=color.hsv(0, 0, 1, 0.6))
        Text("A/D or ←/→ lanes   SPACE jump   S or ↓ slide   M mute   TAB menu",
             parent=self.menu, y=-0.30, origin=(0, 0), scale=1.0, color=color.white)

        # ---------------- game over
        self.over = Entity(parent=camera.ui)
        Entity(parent=self.over, model="quad", scale=(4, 3), color=DIM, z=1)
        Text("GAME OVER", parent=self.over, y=0.25, origin=(0, 0), scale=4, color=RED)
        self.over_score = Text("0 m", parent=self.over, y=0.12, origin=(0, 0), scale=2.4,
                               color=color.white)
        self.over_best = Text("BEST 0 m", parent=self.over, y=0.04, origin=(0, 0), scale=1.6,
                              color=GOLD)
        self.over_new = Text("NEW HIGH SCORE!", parent=self.over, y=-0.03, origin=(0, 0),
                             scale=1.6, color=PINK)
        Button(text="RESTART", parent=self.over, scale=(0.26, 0.08), y=-0.14,
               color=color.hsv(320, 0.7, 0.55), highlight_color=color.hsv(320, 0.7, 0.9),
               on_click=on_restart)
        Text("press R or ENTER", parent=self.over, y=-0.23, origin=(0, 0), scale=1.0,
             color=color.hsv(0, 0, 1, 0.6))

        self._last_score = -1
        self._last_speed = -1
        self.show_menu(0)

    # ------------------------------------------------------------ screens
    def _only(self, hud=False, menu=False, over=False):
        self.hud.enabled = hud
        self.menu.enabled = menu
        self.over.enabled = over

    def show_menu(self, best):
        self.menu_best.text = f"BEST {best} m"
        self._only(menu=True)

    def show_hud(self, best):
        self.best_text.text = f"BEST {best} m"
        self._last_score = self._last_speed = -1
        self._only(hud=True)

    def show_game_over(self, score, best, new_best):
        self.over_score.text = f"{score} m"
        self.over_best.text = f"BEST {best} m"
        self.over_new.enabled = new_best
        self._only(over=True)

    # ------------------------------------------------------------ live updates
    def update_hud(self, score, speed):
        if score != self._last_score:
            self._last_score = score
            self.score_text.text = f"{score} m"
        kmh = int(speed * 3.6)
        if kmh != self._last_speed:
            self._last_speed = kmh
            self.speed_text.text = f"{kmh} km/h"

    def set_muted(self, muted):
        self.mute_text.text = "MUTED" if muted else ""

    def flash(self):
        self.flash_overlay.color = color.hsv(0, 0.9, 1, 0.45)
        self.flash_overlay.animate_color(color.hsv(0, 0.9, 1, 0), duration=0.5)
