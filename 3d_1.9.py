from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random
import math
import wave
import struct
import os

# --- Sound Synthesis ---
def create_sound_assets():
    sample_rate = 44100

    def write_wav(filename, samples):
        with wave.open(filename, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            raw_data = struct.pack('<' + ('h' * len(samples)), *samples)
            wav_file.writeframes(raw_data)

    if not os.path.exists('coin.wav'):
        duration = 0.22
        samples = []
        n_samples = int(sample_rate * duration)
        for i in range(n_samples):
            t = i / sample_rate
            freq = 987.77 if t < 0.09 else 1318.51
            amplitude = int(18000 * (1 - (t / duration)))
            val = int(amplitude * math.sin(2 * math.pi * freq * t))
            samples.append(max(min(val, 32767), -32768))
        write_wav('coin.wav', samples)

    if not os.path.exists('jump.wav'):
        duration = 0.2
        samples = []
        n_samples = int(sample_rate * duration)
        for i in range(n_samples):
            t = i / sample_rate
            freq = 180 + (t / duration) * 320
            amplitude = int(14000 * (1 - (t / duration)))
            val = int(amplitude * math.sin(2 * math.pi * freq * t))
            samples.append(max(min(val, 32767), -32768))
        write_wav('jump.wav', samples)

    if not os.path.exists('shoot_pistol.wav'):
        duration = 0.16
        samples = []
        n_samples = int(sample_rate * duration)
        for i in range(n_samples):
            t = i / sample_rate
            freq = 950 * math.exp(-20 * t) + 120
            amplitude = int(22000 * (1 - (t / duration)))
            val = int(amplitude * math.sin(2 * math.pi * freq * t))
            samples.append(max(min(val, 32767), -32768))
        write_wav('shoot_pistol.wav', samples)

    if not os.path.exists('shoot_shotgun.wav'):
        duration = 0.38
        samples = []
        n_samples = int(sample_rate * duration)
        for i in range(n_samples):
            t = i / sample_rate
            freq = 240 * math.exp(-12 * t) + 40
            noise = (random.random() * 2 - 1) * 0.45
            tonal = math.sin(2 * math.pi * freq * t)
            amplitude = int(28000 * (1 - (t / duration)))
            val = int(amplitude * (tonal * 0.55 + noise))
            samples.append(max(min(val, 32767), -32768))
        write_wav('shoot_shotgun.wav', samples)

    if not os.path.exists('shoot_smg.wav'):
        duration = 0.08
        samples = []
        n_samples = int(sample_rate * duration)
        for i in range(n_samples):
            t = i / sample_rate
            freq = 1400 * math.exp(-35 * t) + 200
            amplitude = int(19000 * (1 - (t / duration)))
            val = int(amplitude * math.sin(2 * math.pi * freq * t))
            samples.append(max(min(val, 32767), -32768))
        write_wav('shoot_smg.wav', samples)

    if not os.path.exists('switch.wav'):
        duration = 0.06
        samples = []
        n_samples = int(sample_rate * duration)
        for i in range(n_samples):
            t = i / sample_rate
            freq = 1800 if t < 0.03 else 2400
            val = int(12000 * math.sin(2 * math.pi * freq * t))
            samples.append(max(min(val, 32767), -32768))
        write_wav('switch.wav', samples)

    if not os.path.exists('reload.wav'):
        duration = 0.3
        samples = []
        n_samples = int(sample_rate * duration)
        for i in range(n_samples):
            t = i / sample_rate
            freq = 500 if t < 0.15 else 800
            amplitude = int(15000 * (1 - (t / duration)))
            val = int(amplitude * math.sin(2 * math.pi * freq * t))
            samples.append(max(min(val, 32767), -32768))
        write_wav('reload.wav', samples)

    if not os.path.exists('bgm.wav'):
        duration = 4.0
        samples = []
        n_samples = int(sample_rate * duration)
        for i in range(n_samples):
            t = i / sample_rate
            w1 = math.sin(2 * math.pi * 130.81 * t)
            w2 = 0.5 * math.sin(2 * math.pi * 196.00 * t)
            w3 = 0.25 * math.sin(2 * math.pi * 261.63 * t)
            val = int(6000 * ((w1 + w2 + w3) / 1.75))
            samples.append(max(min(val, 32767), -32768))
        write_wav('bgm.wav', samples)

create_sound_assets()

# --- Engine Setup ---
app = Ursina()

# Procedural Meshes
cylinder_mesh = Cylinder(resolution=12)
cone_mesh = Cone(resolution=12)

window.title = "3D Open Forest - Massive Open World"
window.borderless = False
window.fullscreen = False
window.fps_counter.enabled = True

# Atmosphere: lower fog density to accommodate long view distances
sky_dome = Sky(color=color.hex('#78b7e3'))
scene.fog_density = 0.005
scene.fog_color = color.hex('#9ec5d9')
camera.clip_plane_far = 350

# --- Sun & Celestial Lighting ---
sun_light = DirectionalLight(y=80, z=120, x=80, shadows=True, rotation=(45, -35, 0))
ambient_light = AmbientLight(color=color.rgba(110, 120, 130, 210))

sun_orb = Entity(
    model='sphere',
    position=(100, 120, 120),
    scale=16,
    color=color.hex('#FFF68F'),
    unlit=True
)
sun_halo = Entity(
    parent=sun_orb,
    model='sphere',
    scale=1.35,
    color=color.rgba(255, 230, 120, 70),
    unlit=True
)

# Audio
bgm = Audio('bgm.wav', loop=True, autoplay=True, volume=0.25)
coin_sfx = Audio('coin.wav', autoplay=False, loop=False, volume=0.7)
jump_sfx = Audio('jump.wav', autoplay=False, loop=False, volume=0.6)
switch_sfx = Audio('switch.wav', autoplay=False, loop=False, volume=0.6)
reload_sfx = Audio('reload.wav', autoplay=False, loop=False, volume=0.7)

# --- EXPANDED TERRAIN & BOUNDARIES ---
# Arena radius is 140 (280x280 playable zone, ground plane 300x300)
wall_dist = 140
wall_height = 8
wall_col = color.hex('#3e4242')

ground = Entity(
    model='plane',
    scale=(300, 1, 300),
    color=color.hex('#3b6634'),
    texture='grass',
    texture_scale=(150, 150),
    collider='box'
)

walls = [
    Entity(model='cube', scale=(wall_dist * 2, wall_height, 3), position=(0, wall_height / 2, wall_dist), color=wall_col, collider='box'),
    Entity(model='cube', scale=(wall_dist * 2, wall_height, 3), position=(0, wall_height / 2, -wall_dist), color=wall_col, collider='box'),
    Entity(model='cube', scale=(3, wall_height, wall_dist * 2), position=(wall_dist, wall_height / 2, 0), color=wall_col, collider='box'),
    Entity(model='cube', scale=(3, wall_height, wall_dist * 2), position=(-wall_dist, wall_height / 2, 0), color=wall_col, collider='box')
]

# --- Procedural Dynamic Clouds ---
clouds = []

class Cloud(Entity):
    def __init__(self, position=(0, 45, 0)):
        super().__init__(position=position)
        self.drift_speed = random.uniform(1.5, 3.5)
        cloud_color = color.rgba(245, 250, 255, 215)

        puff_offsets = [
            (0, 0, 0, 7.0, 3.5, 6.0),
            (-4.0, -0.6, 0.6, 5.0, 2.6, 4.5),
            (3.8, -0.5, -0.5, 5.2, 2.8, 4.8),
            (1.5, 0.8, 1.8, 4.5, 3.0, 4.2),
            (-1.8, 0.6, -1.5, 4.2, 2.5, 4.0),
        ]
        for ox, oy, oz, sx, sy, sz in puff_offsets:
            Entity(
                parent=self,
                model='sphere',
                position=(ox, oy, oz),
                scale=(sx, sy, sz),
                color=cloud_color,
                unlit=True
            )
        clouds.append(self)

    def update_drift(self):
        self.x += self.drift_speed * time.dt
        if self.x > 170:
            self.x = -170
            self.z = random.uniform(-150, 150)
            self.y = random.uniform(40, 60)

for _ in range(32):
    Cloud(position=(
        random.uniform(-160, 160),
        random.uniform(40, 60),
        random.uniform(-160, 160)
    ))

# --- Foliage & Houses ---
class PineTree(Entity):
    def __init__(self, position=(0, 0, 0)):
        super().__init__(position=position)
        Entity(parent=self, model=cylinder_mesh, color=color.hex('#4a2f1c'), scale=(0.8, 3.8, 0.8), y=1.9, collider='box')
        foliage = [(0, 3.2, 4.0, color.hex('#1d4722')), (0, 4.6, 3.1, color.hex('#265c2c')), (0, 5.8, 2.1, color.hex('#317838'))]
        for ox, oy, s, c in foliage:
            Entity(parent=self, model=cone_mesh, color=c, scale=(s, 2.5, s), y=oy)

class BroadleafTree(Entity):
    def __init__(self, position=(0, 0, 0)):
        super().__init__(position=position)
        Entity(parent=self, model=cylinder_mesh, color=color.hex('#543928'), scale=(0.9, 3.0, 0.9), y=1.5, collider='box')
        Entity(parent=self, model='sphere', scale=(3.4, 2.8, 3.4), y=4.0, color=color.hex('#2e6e2e'))
        Entity(parent=self, model='sphere', scale=(2.6, 2.2, 2.6), position=(0.8, 4.8, -0.4), color=color.hex('#3c8a3c'))

class House(Entity):
    def __init__(self, position=(0, 0, 0), rotation_y=0):
        super().__init__(position=position, rotation_y=rotation_y)
        wall_wood = color.hex('#6e4c30')
        roof_wood = color.hex('#3e2515')
        stone_c = color.hex('#5c5c5c')

        Entity(parent=self, model='cube', scale=(7.0, 3.5, 5.5), y=1.75, color=wall_wood, collider='box')
        Entity(parent=self, model=cone_mesh, scale=(7.8, 2.8, 6.2), y=4.6, rotation_y=45, color=roof_wood)
        Entity(parent=self, model='cube', scale=(0.9, 4.2, 0.9), position=(2.0, 3.4, 1.4), color=stone_c, collider='box')
        Entity(parent=self, model='cube', scale=(1.2, 2.1, 0.2), position=(0, 1.05, 2.76), color=color.hex('#2e190e'))
        Entity(parent=self, model='cube', scale=(1.1, 1.1, 0.1), position=(-2.0, 1.8, 2.76), color=color.hex('#f4d06f'), unlit=True)
        Entity(parent=self, model='cube', scale=(1.1, 1.1, 0.1), position=(2.0, 1.8, 2.76), color=color.hex('#f4d06f'), unlit=True)

class AncientRuin(Entity):
    def __init__(self, position=(0, 0, 0), rotation_y=0):
        super().__init__(position=position, rotation_y=rotation_y)
        stone_col = color.hex('#6e7271')
        moss_col = color.hex('#52574e')
        Entity(parent=self, model='cube', scale=(4, 0.8, 2), y=0.4, color=moss_col, collider='box')
        Entity(parent=self, model=cylinder_mesh, scale=(0.7, 4, 0.7), position=(-1.3, 2.4, 0), color=stone_col, collider='box')
        Entity(parent=self, model=cylinder_mesh, scale=(0.7, 4, 0.7), position=(1.3, 2.4, 0), color=stone_col, collider='box')
        Entity(parent=self, model='cube', scale=(4.2, 0.8, 1.4), y=4.8, color=stone_col, collider='box')

class Altar(Entity):
    def __init__(self, position=(0, 0, 0)):
        super().__init__(position=position)
        Entity(parent=self, model=cylinder_mesh, scale=(2.2, 0.4, 2.2), y=0.2, color=color.hex('#474747'), collider='box')
        Entity(parent=self, model=cylinder_mesh, scale=(1.4, 0.8, 1.4), y=0.8, color=color.hex('#5c5c5c'), collider='box')

# --- Animals ---
active_animals = []

class Deer(Entity):
    def __init__(self, position=(0, 0, 0)):
        super().__init__(position=position, name='animal')
        hide = color.hex('#8b5a2b')
        dark_hide = color.hex('#5c3a1e')

        Entity(parent=self, model='cube', scale=(0.8, 0.9, 1.8), y=1.2, color=hide, collider='box')
        Entity(parent=self, model='cube', scale=(0.4, 0.9, 0.5), position=(0, 1.8, 0.8), rotation_x=-25, color=hide)
        Entity(parent=self, model='cube', scale=(0.45, 0.45, 0.7), position=(0, 2.2, 1.15), color=hide)
        Entity(parent=self, model='cube', scale=(0.08, 0.6, 0.08), position=(-0.25, 2.6, 1.05), rotation_z=-20, color=color.hex('#e8dcc4'))
        Entity(parent=self, model='cube', scale=(0.08, 0.6, 0.08), position=(0.25, 2.6, 1.05), rotation_z=20, color=color.hex('#e8dcc4'))
        Entity(parent=self, model=cylinder_mesh, scale=(0.14, 1.1, 0.14), position=(-0.3, 0.55, 0.7), color=dark_hide)
        Entity(parent=self, model=cylinder_mesh, scale=(0.14, 1.1, 0.14), position=(0.3, 0.55, 0.7), color=dark_hide)
        Entity(parent=self, model=cylinder_mesh, scale=(0.14, 1.1, 0.14), position=(-0.3, 0.55, -0.7), color=dark_hide)
        Entity(parent=self, model=cylinder_mesh, scale=(0.14, 1.1, 0.14), position=(0.3, 0.55, -0.7), color=dark_hide)

        self.move_timer = random.uniform(1.0, 3.0)
        self.is_walking = False
        self.speed = 2.2
        active_animals.append(self)

    def update_ai(self):
        self.move_timer -= time.dt
        if self.move_timer <= 0:
            self.is_walking = not self.is_walking
            self.move_timer = random.uniform(2.0, 5.0)
            if self.is_walking:
                self.rotation_y += random.uniform(-60, 60)

        dist_to_player = distance(self.position, player.position)
        if dist_to_player < 8.0:
            away_vec = (self.position - player.position).normalized()
            self.rotation_y = math.degrees(math.atan2(away_vec.x, away_vec.z))
            self.position += self.forward * 6.0 * time.dt
        elif self.is_walking:
            self.position += self.forward * self.speed * time.dt

        # Clamped inside enlarged map boundary
        self.x = clamp(self.x, -135, 135)
        self.z = clamp(self.z, -135, 135)

class Rabbit(Entity):
    def __init__(self, position=(0, 0, 0)):
        super().__init__(position=position, name='animal')
        fur = color.hex('#e0d5c1')
        Entity(parent=self, model='sphere', scale=(0.4, 0.35, 0.55), y=0.22, color=fur, collider='box')
        Entity(parent=self, model='sphere', scale=(0.28, 0.28, 0.32), position=(0, 0.4, 0.24), color=fur)
        Entity(parent=self, model='cube', scale=(0.06, 0.32, 0.08), position=(-0.08, 0.65, 0.2), rotation_z=-12, color=fur)
        Entity(parent=self, model='cube', scale=(0.06, 0.32, 0.08), position=(0.08, 0.65, 0.2), rotation_z=12, color=fur)

        self.hop_timer = random.uniform(0.5, 2.0)
        active_animals.append(self)

    def update_ai(self):
        self.hop_timer -= time.dt
        if self.hop_timer <= 0:
            self.hop_timer = random.uniform(1.2, 3.0)
            self.rotation_y = random.uniform(0, 360)
            self.animate_position(self.position + self.forward * 1.6 + Vec3(0, 0.4, 0), duration=0.2, curve=curve.out_quad)
            invoke(lambda: self.animate_position(Vec3(self.x, 0, self.z), duration=0.2, curve=curve.in_quad), delay=0.2)

        self.x = clamp(self.x, -135, 135)
        self.z = clamp(self.z, -135, 135)

# --- Aggressive Guardian Enemy with Live Health Bar ---
active_guardians = []

class AggressiveGuardian(Entity):
    def __init__(self, position=(0, 0, 0), rotation_y=0):
        super().__init__(position=position, rotation_y=rotation_y, name='guardian')
        self.max_health = 100
        self.health = 100
        self.speed = 3.2

        armor_col, skin_col, accent_col = color.hex('#8b2626'), color.hex('#c2b280'), color.hex('#3b1a1a')

        Entity(parent=self, model='cube', scale=(0.8, 1.2, 0.5), y=1.6, color=armor_col, collider='box')
        Entity(parent=self, model='sphere', scale=0.5, y=2.4, color=skin_col)
        Entity(parent=self, model='cube', scale=(0.6, 0.1, 0.6), y=2.6, color=accent_col)
        Entity(parent=self, model=cylinder_mesh, scale=(0.25, 1.0, 0.25), position=(-0.25, 0.5, 0), color=accent_col, collider='box')
        Entity(parent=self, model=cylinder_mesh, scale=(0.25, 1.0, 0.25), position=(0.25, 0.5, 0), color=accent_col, collider='box')
        Entity(parent=self, model=cylinder_mesh, scale=(0.2, 1.1, 0.2), position=(-0.55, 1.6, 0), rotation_z=15, color=armor_col)
        Entity(parent=self, model=cylinder_mesh, scale=(0.2, 1.1, 0.2), position=(0.55, 1.6, 0), rotation_z=-15, color=armor_col)

        self.bar_bg = Entity(parent=self, model='quad', scale=(1.2, 0.14), y=3.0, color=color.black, billboard=True)
        self.hp_bar = Entity(parent=self.bar_bg, model='quad', scale=(0.96, 0.7), color=color.red, origin_x=-0.5, x=-0.48)

        active_guardians.append(self)

    def take_damage(self, dmg):
        self.health -= dmg
        ratio = max(0.0, self.health / self.max_health)
        self.hp_bar.scale_x = ratio * 0.96

        if self.health <= 0:
            if self in active_guardians:
                active_guardians.remove(self)
            destroy(self)
            return True
        return False

    def update_ai(self):
        dist = distance(self.position, player.position)
        if 2.2 < dist < 35.0:
            self.look_at_2d(player.position, 'y')
            self.position += self.forward * self.speed * time.dt

# --- Dense Population Across Expanded Area ---

# 1. Multiple House Hamlets
hamlets = [
    (-25, 25, 20), (-35, 12, -35), (-18, -30, 95),
    (60, 50, -15), (75, 40, 110), (-70, -60, 45),
    (40, -80, -70), (-85, 75, 130)
]
for hx, hz, hrot in hamlets:
    House(position=(hx, 0, hz), rotation_y=hrot)

# 2. Forest Trees across 280x280 area
for _ in range(120):
    tx, tz = random.uniform(-130, 130), random.uniform(-130, 130)
    if distance((tx, 0, tz), (0, 0, 0)) > 6:
        PineTree(position=(tx, 0, tz))

for _ in range(80):
    ox, oz = random.uniform(-130, 130), random.uniform(-130, 130)
    if distance((ox, 0, oz), (0, 0, 0)) > 6:
        BroadleafTree(position=(ox, 0, oz))

# 3. Wildlife Population
for _ in range(18):
    dx, dz = random.uniform(-125, 125), random.uniform(-125, 125)
    if distance((dx, 0, dz), (0, 0, 0)) > 8:
        Deer(position=(dx, 0, dz))

for _ in range(26):
    rx, rz = random.uniform(-125, 125), random.uniform(-125, 125)
    if distance((rx, 0, rz), (0, 0, 0)) > 6:
        Rabbit(position=(rx, 0, rz))

# 4. Ancient Ruins & Guardians
for _ in range(14):
    rx, rz = random.uniform(-125, 125), random.uniform(-125, 125)
    if distance((rx, 0, rz), (0, 0, 0)) > 10:
        AncientRuin(position=(rx, 0, rz), rotation_y=random.randint(0, 360))

for _ in range(12):
    gx, gz = random.uniform(-120, 120), random.uniform(-120, 120)
    if distance((gx, 0, gz), (0, 0, 0)) > 12:
        AggressiveGuardian(position=(gx, 0, gz), rotation_y=random.randint(0, 360))

# --- Player & Viewmodel ---
player = FirstPersonController(
    speed=11,          # Increased run speed slightly to fit the larger world
    jump_height=1.6,
    origin_y=-0.5,
    position=(0, 2, 0)
)
player.cursor.color = color.rgba(255, 60, 60, 200)
player.cursor.scale = 0.015

gun_rig = Entity(parent=camera, position=(0.42, -0.32, 0.75), rotation=(0, -5, 0))
default_rig_pos = gun_rig.position

Entity(parent=gun_rig, model='cube', position=(0.08, -0.15, -0.35), scale=(0.14, 0.16, 0.8), rotation=(15, -5, 0), color=color.hex('#d69f7e'))

# 1. Pistol
pistol_root = Entity(parent=gun_rig, enabled=True)
Entity(parent=pistol_root, model='cube', scale=(0.1, 0.14, 0.45), color=color.hex('#22252a'))
Entity(parent=pistol_root, model=cylinder_mesh, position=(0, 0.03, 0.35), scale=(0.06, 0.35, 0.06), rotation=(90, 0, 0), color=color.hex('#101214'))
Entity(parent=pistol_root, model='cube', position=(0, 0.07, 0.05), scale=(0.04, 0.03, 0.3), color=color.cyan)
Entity(parent=pistol_root, model='cube', position=(0, -0.12, -0.1), scale=(0.08, 0.22, 0.1), rotation=(-20, 0, 0), color=color.hex('#353a40'))

# 2. Shotgun
shotgun_root = Entity(parent=gun_rig, enabled=False)
Entity(parent=shotgun_root, model='cube', scale=(0.14, 0.16, 0.5), position=(0, 0, -0.05), color=color.hex('#282828'))
Entity(parent=shotgun_root, model=cylinder_mesh, position=(-0.04, 0.05, 0.45), scale=(0.065, 0.65, 0.065), rotation=(90, 0, 0), color=color.hex('#1a1a1a'))
Entity(parent=shotgun_root, model=cylinder_mesh, position=(0.04, 0.05, 0.45), scale=(0.065, 0.65, 0.065), rotation=(90, 0, 0), color=color.hex('#1a1a1a'))
Entity(parent=shotgun_root, model='cube', position=(0, -0.02, 0.35), scale=(0.12, 0.1, 0.3), color=color.hex('#8B4513'))
Entity(parent=shotgun_root, model='cube', position=(0, -0.16, -0.2), scale=(0.1, 0.26, 0.12), rotation=(-25, 0, 0), color=color.hex('#8B4513'))

# 3. SMG
smg_root = Entity(parent=gun_rig, enabled=False)
Entity(parent=smg_root, model='cube', scale=(0.11, 0.18, 0.42), color=color.hex('#1f2326'))
Entity(parent=smg_root, model=cylinder_mesh, position=(0, 0.04, 0.38), scale=(0.05, 0.4, 0.05), rotation=(90, 0, 0), color=color.hex('#393e46'))
Entity(parent=smg_root, model='cube', position=(0, -0.25, 0.06), scale=(0.06, 0.35, 0.12), rotation=(15, 0, 0), color=color.hex('#0f1112'))
Entity(parent=smg_root, model='cube', position=(0, 0.11, -0.05), scale=(0.04, 0.05, 0.22), color=color.hex('#00adb5'))
Entity(parent=smg_root, model=cylinder_mesh, position=(0, -0.15, 0.25), scale=(0.04, 0.18, 0.04), color=color.hex('#1f2326'))

muzzle_flash = Entity(parent=gun_rig, model='sphere', scale=0.18, enabled=False)

weapons = [
    {
        'name': 'Plasma Pistol',
        'root': pistol_root,
        'sfx': Audio('shoot_pistol.wav', autoplay=False, loop=False, volume=0.8),
        'cooldown': 0.25,
        'recoil_pos': Vec3(0, 0.04, -0.15),
        'recoil_rot': Vec3(-8, -5, 4),
        'flash_pos': Vec3(0, 0.03, 0.6),
        'flash_color': color.cyan,
        'pellets': 1,
        'spread': 0.0,
        'damage': 34,
        'mag_size': 12,
        'current_ammo': 12,
        'reload_time': 1.1,
        'automatic': False
    },
    {
        'name': 'Boomstick Shotgun',
        'root': shotgun_root,
        'sfx': Audio('shoot_shotgun.wav', autoplay=False, loop=False, volume=0.9),
        'cooldown': 0.85,
        'recoil_pos': Vec3(0, 0.10, -0.32),
        'recoil_rot': Vec3(-18, -6, 7),
        'flash_pos': Vec3(0, 0.05, 0.82),
        'flash_color': color.orange,
        'pellets': 8,
        'spread': 0.06,
        'damage': 15,
        'mag_size': 6,
        'current_ammo': 6,
        'reload_time': 1.6,
        'automatic': False
    },
    {
        'name': 'Rapid SMG',
        'root': smg_root,
        'sfx': Audio('shoot_smg.wav', autoplay=False, loop=False, volume=0.7),
        'cooldown': 0.09,
        'recoil_pos': Vec3(0, 0.02, -0.08),
        'recoil_rot': Vec3(-3, -2, 2),
        'flash_pos': Vec3(0, 0.04, 0.62),
        'flash_color': color.yellow,
        'pellets': 1,
        'spread': 0.018,
        'damage': 16,
        'mag_size': 30,
        'current_ammo': 30,
        'reload_time': 1.3,
        'automatic': True
    }
]

current_weapon_idx = 0
time_since_shot = 0.0
is_reloading = False

# HUD
score = 0
score_panel = Entity(parent=camera.ui, model='quad', scale=(0.32, 0.08), position=(-0.68, 0.43), color=color.rgba(0, 0, 0, 140))
score_text = Text(parent=camera.ui, text=f'Gems: {score}', position=(-0.82, 0.45), scale=1.4, color=color.gold)

weapon_panel = Entity(parent=camera.ui, model='quad', scale=(0.42, 0.08), position=(0.64, -0.43), color=color.rgba(0, 0, 0, 160))
weapon_text = Text(parent=camera.ui, text='', position=(0.45, -0.41), scale=1.1, color=color.cyan)

def update_hud():
    wep = weapons[current_weapon_idx]
    color_map = [color.cyan, color.orange, color.yellow]
    status = "RELOADING..." if is_reloading else f"{wep['current_ammo']} / {wep['mag_size']}"
    weapon_text.text = f'[{current_weapon_idx + 1}] {wep["name"]}\nAMMO: {status}'
    weapon_text.color = color_map[current_weapon_idx]

update_hud()

def finish_reload(wep):
    global is_reloading
    wep['current_ammo'] = wep['mag_size']
    is_reloading = False
    gun_rig.animate_position(default_rig_pos, duration=0.15)
    switch_sfx.play()
    update_hud()

def reload_weapon():
    global is_reloading
    wep = weapons[current_weapon_idx]
    if is_reloading or wep['current_ammo'] == wep['mag_size']:
        return

    is_reloading = True
    reload_sfx.play()
    update_hud()

    gun_rig.animate_position(default_rig_pos + Vec3(0, -0.38, 0), duration=0.25)
    invoke(lambda: finish_reload(wep), delay=wep['reload_time'])

def switch_weapon(new_index):
    global current_weapon_idx, is_reloading
    if new_index == current_weapon_idx or not (0 <= new_index < len(weapons)):
        return

    is_reloading = False
    weapons[current_weapon_idx]['root'].enabled = False
    current_weapon_idx = new_index
    current_wep = weapons[current_weapon_idx]
    current_wep['root'].enabled = True

    switch_sfx.play()

    gun_rig.y = default_rig_pos.y - 0.2
    gun_rig.animate_position(default_rig_pos, duration=0.15, curve=curve.out_quad)
    update_hud()

# Collectibles & Particles
active_coins = []
active_particles = []

def spawn_coin():
    x, z = random.uniform(-125, 125), random.uniform(-125, 125)
    Altar(position=(x, 0, z))
    coin_root = Entity(position=(x, 1.8, z), base_y=1.8, seed=random.uniform(0, 100))
    Entity(parent=coin_root, model='diamond', scale=(0.9, 1.3, 0.9), color=color.hex('#FFD700'), collider='box')
    Entity(parent=coin_root, model='sphere', scale=0.4, color=color.white)
    active_coins.append(coin_root)

def trigger_particles(pos, col=color.gold, count=12):
    for _ in range(count):
        p = Entity(
            model='cube',
            scale=0.12,
            color=col,
            position=pos + Vec3(random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15))
        )
        p.velocity = Vec3(random.uniform(-4, 4), random.uniform(2, 6), random.uniform(-4, 4))
        p.lifetime = 0.4
        active_particles.append(p)

