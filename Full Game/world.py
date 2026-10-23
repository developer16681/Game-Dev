"""
Procedural, pooled world.

The player stays at Z=0; the *world* scrolls toward the camera (-Z).  That keeps floating-point
precision perfect no matter how far you run.

  * Track chunks are pooled: once a chunk is fully behind the player it jumps to the far end
    of the track and is repopulated with obstacles.
  * Obstacles are pooled per kind: released on recycle, re-used when a chunk is populated.
"""
import random

from ursina import *

import config as C

KINDS = ("low", "high", "full")     # low = jump, high = slide, full = change lane
HUE_START = 200


def _col(h, s, v, a=1.0):
    return color.hsv(h % 360, s, v, a)


class Obstacle(Entity):
    """One obstacle (a lane wide).  Hitbox children carry the BoxColliders."""

    def __init__(self, kind):
        super().__init__()
        self.kind = kind
        self.hitboxes = []
        if kind == "low":                                   # hurdle -> JUMP over it
            self._block((2.4, 1.0, 1.0), (0, 0.5, 0), _col(25, 0.9, 1))
            self._block((2.4, 0.14, 1.04), (0, 1.0, 0), _col(55, 0.9, 1), solid=False)
        elif kind == "high":                                # overhead bar -> SLIDE under it
            self._block((2.6, 1.0, 1.0), (0, 1.8, 0), _col(320, 0.85, 1))
            for sx in (-1.3, 1.3):
                self._block((0.25, 2.3, 0.25), (sx, 1.15, 0), _col(0, 0, 0.55), solid=False)
        else:                                               # full blocker -> DODGE to another lane
            self._block((2.6, 3.0, 1.4), (0, 1.5, 0), _col(0, 0.85, 0.95))
            self._block((2.6, 0.2, 1.44), (0, 3.0, 0), _col(0, 0.5, 1), solid=False)
        self.enabled = False                                # created inactive (pooled)

    def _block(self, scale, pos, col, solid=True):
        e = Entity(parent=self, model="cube", texture="white_cube", color=col,
                   scale=Vec3(*scale), position=Vec3(*pos))
        if solid:
            # 0.92 => slightly forgiving hitbox
            e.collider = BoxCollider(e, center=Vec3(0, 0, 0), size=Vec3(0.92, 0.92, 0.92))
            if C.DEBUG_COLLIDERS:
                try:
                    e.collider.visible = True
                except Exception:
                    pass
            self.hitboxes.append(e)
        return e


class Chunk(Entity):
    """A section of track: floor, lane lines, rails and neon skyline pillars."""

    def __init__(self, parent):
        super().__init__(parent=parent)
        L = C.CHUNK_LENGTH
        self.obstacles = []
        self.floor = Entity(parent=self, model="plane", texture="white_cube",
                            texture_scale=(C.TRACK_WIDTH / 3, L / 3), scale=(C.TRACK_WIDTH, 1, L))
        self.ground = Entity(parent=self, model="plane", scale=(90, 1, L), y=-0.3)
        self.lines = [Entity(parent=self, model="cube", scale=(0.12, 0.12, L), x=x, y=0.06)
                      for x in (-1.5, 1.5)]
        self.rails = [Entity(parent=self, model="cube", scale=(0.35, 0.7, L), x=x, y=0.35)
                      for x in (-C.TRACK_WIDTH / 2, C.TRACK_WIDTH / 2)]
        self.pillars = [Entity(parent=self, model="cube", texture="white_cube") for _ in range(6)]
        self.restyle(HUE_START)

    def restyle(self, hue):
        L = C.CHUNK_LENGTH
        self.floor.color = _col(hue, 0.45, 0.55)
        self.ground.color = _col(hue + 60, 0.7, 0.10)
        for r in self.rails:
            r.color = _col(hue + 140, 0.85, 1)
        for ln in self.lines:
            ln.color = _col(hue, 0.3, 1)
        for i, p in enumerate(self.pillars):
            side = -1 if i % 2 == 0 else 1
            h = random.uniform(6, 24)
            p.scale = Vec3(random.uniform(1.6, 3.2), h, random.uniform(1.6, 3.2))
            p.position = Vec3(side * random.uniform(9, 28), h / 2, random.uniform(-L / 2, L / 2))
            p.texture_scale = (1, h / 4)
            p.color = _col(hue + random.uniform(-40, 40), 0.6, random.uniform(0.3, 0.6))


