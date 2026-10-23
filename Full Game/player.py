"""The runner: lane switching, jump (with gravity + landing), slide (squashes entity AND hitbox)."""
import math

from ursina import *

import config as C

TORSO = color.hsv(190, 0.9, 0.95)
LIMB = color.hsv(190, 0.9, 0.70)
SKIN = color.hsv(30, 0.35, 1)
GLOW = color.hsv(320, 0.9, 1)


class Player(Entity):
    def __init__(self, audio, fx):
        super().__init__()
        self.audio = audio
        self.fx = fx

        # --- visuals live under model_root so lean/tumble does not rotate the collider
        mr = self.model_root = Entity(parent=self)
        Entity(parent=mr, model="cube", color=TORSO, scale=(0.8, 0.95, 0.45), y=1.1)        # torso
        Entity(parent=mr, model="cube", color=GLOW, scale=(0.5, 0.6, 0.2), y=1.15, z=-0.3)   # pack
        Entity(parent=mr, model="sphere", color=SKIN, scale=0.55, y=1.82)                    # head
        Entity(parent=mr, model="cube", color=GLOW, scale=(0.4, 0.14, 0.1), y=1.86, z=0.24)  # visor
        self.legs, self.arms = [], []
        for sx in (-0.2, 0.2):
            piv = Entity(parent=mr, x=sx, y=0.72)                  # pivot at the hip
            Entity(parent=piv, model="cube", color=LIMB, scale=(0.3, 0.72, 0.32), y=-0.36)
            self.legs.append(piv)
        for sx in (-0.55, 0.55):
            piv = Entity(parent=mr, x=sx, y=1.5)                   # pivot at the shoulder
            Entity(parent=piv, model="cube", color=LIMB, scale=(0.22, 0.75, 0.22), y=-0.34)
            self.arms.append(piv)

        # --- hitbox: lives on the root so it squashes together with scale_y while sliding
        self.collider = BoxCollider(self, center=Vec3(0, 0.95, 0), size=Vec3(0.7, 1.9, 0.7))
        if C.DEBUG_COLLIDERS:
            try:
                self.collider.visible = True
            except Exception:
                pass
        self.reset()

    # ------------------------------------------------------------ state
    def reset(self):
        self.lane = 1
        self.position = Vec3(C.LANES[1], 0, 0)
        self.scale = Vec3(1, 1, 1)
        self.vy = 0.0
        self.grounded = True
        self.sliding = False
        self.slide_timer = 0.0
        self.queued_slide = False
        self.alive = True
        self.tumble = 0.0
        self.run_phase = 0.0
        self.dust_timer = 0.0
        self.model_root.rotation = Vec3(0, 0, 0)
        for piv in self.legs + self.arms:
            piv.rotation_x = 0

    def die(self):
        self.alive = False
        self.sliding = False

    def _feet(self):
        return Vec3(self.x, self.y + 0.05, 0)

    # ------------------------------------------------------------ actions
    def move_lane(self, direction):
        new = clamp(self.lane + direction, 0, len(C.LANES) - 1)
        if new == self.lane:
            return
        self.lane = new
        self.audio.play("lane_switch")
        self.fx.dust(self._feet(), 5, 0.16)

    def jump(self):
        if not self.grounded:
            return
        self.vy = C.JUMP_VELOCITY
        self.grounded = False
        self.sliding = False
        self.slide_timer = 0
        self.audio.play("jump")
        self.fx.dust(self._feet(), 10)

    def slide(self):
        if not self.grounded:                      # in the air: slam down, then slide on landing
            self.vy = min(self.vy, C.FAST_FALL_VELOCITY)
            self.queued_slide = True
            return
        if not self.sliding:
            self._begin_slide()

    def _begin_slide(self):
        self.sliding = True
        self.slide_timer = C.SLIDE_DURATION
        self.queued_slide = False
        self.audio.play("slide")
        self.fx.dust(self._feet(), 8)

    # ------------------------------------------------------------ per-frame
    def tick(self, dt, speed):
        mr = self.model_root
        if not self.alive:                         # crash animation: topple backwards
            self.tumble = min(1.0, self.tumble + dt * 4)
            mr.rotation_x = -85 * self.tumble
            return

        # lane interpolation + lean
        tx = C.LANES[self.lane]
        self.x = lerp(self.x, tx, min(1.0, C.LANE_LERP * dt))
        mr.rotation_z = clamp((self.x - tx) * 7, -22, 22)

        # jump physics / landing detection
        if not self.grounded:
            self.vy -= C.GRAVITY * dt
            self.y += self.vy * dt
            if self.y <= 0:
                self.y, self.vy, self.grounded = 0.0, 0.0, True
                self.audio.play("land")
                self.fx.dust(self._feet(), 12, 0.25)
                if self.queued_slide:
                    self._begin_slide()

        # slide timer + squash (scale_y shrinks visual AND collider)
        if self.sliding:
            self.slide_timer -= dt
            if self.slide_timer <= 0:
                self.sliding = False
        target = C.SLIDE_SCALE_Y if self.sliding else 1.0
        self.scale_y = lerp(self.scale_y, target, min(1.0, 25 * dt))

        # running dust trail
        if self.grounded:
            self.dust_timer -= dt
            if self.dust_timer <= 0:
                self.dust_timer = 0.04 if self.sliding else 0.08
                self.fx.dust(self._feet(), 2 if self.sliding else 1, 0.14)

        self._animate(dt, speed)

    def _animate(self, dt, speed):
        self.run_phase += dt * (6 + speed * 0.35)
        s = math.sin(self.run_phase)
        if self.sliding:
            legs, arms = (-80, -80), (-50, -50)
        elif not self.grounded:
            legs, arms = (-40, 25), (-140, -140)
        else:
            legs, arms = (s * 55, -s * 55), (-s * 50, s * 50)
        for piv, a in zip(self.legs, legs):
            piv.rotation_x = a
        for piv, a in zip(self.arms, arms):
            piv.rotation_x = a
