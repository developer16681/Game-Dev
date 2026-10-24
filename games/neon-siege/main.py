"""
NEON SIEGE - a wave-survival first-person shooter made with Ursina.

Install:   pip install ursina
Run:       python neon_siege.py

Controls
    WASD ........ move
    SHIFT ....... sprint
    SPACE ....... jump
    MOUSE ....... look
    LEFT CLICK .. shoot (hold for auto-fire)
    R ........... reload
    ESC ......... quit

No external assets needed: everything is built from primitives, lighting,
shadows, fog, particles and a few neon accents.
"""
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from ursina.shaders import lit_with_shadows_shader, unlit_shader
from types import SimpleNamespace
import math
import random


def C(r, g, b, a=1.0):
    """Color from 0-1 floats (avoids differences between Ursina versions)."""
    return Color(r, g, b, a)


# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
ARENA = 45            # half-size of the arena
MAX_HP = 100
MAG = 30              # magazine size
FIRE_DELAY = 0.11     # seconds between shots
RELOAD_TIME = 1.2

CYAN = C(0.2, 0.95, 1.0)
MAGENTA = C(1.0, 0.2, 0.8)

KINDS = {
    'grunt':  dict(color=C(1.0, 0.20, 0.25), size=1.1, hp=2,  speed=4.5, dmg=10, pts=100),
    'runner': dict(color=C(1.0, 0.60, 0.10), size=0.8, hp=1,  speed=8.0, dmg=6,  pts=150),
    'tank':   dict(color=C(0.70, 0.25, 1.0), size=2.2, hp=10, speed=2.6, dmg=25, pts=400),
}

# ----------------------------------------------------------------------------
# App + rendering setup
# ----------------------------------------------------------------------------
app = Ursina(title='NEON SIEGE', borderless=False, vsync=True)

window.color = C(0.02, 0.02, 0.06)
window.exit_button.visible = False
window.fps_counter.enabled = True
camera.clip_plane_far = 2000

Entity.default_shader = lit_with_shadows_shader   # real-time shadows on everything

sun = DirectionalLight(shadow_map_resolution=(2048, 2048), color=C(0.95, 0.85, 1.0))
sun.look_at(Vec3(1, -1.2, -0.6))
AmbientLight(color=C(0.30, 0.32, 0.45))

scene.fog_color = window.color
scene.fog_density = (30, 110)

# Optional post-processing (skipped quietly if this Ursina version lacks it)
try:
    from ursina.shaders import camera_vignette_shader
    camera.shader = camera_vignette_shader
except Exception:
    pass

# ----------------------------------------------------------------------------
# World
# ----------------------------------------------------------------------------
ground = Entity(model='plane', scale=ARENA * 2, texture='white_cube',
                texture_scale=(ARENA, ARENA), color=C(0.10, 0.12, 0.22), collider='box')

for (x, z, sx, sz) in [(0, ARENA, ARENA * 2 + 2, 2), (0, -ARENA, ARENA * 2 + 2, 2),
                       (ARENA, 0, 2, ARENA * 2 + 2), (-ARENA, 0, 2, ARENA * 2 + 2)]:
    Entity(model='cube', position=(x, 6, z), scale=(sx, 12, sz),
           color=C(0.07, 0.08, 0.15), collider='box')
    for y, col in ((0.3, CYAN), (12, MAGENTA)):
        Entity(model='cube', position=(x, y, z), scale=(sx + 0.2, 0.25, sz + 0.2),
               color=col, shader=unlit_shader)

# Neon pillars around the rim
for i in range(12):
    ang = i / 12 * math.tau
    px, pz = math.cos(ang) * (ARENA - 4), math.sin(ang) * (ARENA - 4)
    Entity(model='cube', position=(px, 8, pz), scale=(1.5, 16, 1.5), color=C(0.06, 0.07, 0.13))
    for y, col in ((3, CYAN if i % 2 else MAGENTA), (9, MAGENTA if i % 2 else CYAN)):
        Entity(model='cube', position=(px, y, pz), scale=(1.6, 0.3, 1.6),
               color=col, shader=unlit_shader)

# Stars
star_verts = []
for _ in range(900):
    v = Vec3(random.gauss(0, 1), abs(random.gauss(0, 1)) + 0.05, random.gauss(0, 1))
    star_verts.append(v.normalized() * 800)
Entity(model=Mesh(vertices=star_verts, mode='point', thickness=3),
       color=color.white, shader=unlit_shader)

# Glowing floor rings (pure eye candy, safe to fail)
try:
    from ursina.models.procedural.circle import Circle
    for r in (8, 18, 30):
        Entity(model=Circle(64, mode='line', thickness=3), rotation_x=90, y=0.06,
               scale=r * 2, color=CYAN if r != 18 else MAGENTA, shader=unlit_shader)