class World:
    def __init__(self):
        self.root = Entity()
        self.chunks = [Chunk(self.root) for _ in range(C.NUM_CHUNKS)]
        self.pools = {k: [Obstacle(k) for _ in range(8)] for k in KINDS}
        self.difficulty = 0.0
        self.carry = 0.0                 # distance (in the next chunk) until the next obstacle row
        self.reset(spawn=False)

    # ------------------------------------------------------------ lifecycle
    def reset(self, spawn=True):
        L = C.CHUNK_LENGTH
        for i, ch in enumerate(self.chunks):
            self._release_all(ch)
            ch.z = i * L
            ch.restyle(HUE_START)
        self.difficulty = 0.0
        self.carry = C.FIRST_OBSTACLE_Z + L / 2          # chunk 0 spans -L/2 .. L/2
        if spawn:
            for ch in self.chunks:
                self._populate(ch)

    def update(self, dt, speed, difficulty, spawn=True):
        self.difficulty = difficulty
        dz = speed * dt
        for ch in self.chunks:
            ch.z -= dz
        for ch in self.chunks:                           # recycle chunks that are behind us
            if ch.z < C.RECYCLE_Z:
                ch.z = max(c.z for c in self.chunks) + C.CHUNK_LENGTH
                self._release_all(ch)
                ch.restyle(HUE_START + difficulty * 120)
                if spawn:
                    self._populate(ch)

    # ------------------------------------------------------------ obstacle pooling
    def _release_all(self, chunk):
        for ob in chunk.obstacles:
            ob.enabled = False
            self.pools[ob.kind].append(ob)
        chunk.obstacles.clear()

    def _place(self, chunk, kind, x, z):
        pool = self.pools[kind]
        ob = pool.pop() if pool else Obstacle(kind)
        ob.parent = chunk
        ob.position = Vec3(x, 0, z)
        ob.enabled = True
        chunk.obstacles.append(ob)

    # ------------------------------------------------------------ procedural generation
    def _populate(self, chunk):
        L, d = C.CHUNK_LENGTH, self.difficulty
        lo = lerp(C.GAP_EASY[0], C.GAP_HARD[0], d)
        hi = lerp(C.GAP_EASY[1], C.GAP_HARD[1], d)
        cursor = self.carry
        while cursor < L:
            self._spawn_row(chunk, cursor - L / 2)
            cursor += random.uniform(lo, hi)
        self.carry = cursor - L

    def _spawn_row(self, chunk, z):
        d = self.difficulty
        lanes = [0, 1, 2]
        if random.random() < 0.15 + 0.25 * d:
            # mixed row: every lane gets its own obstacle (or nothing)
            assign = [random.choice(("low", "high", "full", None)) for _ in lanes]
            if assign.count("full") == 3:                # never wall the whole track
                assign[random.randrange(3)] = random.choice(("low", "high"))
        else:
            kind = random.choices(KINDS, weights=(3, 3, 2 + 3 * d))[0]
            if kind == "full":
                n = 1 if random.random() > 0.25 + 0.5 * d else 2    # always leave a free lane
            else:
                n = random.choices((1, 2, 3), weights=(5, 3, 2 + 2 * d))[0]
            chosen = random.sample(lanes, n)
            assign = [kind if i in chosen else None for i in lanes]
        for i, k in enumerate(assign):
            if k:
                self._place(chunk, k, C.LANES[i], z)

    # ------------------------------------------------------------ helpers
    def hitboxes(self):
        for ch in self.chunks:
            for ob in ch.obstacles:
                for hb in ob.hitboxes:
                    yield hb