# Spawn 24 initial gems across the larger map
for _ in range(24):
    spawn_coin()

def hide_flash():
    muzzle_flash.enabled = False

def fire_weapon():
    global time_since_shot, score
    current_wep = weapons[current_weapon_idx]

    if is_reloading:
        return

    if current_wep['current_ammo'] <= 0:
        reload_weapon()
        return

    if time_since_shot < current_wep['cooldown']:
        return

    time_since_shot = 0.0
    current_wep['current_ammo'] -= 1
    update_hud()
    current_wep['sfx'].play()

    muzzle_flash.position = current_wep['flash_pos']
    muzzle_flash.color = current_wep['flash_color']
    muzzle_flash.enabled = True
    invoke(hide_flash, delay=0.04)

    gun_rig.animate_position(default_rig_pos + current_wep['recoil_pos'], duration=0.03, curve=curve.linear)
    gun_rig.animate_rotation(current_wep['recoil_rot'], duration=0.03)
    invoke(lambda: gun_rig.animate_position(default_rig_pos, duration=0.14, curve=curve.out_bounce), delay=0.04)
    invoke(lambda: gun_rig.animate_rotation(Vec3(0, -5, 0), duration=0.14), delay=0.04)

    pellet_count = current_wep['pellets']
    spread_amt = current_wep['spread']

    for _ in range(pellet_count):
        spread_vec = Vec3(
            random.uniform(-spread_amt, spread_amt),
            random.uniform(-spread_amt, spread_amt),
            random.uniform(-spread_amt, spread_amt)
        )
        fire_dir = (camera.forward + spread_vec).normalized()
        hit_info = raycast(camera.world_position, fire_dir, distance=85, ignore=[player, gun_rig])

        if hit_info.hit:
            trigger_particles(hit_info.world_point, col=current_wep['flash_color'], count=6)
            hit_entity = hit_info.entity

            # Shot Gem
            for c in list(active_coins):
                if hit_entity in c.children or hit_entity == c:
                    coin_sfx.play()
                    trigger_particles(c.position, col=color.gold, count=16)
                    active_coins.remove(c)
                    destroy(c)
                    score += 1
                    score_text.text = f'Gems: {score}'
                    spawn_coin()
                    break

            # Shot Aggressive Guardian
            if hit_entity.parent and isinstance(hit_entity.parent, AggressiveGuardian):
                guardian = hit_entity.parent
                trigger_particles(hit_info.world_point, col=color.smoke, count=8)
                guardian.position += fire_dir * 0.6
                killed = guardian.take_damage(current_wep['damage'])
                if killed:
                    score += 5
                    score_text.text = f'Gems: {score}'

            # Shot Animal (Flee)
            elif hit_entity.parent and getattr(hit_entity.parent, 'name', '') == 'animal':
                trigger_particles(hit_info.world_point, col=color.smoke, count=6)
                animal = hit_entity.parent
                animal.rotation_y = random.uniform(0, 360)
                animal.position += animal.forward * 5.0

