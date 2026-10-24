"""Lightweight visual effects built from pooled Ursina entities (no per-frame allocation)."""
import random

from ursina import *


class Particles:
    """Pooled cube particles: dust puffs when jumping/landing/sliding and a crash burst."""

    def __init__(self, size=90):
        self.pool, self.active = [], []
        for _ in range(size):
            e = Entity(model="cube", scale=0.2)
            e.enabled = False
            self.pool.append(e)

    def emit(self, pos, count, col, size=0.22, life=0.5, spread=1.2, up=2.0, back=0.0):
        for _ in range(count):
            if self.pool:
                p = self.pool.pop()
            elif self.active:               # pool exhausted: steal the oldest particle
                p = self.active.pop(0)
            else:
                return
            p.enabled = True
            p.position = Vec3(pos[0] + random.uniform(-0.35, 0.35),
                              pos[1] + random.uniform(0.0, 0.1),
                              pos[2] + random.uniform(-0.2, 0.2))
            p.color = col
            p.base_size = size * random.uniform(0.6, 1.2)
            p.scale = p.base_size
            p.vel = Vec3(random.uniform(-spread, spread),
                         random.uniform(0.3, 1.0) * up,
                         random.uniform(-spread, spread) * 0.6 - back)
            p.max_life = life * random.uniform(0.7, 1.2)
            p.life = p.max_life
            self.active.append(p)

    def dust(self, pos, count=8, size=0.2):
        self.emit(pos, count, color.hsv(220, 0.12, 0.9), size=size, life=0.45, spread=1.4, up=1.6)

    def burst(self, pos, count=40):
        for hue in (10, 30, 50):
            self.emit(pos, count // 3, color.hsv(hue, 0.9, 1), size=0.32, life=0.8, spread=5, up=6)

    def update(self, dt, world_speed):
        for p in self.active[:]:
            p.life -= dt
            if p.life <= 0:
                p.enabled = False
                self.active.remove(p)
                self.pool.append(p)
                continue
            p.vel.y -= 9.0 * dt
            p.x += p.vel.x * dt
            p.y = max(0.0, p.y + p.vel.y * dt)
            p.z += (p.vel.z - world_speed) * dt        # world scrolls toward the player
            p.scale = p.base_size * (p.life / p.max_life)

    def clear(self):
        for p in self.active:
            p.enabled = False
            self.pool.append(p)
        self.active.clear()


class SpeedLines:
    """A handful of streaks rushing past the camera to sell the sense of speed."""

    def __init__(self, count=16):
        self.lines = []
        for _ in range(count):
            e = Entity(model="cube", scale=(0.05, 0.05, 4), color=color.hsv(190, 0.35, 1, 0.55))
            self._respawn(e, far=random.uniform(0, 140))
            self.lines.append(e)

    @staticmethod
    def _respawn(e, far=None):
        side = random.choice((-1, 1))
        e.x = side * random.uniform(4.5, 12)
        e.y = random.uniform(0.4, 7)
        e.z = far if far is not None else random.uniform(90, 150)

    def update(self, dt, speed, active):
        for e in self.lines:
            e.enabled = active
            if not active:
                continue
            e.z -= speed * 1.6 * dt
            e.scale_z = 2 + speed * 0.1
            if e.z < -15:
                self._respawn(e)