except Exception:
    pass

# ----------------------------------------------------------------------------
# Player + weapon
# ----------------------------------------------------------------------------
player = FirstPersonController(position=(0, 2, 0), speed=9, jump_height=1.8)
camera.fov = 95
if hasattr(player, 'cursor'):
    player.cursor.color = CYAN

gun_root = Entity(parent=camera, position=(0.35, -0.3, 0.6))
Entity(parent=gun_root, model='cube', scale=(0.12, 0.14, 0.7),
       color=C(0.18, 0.19, 0.25), shader=unlit_shader)
Entity(parent=gun_root, model='cube', scale=(0.125, 0.03, 0.5), y=0.06, z=0.05,
       color=CYAN, shader=unlit_shader)
flash = Entity(parent=gun_root, model='sphere', scale=0.2, z=0.55,
               color=C(1, 0.9, 0.3), shader=unlit_shader, enabled=False)

# Crosshair ticks
for (px, py, sx, sy) in ((0.018, 0, 0.012, 0.0025), (-0.018, 0, 0.012, 0.0025),
                         (0, 0.018, 0.0025, 0.012), (0, -0.018, 0.0025, 0.012)):
    Entity(parent=camera.ui, model='quad', position=(px, py), scale=(sx, sy), color=CYAN)

# ----------------------------------------------------------------------------
# Game state
# ----------------------------------------------------------------------------
G = SimpleNamespace(
    health=MAX_HP, ammo=MAG, reloading=False, cooldown=0.0,
    score=0, kills=0, best=0, wave=0, to_spawn=0, spawn_cd=0.0,
    intermission=True, timer=2.0, over=False, banner_t=0.0,
)
enemies = []
pickups = []

# ----------------------------------------------------------------------------
# HUD
# ----------------------------------------------------------------------------
score_text = Text(position=window.top_left + Vec2(0.03, -0.03), scale=1.6, color=CYAN)
wave_text = Text(position=window.top_right + Vec2(-0.22, -0.03), scale=1.6, color=MAGENTA)
ammo_text = Text(position=window.bottom_right + Vec2(-0.28, 0.10), scale=2.4, color=color.white)
Text('HP', position=window.bottom_left + Vec2(0.05, 0.10), scale=1.2, color=color.white)

hp_bg = Entity(parent=camera.ui, model='quad', origin=(-0.5, 0), scale=(0.35, 0.03),
               position=window.bottom_left + Vec2(0.09, 0.075), color=C(0, 0, 0, 0.6))
hp_fg = Entity(parent=camera.ui, model='quad', origin=(-0.5, 0), scale=(0.35, 0.03),
               position=window.bottom_left + Vec2(0.09, 0.075), color=C(0.2, 1, 0.4), z=-0.01)

banner = Text('', origin=(0, 0), scale=3.2, y=0.30, color=CYAN, enabled=False)
damage_flash = Entity(parent=camera.ui, model='quad', scale=(4, 2), color=C(1, 0, 0, 0), z=1)

# Game over screen
over_group = Entity(parent=camera.ui, enabled=False)
Entity(parent=over_group, model='quad', scale=(4, 2), color=C(0, 0, 0, 0.65))
over_title = Text('GAME OVER', parent=over_group, origin=(0, 0), scale=4, y=0.2, color=C(1, 0.25, 0.3))
over_stats = Text('', parent=over_group, origin=(0, 0), scale=1.8, y=0.05, color=color.white)
Button(text='PLAY AGAIN', parent=over_group, scale=(0.3, 0.08), y=-0.12,
       color=C(0.1, 0.5, 0.6), on_click=lambda: restart())


def show_banner(msg, dur=2.0):
    banner.text = msg
    banner.enabled = True
    G.banner_t = dur


def toast(msg, col=color.white):
    t = Text(msg, origin=(0, 0), y=0.12, scale=1.6, color=col)
    t.animate_y(0.2, duration=0.8)
    destroy(t, delay=0.8)


def update_hp_bar():
    frac = clamp(G.health / MAX_HP, 0, 1)
    hp_fg.scale_x = 0.35 * frac
    hp_fg.color = lerp(C(1, 0.2, 0.2), C(0.2, 1, 0.4), frac)


# ----------------------------------------------------------------------------
# Effects
# ----------------------------------------------------------------------------
def burst(pos, col, n=12):
    for _ in range(n):
        p = Entity(model='cube', position=pos, scale=random.uniform(0.06, 0.16),
                   color=col, shader=unlit_shader)
        target = pos + Vec3(random.uniform(-1, 1), random.uniform(0.2, 1.4),
                            random.uniform(-1, 1)) * random.uniform(0.8, 2.2)
        p.animate_position(target, duration=0.5, curve=curve.out_expo)
        p.animate_scale(0, duration=0.5)
        destroy(p, delay=0.55)