# --- Frame Loop ---
def update():
    global score, time_since_shot
    time_since_shot += time.dt
    current_wep = weapons[current_weapon_idx]

    if current_wep['automatic'] and mouse.left:
        fire_weapon()

    # Day / Night Solar Cycle orbiting around larger world
    solar_time = time.time() * 0.05
    sun_x = math.cos(solar_time) * 160
    sun_y = math.sin(solar_time) * 160

    sun_orb.position = Vec3(sun_x, sun_y, 80)
    sun_light.position = sun_orb.position
    sun_light.look_at((0, 0, 0))

    day_factor = clamp(math.sin(solar_time), 0.05, 1.0)
    sky_dome.color = color.rgb(0.47 * day_factor, 0.71 * day_factor, 0.89 * day_factor)
    scene.fog_color = color.rgb(0.62 * day_factor, 0.77 * day_factor, 0.85 * day_factor)
    ambient_light.color = color.rgba(int(110 * day_factor), int(120 * day_factor), int(130 * day_factor), 210)

    # Cloud & Entity updates
    for cloud in clouds:
        cloud.update_drift()

    for animal in active_animals:
        animal.update_ai()

    for guardian in list(active_guardians):
        guardian.update_ai()

    # Gem bobbing
    for coin in list(active_coins):
        coin.rotation_y += 90 * time.dt
        coin.y = coin.base_y + math.sin(time.time() * 3 + coin.seed) * 0.25

        if distance(player.position, coin.position) < 1.7:
            coin_sfx.play()
            trigger_particles(coin.position, col=color.gold, count=14)
            active_coins.remove(coin)
            destroy(coin)
            score += 1
            score_text.text = f'Gems: {score}'
            spawn_coin()

    # Particle simulation
    for p in list(active_particles):
        p.position += p.velocity * time.dt
        p.velocity.y -= 14 * time.dt
        p.scale *= 0.92
        p.lifetime -= time.dt
        if p.lifetime <= 0:
            active_particles.remove(p)
            destroy(p)

    # Weapon sway
    if not is_reloading:
        is_moving = held_keys['w'] or held_keys['a'] or held_keys['s'] or held_keys['d']
        if is_moving and player.grounded:
            sway_x = math.sin(time.time() * 10) * 0.015
            sway_y = math.cos(time.time() * 20) * 0.012
            gun_rig.x = default_rig_pos.x + sway_x
            gun_rig.y = default_rig_pos.y + sway_y
        else:
            gun_rig.y = default_rig_pos.y + math.sin(time.time() * 2) * 0.004

    # Boundary reset
    if player.y < -15:
        player.position = (0, 3, 0)

# Input
def input(key):
    if key == 'left mouse down':
        if not weapons[current_weapon_idx]['automatic']:
            fire_weapon()

    if key == 'r':
        reload_weapon()

    if key == '1': switch_weapon(0)
    if key == '2': switch_weapon(1)
    if key == '3': switch_weapon(2)

    if key == 'scroll up':
        switch_weapon((current_weapon_idx - 1) % len(weapons))
    if key == 'scroll down':
        switch_weapon((current_weapon_idx + 1) % len(weapons))

    if key == 'space' and player.grounded:
        jump_sfx.play()

    if key == 'escape':
        application.quit()

app.run()