# ----------------------------------------------------------------------------
# Enemies and pickups
# ----------------------------------------------------------------------------
class Drone(Entity):
    def __init__(self, kind, position):
        s = KINDS[kind]
        super().__init__(model='sphere', color=s['color'], scale=s['size'],
                         position=position, collider='sphere')
        self.kind = kind
        self.size = s['size']
        self.base_color = s['color']
        self.hp = s['hp'] + (G.wave // 5 if kind != 'runner' else 0)
        self.speed = s['speed'] * (1 + 0.03 * G.wave)
        self.dmg = s['dmg']
        self.pts = s['pts']
        self.hover = 1.5 + self.size * 0.3
        self.phase = random.random() * 6.28
        self.attack_cd = 0.4
        self.dead = False
        self.eye = Entity(parent=self, model='sphere', scale=0.38, position=(0, 0.1, 0.42),
                          color=color.white, shader=unlit_shader)
        self.ring = Entity(parent=self, model='cube', scale=(1.6, 0.06, 1.6),
                           color=s['color'], shader=unlit_shader)

    def update(self):
        if G.over or self.dead:
            return
        dt = time.dt
        dx, dz = player.x - self.x, player.z - self.z
        dist = math.hypot(dx, dz) or 0.001
        reach = self.size * 0.5 + 1.3

        self.look_at(Vec3(player.x, self.y, player.z))
        if dist > reach * 0.8:
            self.x += dx / dist * self.speed * dt
            self.z += dz / dist * self.speed * dt

        # soft separation so drones don't stack into one blob
        for o in enemies:
            if o is self:
                continue
            ox, oz = self.x - o.x, self.z - o.z
            d2 = ox * ox + oz * oz
            min_d = (self.size + o.size) * 0.5
            if 0 < d2 < min_d * min_d:
                d = math.sqrt(d2)
                push = (min_d - d) * 0.5
                self.x += ox / d * push
                self.z += oz / d * push

        self.x = clamp(self.x, -ARENA + 2, ARENA - 2)
        self.z = clamp(self.z, -ARENA + 2, ARENA - 2)
        self.y = self.hover + math.sin(time.time() * 2 + self.phase) * 0.25
        self.ring.rotation_y += 220 * dt

        # melee ram
        if dist < reach and abs((player.y + 1.0) - self.y) < 2.6:
            self.attack_cd -= dt
            if self.attack_cd <= 0:
                self.attack_cd = 1.0
                hurt_player(self.dmg)
        else:
            self.attack_cd = min(self.attack_cd + dt, 0.4)

    def hit(self, dmg=1):
        if self.dead:
            return
        self.hp -= dmg
        self.color = color.white
        invoke(self.restore_color, delay=0.06)
        if self.hp <= 0:
            self.die()

    def restore_color(self):
        if not self.dead:
            self.color = self.base_color

    def die(self):
        self.dead = True
        if self in enemies:
            enemies.remove(self)
        G.score += self.pts
        G.kills += 1
        burst(self.world_position, self.base_color, 24)
        if random.random() < 0.20:
            Pickup(random.choice(['health', 'ammo']), Vec3(self.x, 1.0, self.z))
        destroy(self)


class Pickup(Entity):
    def __init__(self, kind, position):
        col = C(0.2, 1.0, 0.4) if kind == 'health' else C(1.0, 0.85, 0.2)
        super().__init__(model='sphere' if kind == 'health' else 'cube', color=col,
                         scale=0.55, position=position, shader=unlit_shader)
        self.kind = kind
        self.age = 0.0
        self.base_y = position.y
        pickups.append(self)

    def update(self):
        self.age += time.dt
        self.rotation_y += 120 * time.dt
        self.y = self.base_y + math.sin(self.age * 3) * 0.2
        if G.over:
            return
        if (self.position - player.position).length() < 2.2:
            if self.kind == 'health':
                G.health = min(MAX_HP, G.health + 30)
                update_hp_bar()
                toast('+30 HP', C(0.2, 1, 0.4))
            else:
                G.ammo = MAG
                G.reloading = False
                toast('AMMO REFILLED', C(1, 0.85, 0.2))
            self.remove()
        elif self.age > 15:
            self.remove()

    def remove(self):
        if self in pickups:
            pickups.remove(self)
        destroy(self)


def spawn_enemy():
    ang = random.uniform(0, math.tau)
    r = random.uniform(ARENA - 12, ARENA - 6)
    pos = Vec3(math.cos(ang) * r, 3, math.sin(ang) * r)
    choices = ['grunt'] * 6
    if G.wave >= 2:
        choices += ['runner'] * 3
    if G.wave >= 3:
        choices += ['tank'] * (1 + G.wave // 4)
    enemies.append(Drone(random.choice(choices), pos))


# ----------------------------------------------------------------------------
# Combat
# ----------------------------------------------------------------------------
def hurt_player(dmg):
    if G.over:
        return
    G.health -= dmg
    update_hp_bar()
    damage_flash.color = C(1, 0, 0, 0.4)
    damage_flash.animate_color(C(1, 0, 0, 0), duration=0.4)
    if G.health <= 0:
        game_over()


def shoot():
    if G.reloading:
        return
    if G.ammo <= 0:
        reload()
        return
    G.ammo -= 1
    G.cooldown = FIRE_DELAY

    flash.enabled = True
    invoke(setattr, flash, 'enabled', False, delay=0.04)
    gun_root.z = 0.48
    gun_root.animate_z(0.6, duration=0.1)
    player.camera_pivot.rotation_x -= 0.5

    origin = camera.world_position
    hit = raycast(origin, camera.forward, distance=120, ignore=[player], debug=False)
    start = origin + camera.forward * 1.2 + camera.right * 0.3 + camera.down * 0.25
    end = hit.world_point if hit.hit else origin + camera.forward * 120

    length = (end - start).length()
    tracer = Entity(model='cube', position=(start + end) / 2, scale=(0.03, 0.03, length),
                    color=C(1, 0.9, 0.3), shader=unlit_shader)
    tracer.look_at(end)
    destroy(tracer, delay=0.05)

    if hit.hit:
        if isinstance(hit.entity, Drone):
            hit.entity.hit(1)
            burst(hit.world_point, color.white, 5)
        else:
            burst(hit.world_point, C(0.5, 0.7, 1.0), 4)


def reload():
    if G.reloading or G.ammo == MAG or G.over:
        return
    G.reloading = True
    invoke(finish_reload, delay=RELOAD_TIME)


def finish_reload():
    if G.reloading:
        G.ammo = MAG
        G.reloading = False


# ----------------------------------------------------------------------------
# Game flow
# ----------------------------------------------------------------------------
def start_wave():
    G.wave += 1
    G.to_spawn = 5 + G.wave * 3
    G.spawn_cd = 0.0
    G.intermission = False
    show_banner(f'WAVE {G.wave}', 2.0)


def game_over():
    G.over = True
    G.best = max(G.best, G.score)
    player.enabled = False
    mouse.visible = True
    over_stats.text = f'Score {G.score}     Kills {G.kills}     Wave {G.wave}\nBest {G.best}'
    over_group.enabled = True
    banner.enabled = False


def restart():
    for e in list(enemies):
        destroy(e)
    enemies.clear()
    for p in list(pickups):
        destroy(p)
    pickups.clear()

    G.health, G.ammo, G.reloading, G.cooldown = MAX_HP, MAG, False, 0.0
    G.score = G.kills = G.wave = G.to_spawn = 0
    G.intermission, G.timer, G.banner_t = True, 2.0, 0.0
    update_hp_bar()

    over_group.enabled = False
    player.position = Vec3(0, 2, 0)
    player.rotation_y = 0
    player.camera_pivot.rotation_x = 0
    player.enabled = True
    mouse.locked = True
    G.over = False


def update():
    if G.over:
        return
    dt = time.dt

    player.speed = 14 if held_keys['shift'] else 9
    G.cooldown -= dt
    if held_keys['left mouse'] and G.cooldown <= 0:
        shoot()

    if player.y < -5:
        player.position = Vec3(0, 2, 0)

    # waves
    if G.intermission:
        G.timer -= dt
        if G.timer <= 0:
            start_wave()
    elif G.to_spawn > 0:
        G.spawn_cd -= dt
        if G.spawn_cd <= 0:
            spawn_enemy()
            G.to_spawn -= 1
            G.spawn_cd = max(0.25, 1.0 - G.wave * 0.06)
    elif not enemies:
        G.intermission = True
        G.timer = 4.0
        bonus = 250 * G.wave
        G.score += bonus
        G.health = min(MAX_HP, G.health + 20)
        update_hp_bar()
        show_banner(f'WAVE CLEARED  +{bonus}', 2.5)

    # banner timeout
    if G.banner_t > 0:
        G.banner_t -= dt
        if G.banner_t <= 0:
            banner.enabled = False

    # HUD
    score_text.text = f'SCORE {G.score}'
    wave_text.text = f'WAVE {max(G.wave, 1)}'
    ammo_text.text = 'RELOADING...' if G.reloading else f'{G.ammo} / {MAG}'
    ammo_text.color = C(1, 0.4, 0.3) if (G.reloading or G.ammo <= 5) else color.white


def input(key):
    if key == 'r':
        reload()
    elif key == 'escape':
        application.quit()


update_hp_bar()
show_banner('NEON SIEGE', 2.0)
app.run()