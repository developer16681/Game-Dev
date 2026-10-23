"""
=============================================================================
   CYBER TANK: RICOCHET ARENA  --  3D Arcade Action in Ursina Engine
=============================================================================
Controls:
  - WASD / Arrow Keys : Drive Tank
  - Mouse Move        : Aim Turret (with predictive ricochet laser sight)
  - Left Mouse / Space: Fire Ricochet Shell (bounces off walls to hit around corners!)
  - Right Mouse / Shift: Thruster Dash (quick dodge with invulnerability frames)
  - R                 : Restart Game (anytime or after Game Over)
  - ESC               : Pause / Resume / Quit

Features:
  - True 3D bouncing ballistics with realistic surface reflection physics
  - Tactical Ricochet Aim Preview: Shows your primary shot AND first bounce path!
  - 3 Enemy Types: Agile Drones, Lock-on Sentry Turrets, Heavy Goliath Boss Tanks
  - Destructible Cover Crates (drop power-ups) & Chain-reacting Explosive Barrels
  - 5 Power-Ups: Tri-Shot, Hyper-Bounce, Rapid-Fire, Plasma Shield, Repair Core
  - Procedural Sound Synthesis (pure Python standard library -- zero audio files needed!)
  - Screen Shake, Particle Sparks, Debris Physics, Floating Combat Text, Combos!
=============================================================================
"""

import math
import random
import struct
import wave
from pathlib import Path
from ursina import *

# =============================================================================
#  INITIALIZE URSINA APP & SETTINGS
# =============================================================================
app = Ursina(
    title='Cyber Tank: Ricochet Arena',
    borderless=False,
    vsync=True
)
window.fps_counter.enabled = True
window.exit_button.visible = False
window.color = color.hex('#050811')

# Set camera to high-angle isometric perspective
camera.position = (0, 28, -20)
camera.rotation = (54, 0, 0)
camera.fov = 50

# Global sound folder
SOUNDS_DIR = Path(__file__).resolve().parent / 'sounds'


# =============================================================================
#  PROCEDURAL AUDIO SYNTHESIS (Zero External Assets Required)
# =============================================================================
def generate_sound_assets():
    """Synthesizes retro-futuristic arcade sound effects into local WAV files."""
    try:
        SOUNDS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    rate = 22050

    def write_wav(filename, samples):
        filepath = SOUNDS_DIR / filename
        if filepath.exists() and filepath.stat().st_size > 100:
            return
        try:
            with wave.open(str(filepath), 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(rate)
                packed = struct.pack(f'<{len(samples)}h', *samples)
                wf.writeframes(packed)
        except Exception as e:
            print(f"Audio synth notice: {e}")

    # 1. Cannon Shoot: punchy saw/square sweep down
    dur = 0.16
    n = int(rate * dur)
    s_shoot = []
    for i in range(n):
        t = i / rate
        f = 750 * math.exp(-22 * t) + 120
        amp = 24000 * (1 - t / dur)
        val = int(amp * (0.6 * math.sin(2 * math.pi * f * t) + 0.4 * (1 if math.sin(2 * math.pi * f * t) > 0 else -1)))
        s_shoot.append(max(-32767, min(32767, val)))
    write_wav('shoot.wav', s_shoot)

    # 2. Ricochet Ping: high metallic resonant chirp
    dur = 0.14
    n = int(rate * dur)
    s_ricochet = []
    for i in range(n):
        t = i / rate
        f = 1900 + 400 * math.sin(2 * math.pi * 18 * t)
        amp = 20000 * math.exp(-24 * t)
        val = int(amp * (math.sin(2 * math.pi * f * t) + 0.3 * math.sin(2 * math.pi * f * 2.1 * t)))
        s_ricochet.append(max(-32767, min(32767, val)))
    write_wav('ricochet.wav', s_ricochet)

    # 3. Hit Clank: metallic strike + short noise
    dur = 0.11
    n = int(rate * dur)
    s_hit = []
    for i in range(n):
        t = i / rate
        f = 420 * math.exp(-30 * t)
        noise = (random.random() * 2 - 1) * 9000 * (1 - t / dur)
        body = math.sin(2 * math.pi * f * t) * 16000 * (1 - t / dur)
        val = int(body + noise)
        s_hit.append(max(-32767, min(32767, val)))
    write_wav('hit.wav', s_hit)

    # 4. Explosion: deep low rumble + filtered noise
    dur = 0.45
    n = int(rate * dur)
    s_boom = []
    for i in range(n):
        t = i / rate
        f = 120 * math.exp(-8 * t) + 35
        noise = (random.random() * 2 - 1) * 18000 * math.exp(-7 * t)
        bass = math.sin(2 * math.pi * f * t) * 20000 * math.exp(-5 * t)
        val = int(bass + noise)
        s_boom.append(max(-32767, min(32767, val)))
    write_wav('explode.wav', s_boom)

    # 5. Dash Whoosh: aerodynamic filter sweep
    dur = 0.22
    n = int(rate * dur)
    s_dash = []
    for i in range(n):
        t = i / rate
        f = 240 + 700 * math.sin(math.pi * (t / dur))
        noise = (random.random() * 2 - 1) * 12000 * math.sin(math.pi * (t / dur))
        val = int(noise + math.sin(2 * math.pi * f * t) * 10000)
        s_dash.append(max(-32767, min(32767, val)))
    write_wav('dash.wav', s_dash)

    # 6. Power-up Chime: rapid 4-note ascending synth arpeggio
    dur = 0.30
    n = int(rate * dur)
    s_power = []
    notes = [523.25, 659.25, 783.99, 1046.50]  # C5, E5, G5, C6
    for i in range(n):
        t = i / rate
        step = min(3, int(t / (dur / 4)))
        f = notes[step]
        sub_t = t - step * (dur / 4)
        env = math.exp(-12 * sub_t)
        val = int(18000 * env * (math.sin(2 * math.pi * f * t) + 0.25 * math.sin(4 * math.pi * f * t)))
        s_power.append(max(-32767, min(32767, val)))
    write_wav('powerup.wav', s_power)

    # 7. Wave Clear Fanfare: bright triad chord
    dur = 0.55
    n = int(rate * dur)
    s_clear = []
    for i in range(n):
        t = i / rate
        env = (1 - t / dur)
        val = int(env * 8000 * (
            math.sin(2 * math.pi * 587.33 * t) +   # D5
            math.sin(2 * math.pi * 739.99 * t) +   # F#5
            math.sin(2 * math.pi * 880.00 * t)     # A5
        ))
        s_clear.append(max(-32767, min(32767, val)))
    write_wav('wave_clear.wav', s_clear)

    # 8. Game Over: sad descending minor sweep
    dur = 0.65
    n = int(rate * dur)
    s_over = []
    for i in range(n):
        t = i / rate
        f = 330 * math.exp(-3.2 * t)
        env = math.exp(-3.5 * t)
        val = int(20000 * env * (math.sin(2 * math.pi * f * t) + 0.3 * math.sin(2 * math.pi * (f * 1.5) * t)))
        s_over.append(max(-32767, min(32767, val)))
    write_wav('game_over.wav', s_over)


generate_sound_assets()


def play_sfx(name, vol=0.65, pitch=1.0):
    """Safely plays a sound without throwing errors if audio device is unavailable."""
    path = SOUNDS_DIR / name
    if path.exists():
        try:
            snd = Audio(str(path), autoplay=True, auto_destroy=True, volume=vol)
            if hasattr(snd, 'pitch'):
                snd.pitch = pitch
        except Exception:
            pass


# =============================================================================
#  VISUAL EFFECTS & JUICE MANAGERS
# =============================================================================
class CameraShake:
    """Handles punchy camera trauma and screen shake."""
    def __init__(self):
        self.trauma = 0.0
        self.base_pos = Vec3(0, 28, -20)

    def add(self, amount):
        self.trauma = min(1.0, self.trauma + amount)

    def update(self):
        if self.trauma > 0:
            shake = (self.trauma ** 2) * 1.6
            ox = (random.random() * 2 - 1) * shake
            oy = (random.random() * 2 - 1) * shake * 0.5
            oz = (random.random() * 2 - 1) * shake * 0.7
            camera.position = self.base_pos + Vec3(ox, oy, oz)
            self.trauma = max(0.0, self.trauma - time.dt * 2.8)
        else:
            camera.position = self.base_pos


camera_shake = CameraShake()


class SparkParticle(Entity):
    """Bright spark launched from bullet ricochets and impacts."""
    def __init__(self, position, velocity, clr=color.cyan, life=0.35, scale_size=0.18):
        super().__init__(
            model='sphere',
            color=clr,
            position=position,
            scale=scale_size,
            unlit=True
        )
        self.velocity = velocity
        self.life = life
        self.max_life = life

    def update(self):
        self.position += self.velocity * time.dt
        self.velocity.y -= 14.0 * time.dt  # Gravity
        self.life -= time.dt
        progress = self.life / self.max_life
        self.scale = max(0.01, progress * 0.22)
        if self.life <= 0:
            destroy(self)


class DebrisCube(Entity):
    """3D tumbling debris cube spawned when crates or tanks shatter."""
    def __init__(self, position, clr=color.gray, force=6.0):
        super().__init__(
            model='cube',
            color=clr,
            position=position + Vec3(random.uniform(-0.3, 0.3), random.uniform(0.1, 0.5), random.uniform(-0.3, 0.3)),
            scale=random.uniform(0.2, 0.38),
            rotation=(random.uniform(0, 360), random.uniform(0, 360), random.uniform(0, 360))
        )
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(2.0, force)
        self.vel = Vec3(math.cos(angle) * speed, random.uniform(4.0, 9.0), math.sin(angle) * speed)
        self.rot_speed = Vec3(random.uniform(-300, 300), random.uniform(-300, 300), random.uniform(-300, 300))
        self.life = random.uniform(1.2, 2.0)

    def update(self):
        self.position += self.vel * time.dt
        self.vel.y -= 22.0 * time.dt
        if self.y < 0.2:
            self.y = 0.2
            self.vel.y = -self.vel.y * 0.45
            self.vel.x *= 0.75
            self.vel.z *= 0.75
        self.rotation += self.rot_speed * time.dt
        self.life -= time.dt
        if self.life < 0.4:
            self.scale = max(0.01, (self.life / 0.4) * 0.3)
        if self.life <= 0:
            destroy(self)


class FloatingText(Entity):
    """Arcade score and notification text floating in 3D world space."""
    def __init__(self, text, position, clr=color.yellow, scale_mult=1.0):
        super().__init__(
            parent=scene,
            position=position + Vec3(0, 1.2, 0),
            billboard=True
        )
        self.txt = Text(
            text=text,
            parent=self,
            origin=(0, 0),
            color=clr,
            scale=14 * scale_mult
        )
        self.life = 0.85
        self.vy = 2.4

    def update(self):
        self.position += Vec3(0, self.vy * time.dt, 0)
        self.vy = max(0.5, self.vy - time.dt * 2.0)
        self.life -= time.dt
        alpha = min(1.0, self.life / 0.4)
        self.txt.color = color.rgba(self.txt.color.r, self.txt.color.g, self.txt.color.b, alpha)
        if self.life <= 0:
            destroy(self.txt)
            destroy(self)


def spawn_explosion_fx(pos, clr=color.orange, count=16, is_big=False):
    """Creates a flash, sparks, expanding shockwave, and screen shake."""
    camera_shake.add(0.35 if is_big else 0.2)
    # Expanding flash sphere
    flash = Entity(
        model='sphere',
        position=pos + Vec3(0, 0.4, 0),
        scale=1.2 if is_big else 0.7,
        color=color.white,
        unlit=True
    )
    flash.animate_scale(4.5 if is_big else 2.4, duration=0.2, curve=curve.out_expo)
    flash.fade_out(duration=0.22)
    destroy(flash, delay=0.25)

    # Sparks in a spherical spray
    spark_count = count * (2 if is_big else 1)
    for _ in range(spark_count):
        theta = random.uniform(0, math.pi * 2)
        phi = random.uniform(-0.2, math.pi * 0.45)
        spd = random.uniform(5, 14 if is_big else 9)
        vel = Vec3(math.cos(theta) * math.cos(phi) * spd, math.sin(phi) * spd + 2.0, math.sin(theta) * math.cos(phi) * spd)
        p_clr = random.choice([color.white, color.yellow, clr, color.hex('#ff3366')])
        SparkParticle(pos + Vec3(0, 0.3, 0), vel, clr=p_clr, life=random.uniform(0.3, 0.65))

    # Debris blocks
    for _ in range(6 if is_big else 3):
        DebrisCube(pos, clr=color.hex('#2c3e50'), force=8 if is_big else 5)


# =============================================================================
#  RICOCHET BALLISTICS & LASER SIGHT
# =============================================================================
class RicochetBullet(Entity):
    """
    High-speed projectile that accurately reflects off walls and obstacles.
    Features:
      - Vector reflection on collision normals
      - Spark bursts and distinct audio on ricochet
      - Hits enemies, barrels, and crates
      - Can damage shooter only AFTER at least one bounce (classic trick-shot rule!)
    """
    def __init__(self, position, direction, speed=32.0, max_bounces=2, owner=None, damage=35, clr=color.cyan):
        super().__init__(
            model='sphere',
            position=position,
            scale=(0.35, 0.35, 0.75),
            color=clr,
            unlit=True
        )
        self.direction = direction.normalized()
        self.look_at(self.position + self.direction)
        self.speed = speed
        self.bounces_left = max_bounces
        self.bounces_done = 0
        self.owner = owner
        self.damage = damage
        self.bullet_color = clr
        self.lifetime = 4.0

        # Glowing trailing tail
        self.tail = Entity(
            parent=self,
            model='cylinder',
            position=(0, 0, -0.6),
            rotation=(90, 0, 0),
            scale=(0.18, 0.8, 0.18),
            color=color.rgba(clr.r, clr.g, clr.b, 0.5),
            unlit=True
        )

        game.bullets.append(self)

    def update(self):
        step_dist = self.speed * time.dt
        ignore_list = [self, self.tail]
        # Ignore owner ONLY before the first bounce so player cannot shoot themselves point-blank
        if self.bounces_done == 0 and self.owner is not None:
            if hasattr(self.owner, 'parts'):
                ignore_list.extend(self.owner.parts)
            else:
                ignore_list.append(self.owner)

        # Continuous raycast collision detection along flight path
        hit = raycast(
            self.world_position,
            self.forward,
            distance=step_dist + 0.15,
            ignore=ignore_list
        )

        if hit.hit:
            hit_ent = hit.entity

            # Check if we struck a damageable target (Player, Enemy, Barrel, Crate)
            target = getattr(hit_ent, 'damage_target', None) or hit_ent
            if hasattr(target, 'take_damage') and target != self.owner or (self.bounces_done > 0 and hasattr(target, 'take_damage')):
                # Score multiplier bonus for ricochet trick shots!
                bonus_mult = 1.0 + (self.bounces_done * 0.5)
                dealt = int(self.damage * bonus_mult)
                target.take_damage(dealt, attacker=self.owner)

                if self.bounces_done > 0 and self.owner == game.player:
                    FloatingText(f"RICOCHET x{self.bounces_done}!", hit.point, clr=color.hex('#00ffff'), scale_mult=1.3)
                    game.score += 75 * self.bounces_done

                # Spark hit effect
                for _ in range(8):
                    vel = (hit.normal + Vec3(random.uniform(-0.5, 0.5), random.uniform(0.1, 0.8), random.uniform(-0.5, 0.5))).normalized() * random.uniform(4, 9)
                    SparkParticle(hit.point, vel, clr=self.bullet_color)

                play_sfx('hit.wav', vol=0.7)
                self.destroy_bullet()
                return

            # Check if we struck a reflective wall or solid obstacle
            if getattr(hit_ent, 'is_reflective', False) or getattr(hit_ent, 'is_wall', False):
                # Calculate physics reflection: R = V - 2 * (V . N) * N
                normal = hit.normal
                if normal.length() < 0.1:
                    normal = -self.forward
                normal = normal.normalized()

                dot = self.direction.dot(normal)
                refl = (self.direction - 2 * dot * normal).normalized()

                self.direction = refl
                self.world_position = hit.point + normal * 0.12
                self.look_at(self.world_position + self.direction)

                self.bounces_left -= 1
                self.bounces_done += 1

                # Visual & audio feedback for crisp bounce
                play_sfx('ricochet.wav', vol=0.6, pitch=random.uniform(0.9, 1.15))
                for _ in range(6):
                    v = (normal + Vec3(random.uniform(-0.6, 0.6), random.uniform(0.2, 0.9), random.uniform(-0.6, 0.6))).normalized() * random.uniform(3, 7)
                    SparkParticle(hit.point, v, clr=color.yellow, life=0.25)

                if self.bounces_left <= 0:
                    self.fizzle_bullet()
                return

            # Hit anything else solid
            self.destroy_bullet()
            return

        # No collision: move forward normally
        self.world_position += self.forward * step_dist
        self.lifetime -= time.dt
        if self.lifetime <= 0:
            self.destroy_bullet()

    def fizzle_bullet(self):
        for _ in range(5):
            vel = Vec3(random.uniform(-1, 1), random.uniform(0.2, 1), random.uniform(-1, 1)).normalized() * random.uniform(2, 4)
            SparkParticle(self.world_position, vel, clr=self.bullet_color, life=0.2)
        self.destroy_bullet()

    def destroy_bullet(self):
        if self in game.bullets:
            game.bullets.remove(self)
        destroy(self.tail)
        destroy(self)


class LaserSight:
    """Predictive targeting laser that renders the primary ray and first reflection."""
    def __init__(self, tank):
        self.tank = tank
        # Beam segment 1: Tank to first obstacle
        self.beam1 = Entity(
            model='cube',
            color=color.rgba(0, 255, 255, 0.6),
            scale=(0.04, 0.04, 1),
            unlit=True,
            enabled=True
        )
        # Dot at first bounce point
        self.dot = Entity(
            model='sphere',
            color=color.hex('#00ffff'),
            scale=0.22,
            unlit=True,
            enabled=True
        )
        # Beam segment 2: Reflected path
        self.beam2 = Entity(
            model='cube',
            color=color.rgba(255, 220, 0, 0.45),
            scale=(0.03, 0.03, 1),
            unlit=True,
            enabled=True
        )

    def update(self, origin, forward_dir):
        ignore_parts = self.tank.parts + [self.beam1, self.dot, self.beam2]
        hit1 = raycast(origin, forward_dir, distance=35.0, ignore=ignore_parts)

        if hit1.hit:
            dist1 = hit1.distance
            self.beam1.enabled = True
            self.beam1.world_position = origin + forward_dir * (dist1 * 0.5)
            self.beam1.scale_z = dist1
            self.beam1.look_at(hit1.point)

            self.dot.enabled = True
            self.dot.world_position = hit1.point

            # Calculate reflection for preview
            normal = hit1.normal
            if normal.length() > 0.1:
                normal = normal.normalized()
                refl_dir = (forward_dir - 2 * forward_dir.dot(normal) * normal).normalized()
                hit2 = raycast(hit1.point + normal * 0.05, refl_dir, distance=18.0, ignore=ignore_parts + [hit1.entity])
                dist2 = hit2.distance if hit2.hit else 14.0
                end_pt = (hit1.point + normal * 0.05) + refl_dir * dist2

                self.beam2.enabled = True
                self.beam2.world_position = (hit1.point + normal * 0.05) + refl_dir * (dist2 * 0.5)
                self.beam2.scale_z = dist2
                self.beam2.look_at(end_pt)
            else:
                self.beam2.enabled = False
        else:
            self.beam1.enabled = True
            self.beam1.world_position = origin + forward_dir * 15.0
            self.beam1.scale_z = 30.0
            self.beam1.look_at(origin + forward_dir * 30.0)
            self.dot.enabled = False
            self.beam2.enabled = False

    def disable(self):
        self.beam1.enabled = False
        self.dot.enabled = False
        self.beam2.enabled = False

    def destroy_self(self):
        destroy(self.beam1)
        destroy(self.dot)
        destroy(self.beam2)


# =============================================================================
#  ARENA PROPS: DESTRUCTIBLE CRATES & EXPLOSIVE BARRELS
# =============================================================================
class SupplyCrate(Entity):
    """Destructible energy cache that shatters and drops power-ups."""
    def __init__(self, position):
        super().__init__(
            model='cube',
            position=position + Vec3(0, 0.75, 0),
            scale=(1.5, 1.5, 1.5),
            color=color.hex('#1b4965'),
            collider='box'
        )
        self.damage_target = self
        self.is_reflective = True
        self.is_destructible = True
        self.hp = 20

        # Glowing neon frame
        self.frame = Entity(
            parent=self,
            model='cube',
            scale=(1.02, 1.02, 1.02),
            color=color.hex('#62b6cb'),
            wireframe=True
        )
        game.destructibles.append(self)

    def take_damage(self, amount, attacker=None):
        self.hp -= amount
        # Flash
        self.color = color.white
        invoke(setattr, self, 'color', color.hex('#1b4965'), delay=0.08)

        if self.hp <= 0:
            self.shatter()

    def shatter(self):
        spawn_explosion_fx(self.world_position, clr=color.hex('#62b6cb'), count=10)
        play_sfx('hit.wav', vol=0.8, pitch=0.8)

        # 60% chance to drop a random Power-Up
        if random.random() < 0.65:
            ptype = random.choice(['TRI_SHOT', 'HYPER_BOUNCE', 'RAPID_FIRE', 'SHIELD', 'HEALTH'])
            PowerUp(self.world_position, ptype)

        if self in game.destructibles:
            game.destructibles.remove(self)
        destroy(self.frame)
        destroy(self)


class ExplosiveBarrel(Entity):
    """Volatile plasma cylinder that chain-reacts and damages nearby combatants."""
    def __init__(self, position):
        super().__init__(
            model='cylinder',
            position=position + Vec3(0, 0.8, 0),
            scale=(1.2, 1.6, 1.2),
            color=color.hex('#e63946'),
            collider='box'
        )
        self.damage_target = self
        self.is_reflective = True
        self.hp = 15
        self.primed = False

        # Yellow hazard band
        self.band = Entity(
            parent=self,
            model='cylinder',
            position=(0, 0, 0),
            scale=(1.03, 0.35, 1.03),
            color=color.hex('#ffbe0b')
        )
        game.destructibles.append(self)

    def take_damage(self, amount, attacker=None):
        self.hp -= amount
        if self.hp <= 0 and not self.primed:
            self.primed = True
            # Flash fast before detonating
            self.color = color.white
            invoke(self.detonate, delay=0.15)

    def detonate(self):
        play_sfx('explode.wav', vol=0.9, pitch=0.9)
        spawn_explosion_fx(self.world_position, clr=color.hex('#e63946'), count=24, is_big=True)
        FloatingText("BOOM!", self.world_position, clr=color.hex('#ff3366'), scale_mult=1.5)

        blast_radius = 5.8
        blast_damage = 70

        # Damage player if caught in radius
        if game.player and game.player.alive:
            dist = (game.player.world_position - self.world_position).length()
            if dist < blast_radius:
                dmg = int(blast_damage * (1 - dist / blast_radius))
                game.player.take_damage(dmg)

        # Damage enemies
        for e in game.enemies[:]:
            if e and e.alive:
                dist = (e.world_position - self.world_position).length()
                if dist < blast_radius:
                    dmg = int(blast_damage * (1 - dist / blast_radius))
                    e.take_damage(dmg)

        # Chain reaction on nearby barrels / crates
        for d in game.destructibles[:]:
            if d != self and d.enabled:
                dist = (d.world_position - self.world_position).length()
                if dist < blast_radius:
                    d.take_damage(50)

        if self in game.destructibles:
            game.destructibles.remove(self)
        destroy(self.band)
        destroy(self)


# =============================================================================
#  POWER-UP ITEMS
# =============================================================================
class PowerUp(Entity):
    """Floating collectible crystal that grants powerful tactical upgrades."""
    CONFIGS = {
        'TRI_SHOT':     {'clr': color.hex('#00f0ff'), 'label': 'TRI-SHOT',     'icon': '3x'},
        'HYPER_BOUNCE': {'clr': color.hex('#ffe600'), 'label': 'HYPER BOUNCE', 'icon': '4B'},
        'RAPID_FIRE':   {'clr': color.hex('#ff0055'), 'label': 'RAPID FIRE',  'icon': 'RF'},
        'SHIELD':       {'clr': color.hex('#7928ca'), 'label': 'FORCE SHIELD', 'icon': 'SH'},
        'HEALTH':       {'clr': color.hex('#00ff88'), 'label': 'REPAIR CORE',  'icon': '+HP'}
    }

    def __init__(self, position, ptype):
        self.ptype = ptype
        cfg = self.CONFIGS.get(ptype, self.CONFIGS['HEALTH'])

        super().__init__(
            model='sphere',
            position=position + Vec3(0, 0.8, 0),
            scale=(0.7, 0.7, 0.7),
            color=cfg['clr'],
            unlit=True
        )
        self.ring = Entity(
            parent=self,
            model='cylinder',
            scale=(1.4, 0.08, 1.4),
            rotation=(35, 0, 20),
            color=color.white,
            wireframe=True
        )
        self.base_y = self.y
        self.time_offset = random.uniform(0, 10)
        game.powerups.append(self)

    def update(self):
        # Bobbing and rotation animation
        t = time.time() + self.time_offset
        self.y = self.base_y + math.sin(t * 3.5) * 0.22
        self.rotation_y += 90 * time.dt
        self.ring.rotation_x += 120 * time.dt

        # Check pickup distance from player
        if game.player and game.player.alive:
            dist = (self.world_position - game.player.world_position).length()
            if dist < 1.7:
                self.collect()

    def collect(self):
        play_sfx('powerup.wav', vol=0.8)
        game.player.apply_powerup(self.ptype)
        cfg = self.CONFIGS[self.ptype]
        FloatingText(cfg['label'] + "!", self.world_position, clr=cfg['clr'], scale_mult=1.4)
        for _ in range(12):
            v = Vec3(random.uniform(-1, 1), random.uniform(0.3, 1.2), random.uniform(-1, 1)).normalized() * random.uniform(3, 7)
            SparkParticle(self.world_position, v, clr=cfg['clr'])

        if self in game.powerups:
            game.powerups.remove(self)
        destroy(self.ring)
        destroy(self)


# =============================================================================
#  PLAYER TANK
# =============================================================================
class PlayerTank(Entity):
    """
    Player-controlled twin-stick cyber tank.
    - WASD movement (screen-oriented, smooth acceleration)
    - Independent mouse-aimed turret with laser reflection sight
    - Thruster Dash with invulnerability frames and ghost trails
    """
    def __init__(self, position=Vec3(0, 0, -8)):
        super().__init__(position=position)
        self.alive = True
        self.max_hp = 100
        self.hp = 100
        self.speed = 10.5
        self.velocity = Vec3(0, 0, 0)
        self.parts = []

        # Chassis Body
        self.chassis = Entity(
            parent=self,
            model='cube',
            scale=(1.8, 0.55, 2.2),
            position=(0, 0.35, 0),
            color=color.hex('#0d2b45'),
            collider='box'
        )
        self.chassis.damage_target = self
        self.parts.append(self.chassis)

        # Dual Treads
        for side in (-0.95, 0.95):
            tread = Entity(
                parent=self,
                model='cube',
                scale=(0.38, 0.45, 2.35),
                position=(side, 0.3, 0),
                color=color.hex('#081624')
            )
            self.parts.append(tread)

        # Glowing Engine Exhaust Vents
        self.exhaust = Entity(
            parent=self,
            model='cube',
            scale=(0.9, 0.18, 0.15),
            position=(0, 0.45, -1.05),
            color=color.hex('#00ffff'),
            unlit=True
        )
        self.parts.append(self.exhaust)

        # Turret Rotator (tracks mouse in 3D world space)
        self.turret = Entity(parent=self, position=(0, 0.65, 0))

        self.turret_dome = Entity(
            parent=self.turret,
            model='sphere',
            scale=(1.1, 0.65, 1.1),
            position=(0, 0, -0.1),
            color=color.hex('#144569')
        )
        self.parts.append(self.turret_dome)

        # Cannon Barrel with Recoil
        self.barrel = Entity(
            parent=self.turret,
            model='cylinder',
            scale=(0.24, 1.4, 0.24),
            position=(0, 0.12, 0.8),
            rotation=(90, 0, 0),
            color=color.hex('#20639b')
        )
        self.muzzle_tip = Entity(
            parent=self.turret,
            model='cylinder',
            scale=(0.28, 0.25, 0.28),
            position=(0, 0.12, 1.55),
            rotation=(90, 0, 0),
            color=color.hex('#00ffff'),
            unlit=True
        )
        self.parts.extend([self.barrel, self.muzzle_tip])

        # Laser Sight
        self.laser = LaserSight(self)

        # Force Shield Sphere (hidden until acquired)
        self.shield_bubble = Entity(
            parent=self,
            model='sphere',
            scale=(2.6, 2.2, 2.6),
            position=(0, 0.6, 0),
            color=color.rgba(121, 40, 202, 0.35),
            unlit=True,
            enabled=False
        )

        # Combat & Cooldown state
        self.shoot_cooldown = 0.0
        self.fire_rate = 0.28
        self.dash_cooldown = 0.0
        self.dash_timer = 0.0
        self.is_dashing = False
        self.invulnerable = False

        # Active Power-up Durations
        self.active_buffs = {}

    def update(self):
        if not self.alive:
            self.laser.disable()
            return

        dt = time.dt

        # Update power-up timers
        expired = []
        for buff, timer in self.active_buffs.items():
            self.active_buffs[buff] = timer - dt
            if self.active_buffs[buff] <= 0:
                expired.append(buff)
        for b in expired:
            del self.active_buffs[b]
            if b == 'SHIELD':
                self.shield_bubble.enabled = False

        # Cooldown ticks
        self.shoot_cooldown = max(0.0, self.shoot_cooldown - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)

        # Movement handling (WASD)
        move_dir = Vec3(0, 0, 0)
        if held_keys['w'] or held_keys['up arrow']:    move_dir.z += 1
        if held_keys['s'] or held_keys['down arrow']:  move_dir.z -= 1
        if held_keys['a'] or held_keys['left arrow']:  move_dir.x -= 1
        if held_keys['d'] or held_keys['right arrow']: move_dir.x += 1

        if move_dir.length() > 0.1:
            move_dir = move_dir.normalized()
            # Smooth chassis rotation toward travel direction
            target_rot = math.degrees(math.atan2(move_dir.x, move_dir.z))
            self.rotation_y = lerp_angle(self.rotation_y, target_rot, dt * 14.0)

            # Tread dust particles
            if random.random() < 0.35:
                pos = self.world_position + Vec3(random.uniform(-0.8, 0.8), 0.1, -1.0)
                SparkParticle(pos, Vec3(0, 0.6, -1.5), clr=color.hex('#005577'), life=0.2, scale_size=0.1)

        # Handle Dash
        if self.is_dashing:
            self.dash_timer -= dt
            # Spawn after-image ghost silhouette
            if random.random() < 0.6:
                ghost = Entity(
                    model='cube',
                    position=self.world_position + Vec3(0, 0.4, 0),
                    rotation=self.rotation,
                    scale=(1.8, 0.5, 2.2),
                    color=color.rgba(0, 255, 255, 0.35),
                    unlit=True
                )
                ghost.fade_out(duration=0.2)
                destroy(ghost, delay=0.22)

            if self.dash_timer <= 0:
                self.is_dashing = False
                self.invulnerable = False
        else:
            speed_mult = 1.0
            self.velocity = lerp(self.velocity, move_dir * (self.speed * speed_mult), dt * 12.0)

        # Move and clamp within arena boundary
        new_pos = self.position + self.velocity * dt
        new_pos.x = max(-15.0, min(15.0, new_pos.x))
        new_pos.z = max(-11.5, min(11.5, new_pos.z))
        self.position = new_pos

        # Mouse Aiming in 3D: Raycast from camera along mouse ray to ground plane (Y=0)
        aim_pt = None
        if mouse.ray and mouse.ray.direction.y != 0:
            # Exact mathematical ray-plane intersection at Y=0.7
            t = (0.7 - camera.world_position.y) / mouse.ray.direction.y
            if t > 0:
                aim_pt = camera.world_position + mouse.ray.direction * t

        if aim_pt is None and mouse.world_point:
            aim_pt = mouse.world_point

        if aim_pt:
            # Aim turret at cursor position
            look_pos = Vec3(aim_pt.x, self.turret.world_y, aim_pt.z)
            self.turret.look_at(look_pos)

            # Update tactical laser sight
            muzzle_wpos = self.muzzle_tip.world_position
            fwd = self.turret.forward
            self.laser.update(muzzle_wpos, fwd)

        # Automatic firing if left mouse held
        if (held_keys['left mouse'] or held_keys['space']) and self.shoot_cooldown <= 0:
            self.fire_cannon()

    def fire_cannon(self):
        cur_rate = self.fire_rate * (0.45 if 'RAPID_FIRE' in self.active_buffs else 1.0)
        self.shoot_cooldown = cur_rate

        # Barrel recoil animation
        self.barrel.z = 0.55
        self.barrel.animate_position((0, 0.12, 0.8), duration=0.12, curve=curve.out_quad)

        # Muzzle flash
        flash = Entity(
            model='sphere',
            position=self.muzzle_tip.world_position,
            scale=0.6,
            color=color.hex('#00ffff'),
            unlit=True
        )
        flash.animate_scale(0.1, duration=0.06)
        destroy(flash, delay=0.07)

        play_sfx('shoot.wav', vol=0.75, pitch=random.uniform(0.95, 1.05))
        camera_shake.add(0.08)

        # Determine bullet parameters
        max_bounces = 4 if 'HYPER_BOUNCE' in self.active_buffs else 2
        bullet_clr = color.hex('#ffe600') if 'HYPER_BOUNCE' in self.active_buffs else color.hex('#00ffff')
        spd = 38.0 if 'HYPER_BOUNCE' in self.active_buffs else 30.0

        muzzle_pos = self.muzzle_tip.world_position + self.turret.forward * 0.2

        if 'TRI_SHOT' in self.active_buffs:
            # 3-way spread pattern (-18, 0, +18 degrees)
            for angle_offset in (-18, 0, 18):
                rad = math.radians(angle_offset)
                cos_a = math.cos(rad)
                sin_a = math.sin(rad)
                fwd = self.turret.forward
                spread_dir = Vec3(
                    fwd.x * cos_a - fwd.z * sin_a,
                    0,
                    fwd.x * sin_a + fwd.z * cos_a
                ).normalized()
                RicochetBullet(muzzle_pos, spread_dir, speed=spd, max_bounces=max_bounces, owner=self, clr=bullet_clr)
        else:
            RicochetBullet(muzzle_pos, self.turret.forward, speed=spd, max_bounces=max_bounces, owner=self, clr=bullet_clr)

    def trigger_dash(self):
        if self.dash_cooldown > 0 or not self.alive:
            return
        self.dash_cooldown = 1.6
        self.is_dashing = True
        self.dash_timer = 0.22
        self.invulnerable = True

        # Dash in movement direction (or chassis forward if stationary)
        dash_dir = self.velocity.normalized() if self.velocity.length() > 0.5 else self.forward
        self.velocity = dash_dir * 28.0

        play_sfx('dash.wav', vol=0.8)
        camera_shake.add(0.12)

    def apply_powerup(self, ptype):
        if ptype == 'HEALTH':
            self.hp = min(self.max_hp, self.hp + 40)
            game.update_hud()
            return
        if ptype == 'SHIELD':
            self.active_buffs['SHIELD'] = 15.0
            self.shield_bubble.enabled = True
            return
        # Other powerups have 10-second timer
        self.active_buffs[ptype] = 11.0

    def take_damage(self, amount, attacker=None):
        if not self.alive or self.invulnerable:
            return

        # Shield absorbs hit entirely
        if 'SHIELD' in self.active_buffs:
            del self.active_buffs['SHIELD']
            self.shield_bubble.enabled = False
            play_sfx('ricochet.wav', vol=0.9, pitch=1.4)
            FloatingText("SHIELD BROKEN!", self.world_position, clr=color.hex('#7928ca'))
            for _ in range(10):
                v = Vec3(random.uniform(-1, 1), random.uniform(0.1, 1), random.uniform(-1, 1)).normalized() * 5
                SparkParticle(self.world_position, v, clr=color.hex('#7928ca'))
            return

        self.hp = max(0, self.hp - amount)
        camera_shake.add(0.28)
        play_sfx('hit.wav', vol=0.85, pitch=0.8)
        FloatingText(f"-{amount}", self.world_position, clr=color.red)

        # Hull damage flash
        self.chassis.color = color.red
        invoke(setattr, self.chassis, 'color', color.hex('#0d2b45'), delay=0.1)

        game.update_hud()

        if self.hp <= 0:
            self.destroy_tank()

    def destroy_tank(self):
        self.alive = False
        self.laser.disable()
        spawn_explosion_fx(self.world_position, clr=color.hex('#00ffff'), count=28, is_big=True)
        play_sfx('explode.wav', vol=1.0)
        play_sfx('game_over.wav', vol=0.9)
        self.enabled = False
        game.on_player_death()

    def destroy_self(self):
        self.laser.destroy_self()
        destroy(self.shield_bubble)
        destroy(self)


# =============================================================================
#  ENEMY AI COMBATANTS
# =============================================================================
class EnemyBase(Entity):
    """Base class for autonomous cyber combat units."""
    def __init__(self, position, hp=40, speed=5.0, score_val=150):
        super().__init__(position=position)
        self.alive = True
        self.hp = hp
        self.max_hp = hp
        self.speed = speed
        self.score_val = score_val
        self.shoot_timer = random.uniform(1.0, 2.5)
        self.parts = []
        game.enemies.append(self)

    def take_damage(self, amount, attacker=None):
        if not self.alive:
            return
        self.hp -= amount
        FloatingText(f"-{amount}", self.world_position, clr=color.hex('#ffbe0b'))
        play_sfx('hit.wav', vol=0.6, pitch=1.1)

        # Flash on hit
        for p in self.parts:
            if hasattr(p, 'orig_color'):
                p.color = color.white
                invoke(setattr, p, 'color', p.orig_color, delay=0.07)

        if self.hp <= 0:
            self.die()

    def die(self):
        self.alive = False
        spawn_explosion_fx(self.world_position, clr=color.hex('#e63946'), count=18)
        play_sfx('explode.wav', vol=0.75)

        # Score & Combo streak
        game.add_score(self.score_val)
        FloatingText(f"+{self.score_val}", self.world_position, clr=color.yellow, scale_mult=1.3)

        # 25% chance to drop a power-up
        if random.random() < 0.28:
            ptype = random.choice(['TRI_SHOT', 'HYPER_BOUNCE', 'RAPID_FIRE', 'SHIELD', 'HEALTH'])
            PowerUp(self.world_position, ptype)

        if self in game.enemies:
            game.enemies.remove(self)
        destroy(self)
        game.on_enemy_killed()


class DroneScout(EnemyBase):
    """
    Agile red hunter drone.
    Circles player at medium distance and fires bouncing plasma shells.
    """
    def __init__(self, position):
        super().__init__(position=position, hp=45, speed=6.8, score_val=200)

        # Chassis
        self.body = Entity(
            parent=self,
            model='cube',
            scale=(1.6, 0.45, 1.6),
            position=(0, 0.3, 0),
            color=color.hex('#b7094c'),
            collider='box'
        )
        self.body.damage_target = self
        self.body.orig_color = self.body.color
        self.parts.append(self.body)

        # Glowing red central eye
        self.eye = Entity(
            parent=self,
            model='sphere',
            scale=0.55,
            position=(0, 0.45, 0.65),
            color=color.hex('#ff0a54'),
            unlit=True
        )
        self.parts.append(self.eye)

        # Cannon
        self.cannon = Entity(
            parent=self,
            model='cylinder',
            scale=(0.2, 0.8, 0.2),
            position=(0, 0.35, 0.95),
            rotation=(90, 0, 0),
            color=color.hex('#5c0029')
        )
        self.parts.append(self.cannon)

    def update(self):
        if not self.alive or not game.player or not game.player.alive:
            return

        dt = time.dt
        to_player = game.player.world_position - self.world_position
        dist = to_player.length()

        # Face toward player
        target_rot = math.degrees(math.atan2(to_player.x, to_player.z))
        self.rotation_y = lerp_angle(self.rotation_y, target_rot, dt * 6.0)

        # Maintain ideal engagement range (~8-11 units)
        move_vec = Vec3(0, 0, 0)
        if dist > 11.0:
            move_vec = to_player.normalized()
        elif dist < 7.0:
            move_vec = -to_player.normalized()
        else:
            # Strafe sideways around player
            strafe = Vec3(-to_player.z, 0, to_player.x).normalized()
            move_vec = strafe

        # Simple obstacle avoidance raycast
        fwd_hit = raycast(self.world_position + Vec3(0, 0.5, 0), move_vec, distance=2.2, ignore=[self, self.body])
        if fwd_hit.hit:
            move_vec = Vec3(-move_vec.z, 0, move_vec.x)  # Turn 90 degrees

        new_pos = self.position + move_vec * (self.speed * dt)
        new_pos.x = max(-14.5, min(14.5, new_pos.x))
        new_pos.z = max(-11.0, min(11.0, new_pos.z))
        self.position = new_pos

        # Shooting logic
        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot_timer = random.uniform(2.0, 3.2)
            self.fire()

    def fire(self):
        if not self.alive:
            return
        play_sfx('shoot.wav', vol=0.5, pitch=1.2)
        fwd = self.forward
        muzzle = self.world_position + fwd * 1.4 + Vec3(0, 0.35, 0)
        RicochetBullet(muzzle, fwd, speed=26.0, max_bounces=2, owner=self, damage=22, clr=color.hex('#ff0a54'))


class TurretSentry(EnemyBase):
    """
    Stationary amber tripod turret.
    Sweeps a 360-degree detection beam; locks on and fires 2-round bursts!
    """
    def __init__(self, position):
        super().__init__(position=position, hp=60, speed=0.0, score_val=250)

        # Sturdy stationary base
        self.base_ent = Entity(
            parent=self,
            model='cylinder',
            scale=(1.8, 0.5, 1.8),
            position=(0, 0.25, 0),
            color=color.hex('#4a4e69'),
            collider='box'
        )
        self.base_ent.damage_target = self
        self.base_ent.orig_color = self.base_ent.color
        self.parts.append(self.base_ent)

        # Rotating dome head
        self.dome = Entity(
            parent=self,
            model='sphere',
            scale=(1.2, 0.7, 1.2),
            position=(0, 0.65, 0),
            color=color.hex('#ffb703')
        )
        self.dome.orig_color = self.dome.color
        self.parts.append(self.dome)

        # Dual twin guns
        self.guns = []
        for x_off in (-0.32, 0.32):
            g = Entity(
                parent=self.dome,
                model='cylinder',
                scale=(0.16, 1.0, 0.16),
                position=(x_off, 0.05, 0.7),
                rotation=(90, 0, 0),
                color=color.hex('#22223b')
            )
            self.parts.append(g)
            self.guns.append(g)

        self.burst_count = 0
        self.burst_cooldown = 0.0

    def update(self):
        if not self.alive or not game.player or not game.player.alive:
            return

        dt = time.dt
        to_player = game.player.world_position - self.world_position
        dist = to_player.length()

        # Check line of sight
        los_hit = raycast(
            self.world_position + Vec3(0, 0.7, 0),
            to_player.normalized(),
            distance=dist + 0.2,
            ignore=[self, self.base_ent]
        )

        can_see = los_hit.hit and (los_hit.entity == game.player or los_hit.entity in getattr(game.player, 'parts', []))

        if can_see and dist < 22.0:
            # Lock onto player
            target_rot = math.degrees(math.atan2(to_player.x, to_player.z))
            self.dome.rotation_y = lerp_angle(self.dome.rotation_y, target_rot, dt * 7.0)

            self.shoot_timer -= dt
            if self.shoot_timer <= 0:
                self.shoot_timer = 2.6
                self.burst_count = 2
                self.burst_cooldown = 0.0
        else:
            # Idle radar scan
            self.dome.rotation_y += 45 * dt

        # Handle 2-round burst
        if self.burst_count > 0:
            self.burst_cooldown -= dt
            if self.burst_cooldown <= 0:
                self.burst_cooldown = 0.16
                self.burst_count -= 1
                self.fire_single()

    def fire_single(self):
        play_sfx('shoot.wav', vol=0.55, pitch=1.1)
        gun_ent = self.guns[self.burst_count % 2]
        muzzle = gun_ent.world_position + self.dome.forward * 0.4
        RicochetBullet(muzzle, self.dome.forward, speed=30.0, max_bounces=2, owner=self, damage=20, clr=color.hex('#ffb703'))


class GoliathTank(EnemyBase):
    """
    Massive purple boss tank.
    High armor, fires alternating twin heavy cannons and spawns explosive clusters!
    """
    def __init__(self, position):
        super().__init__(position=position, hp=150, speed=3.6, score_val=600)

        # Huge armored chassis
        self.chassis = Entity(
            parent=self,
            model='cube',
            scale=(2.6, 0.8, 3.0),
            position=(0, 0.45, 0),
            color=color.hex('#3c096c'),
            collider='box'
        )
        self.chassis.damage_target = self
        self.chassis.orig_color = self.chassis.color
        self.parts.append(self.chassis)

        # Giant dual treads
        for side in (-1.4, 1.4):
            t = Entity(
                parent=self,
                model='cube',
                scale=(0.5, 0.7, 3.2),
                position=(side, 0.4, 0),
                color=color.hex('#10002b')
            )
            self.parts.append(t)

        # Heavy turret dome
        self.turret = Entity(
            parent=self,
            model='sphere',
            scale=(1.6, 0.9, 1.6),
            position=(0, 0.9, 0),
            color=color.hex('#5a189a')
        )
        self.turret.orig_color = self.turret.color
        self.parts.append(self.turret)

        # Heavy twin barrels
        self.barrels = []
        for x_off in (-0.5, 0.5):
            b = Entity(
                parent=self.turret,
                model='cylinder',
                scale=(0.3, 1.8, 0.3),
                position=(x_off, 0.15, 1.2),
                rotation=(90, 0, 0),
                color=color.hex('#7b2cbf')
            )
            self.parts.append(b)
            self.barrels.append(b)

    def update(self):
        if not self.alive or not game.player or not game.player.alive:
            return

        dt = time.dt
        to_player = game.player.world_position - self.world_position
        dist = to_player.length()

        # Steer chassis toward player
        target_rot = math.degrees(math.atan2(to_player.x, to_player.z))
        self.rotation_y = lerp_angle(self.rotation_y, target_rot, dt * 2.8)
        self.turret.rotation_y = lerp_angle(self.turret.rotation_y, target_rot, dt * 5.0)

        # Move steadily forward
        if dist > 6.0:
            new_pos = self.position + self.forward * (self.speed * dt)
            new_pos.x = max(-14.0, min(14.0, new_pos.x))
            new_pos.z = max(-10.5, min(10.5, new_pos.z))
            self.position = new_pos

        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot_timer = 2.4
            self.fire_barrage()

    def fire_barrage(self):
        play_sfx('shoot.wav', vol=0.8, pitch=0.75)
        camera_shake.add(0.18)
        for b in self.barrels:
            muzzle = b.world_position + self.turret.forward * 0.4
            RicochetBullet(muzzle, self.turret.forward, speed=26.0, max_bounces=3, owner=self, damage=30, clr=color.hex('#9d4edd'))


# =============================================================================
#  ARENA GENERATION
# =============================================================================
class Arena:
    """Creates the futuristic cyber neon arena and border barriers."""
    def __init__(self):
        self.entities = []

        # Ground Platform with Grid Look
        self.floor = Entity(
            model='plane',
            scale=(32, 1, 24),
            position=(0, 0, 0),
            color=color.hex('#0a0f1d'),
            collider='box'
        )
        self.entities.append(self.floor)

        # Glowing Floor Grid Lines
        for x in range(-15, 16, 3):
            line = Entity(
                model='cube',
                scale=(0.04, 0.02, 24),
                position=(x, 0.02, 0),
                color=color.rgba(0, 240, 255, 0.12),
                unlit=True
            )
            self.entities.append(line)

        for z in range(-11, 12, 3):
            line = Entity(
                model='cube',
                scale=(32, 0.02, 0.04),
                position=(0, 0.02, z),
                color=color.rgba(0, 240, 255, 0.12),
                unlit=True
            )
            self.entities.append(line)

        # Perimeter Reflective Neon Walls
        wall_data = [
            # ((x, y, z), (scale_x, scale_y, scale_z))
            ((0, 1.2, 12.0), (32.4, 2.4, 0.8)),   # North
            ((0, 1.2, -12.0), (32.4, 2.4, 0.8)),  # South
            ((16.0, 1.2, 0), (0.8, 2.4, 24.4)),   # East
            ((-16.0, 1.2, 0), (0.8, 2.4, 24.4)),  # West
        ]

        for pos, sc in wall_data:
            wall = Entity(
                model='cube',
                position=pos,
                scale=sc,
                color=color.hex('#101826'),
                collider='box'
            )
            wall.is_wall = True
            wall.is_reflective = True
            self.entities.append(wall)

            # Glowing neon rim along wall top
            rim = Entity(
                parent=wall,
                model='cube',
                position=(0, 0.48, 0),
                scale=(1.01, 0.08, 1.01),
                color=color.hex('#00f0ff'),
                unlit=True
            )
            self.entities.append(rim)

        # Reflective Corner Pillars
        pillar_positions = [(-11, 0, 7), (11, 0, 7), (-11, 0, -7), (11, 0, -7)]
        for p in pillar_positions:
            pillar = Entity(
                model='cube',
                position=Vec3(*p) + Vec3(0, 1.5, 0),
                scale=(2.2, 3.0, 2.2),
                color=color.hex('#162238'),
                collider='box'
            )
            pillar.is_wall = True
            pillar.is_reflective = True
            self.entities.append(pillar)

            trim = Entity(
                parent=pillar,
                model='cube',
                scale=(1.05, 0.15, 1.05),
                position=(0, 0.45, 0),
                color=color.hex('#ffe600'),
                unlit=True
            )
            self.entities.append(trim)

        # Central Tactical Barriers (Angle blocks for rich ricochets)
        barrier_data = [
            ((-4, 1.0, 2), (3.5, 2.0, 1.2)),
            ((4, 1.0, -2), (3.5, 2.0, 1.2)),
        ]
        for pos, sc in barrier_data:
            b = Entity(
                model='cube',
                position=pos,
                scale=sc,
                color=color.hex('#1f2d42'),
                collider='box'
            )
            b.is_wall = True
            b.is_reflective = True
            self.entities.append(b)

            b_rim = Entity(
                parent=b,
                model='cube',
                scale=(1.03, 0.1, 1.03),
                position=(0, 0.46, 0),
                color=color.hex('#00ffff'),
                unlit=True
            )
            self.entities.append(b_rim)


# =============================================================================
#  GAME DIRECTOR & HUD MANAGER
# =============================================================================
class GameDirector:
    """Manages wave spawning, score, HUD UI, player lifecycle, and game state."""
    def __init__(self):
        self.score = 0
        self.wave = 1
        self.combo = 0
        self.combo_timer = 0.0
        self.state = 'PLAYING'  # PLAYING, GAMEOVER, PAUSED

        self.player = None
        self.arena = None
        self.bullets = []
        self.enemies = []
        self.destructibles = []
        self.powerups = []

        self.init_hud()
        self.start_game()

    def init_hud(self):
        """Builds clean high-contrast cyberpunk HUD elements."""
        # Top-Left: Health Bar
        self.hp_bg = Entity(
            parent=camera.ui,
            model='quad',
            scale=(0.32, 0.03),
            position=(-0.68, 0.44),
            color=color.hex('#1b263b'),
            origin=(-0.5, 0)
        )
        self.hp_bar = Entity(
            parent=camera.ui,
            model='quad',
            scale=(0.32, 0.03),
            position=(-0.68, 0.44),
            color=color.hex('#00f0ff'),
            origin=(-0.5, 0)
        )
        self.hp_label = Text(
            text='HULL INTEGRITY',
            parent=camera.ui,
            scale=0.85,
            position=(-0.68, 0.475),
            color=color.hex('#8ecae6')
        )

        # Dash Cooldown Indicator
        self.dash_bar = Entity(
            parent=camera.ui,
            model='quad',
            scale=(0.32, 0.012),
            position=(-0.68, 0.415),
            color=color.hex('#ffe600'),
            origin=(-0.5, 0)
        )
        self.dash_label = Text(
            text='THRUSTERS: READY',
            parent=camera.ui,
            scale=0.7,
            position=(-0.68, 0.395),
            color=color.hex('#ffbe0b')
        )

        # Top-Center: Wave Announcement
        self.wave_text = Text(
            text='WAVE 1',
            parent=camera.ui,
            scale=1.5,
            origin=(0, 0),
            position=(0, 0.44),
            color=color.white
        )

        # Top-Right: Score & Combo
        self.score_text = Text(
            text='SCORE: 000,000',
            parent=camera.ui,
            scale=1.3,
            origin=(0.5, 0),
            position=(0.82, 0.44),
            color=color.hex('#00f0ff')
        )
        self.combo_text = Text(
            text='',
            parent=camera.ui,
            scale=1.1,
            origin=(0.5, 0),
            position=(0.82, 0.395),
            color=color.hex('#ffbe0b')
        )

        # Wave Banner overlay (for dramatic start of waves)
        self.banner = Text(
            text='',
            parent=camera.ui,
            scale=2.4,
            origin=(0, 0),
            position=(0, 0.1),
            color=color.yellow,
            enabled=False
        )

        # Game Over / Win Screen Panel
        self.game_over_panel = Entity(
            parent=camera.ui,
            model='quad',
            scale=(0.75, 0.65),
            position=(0, 0),
            color=color.rgba(10, 15, 29, 0.94),
            enabled=False
        )
        self.go_title = Text(
            text='SYSTEM COMPROMISED',
            parent=self.game_over_panel,
            scale=2.0,
            origin=(0, 0),
            position=(0, 0.28),
            color=color.red
        )
        self.go_score = Text(
            text='',
            parent=self.game_over_panel,
            scale=1.4,
            origin=(0, 0),
            position=(0, 0.08),
            color=color.white
        )
        self.go_wave = Text(
            text='',
            parent=self.game_over_panel,
            scale=1.2,
            origin=(0, 0),
            position=(0, -0.04),
            color=color.hex('#8ecae6')
        )
        self.go_prompt = Text(
            text='PRESS [R] TO RESTART',
            parent=self.game_over_panel,
            scale=1.3,
            origin=(0, 0),
            position=(0, -0.22),
            color=color.yellow
        )

    def start_game(self):
        """Clears existing state and begins a fresh game run."""
        self.state = 'PLAYING'
        self.score = 0
        self.wave = 1
        self.combo = 0
        self.combo_timer = 0.0
        self.game_over_panel.enabled = False

        # Clear active entities
        for b in self.bullets[:]:
            destroy(b)
        self.bullets.clear()

        for e in self.enemies[:]:
            destroy(e)
        self.enemies.clear()

        for d in self.destructibles[:]:
            destroy(d)
        self.destructibles.clear()

        for p in self.powerups[:]:
            destroy(p)
        self.powerups.clear()

        if self.player:
            self.player.destroy_self()

        if not self.arena:
            self.arena = Arena()

        # Spawn Player
        self.player = PlayerTank(position=Vec3(0, 0, -8))

        self.spawn_wave(self.wave)
        self.update_hud()

    def spawn_wave(self, wave_num):
        """Spawns wave-specific enemies, obstacles, and plays fanfare."""
        self.wave = wave_num
        self.wave_text.text = f'WAVE {self.wave}'

        # Clear remaining destructibles & spawn fresh layout
        for d in self.destructibles[:]:
            destroy(d)
        self.destructibles.clear()

        # Spawn Crates & Barrels in tactical pockets
        crate_spots = [(-7, 0, 4), (7, 0, 4), (-7, 0, -4), (7, 0, -4), (0, 0, 5), (0, 0, -5)]
        for pos in crate_spots:
            SupplyCrate(Vec3(*pos))

        barrel_spots = [(-11, 0, 0), (11, 0, 0), (0, 0, 8)]
        for pos in barrel_spots:
            ExplosiveBarrel(Vec3(*pos))

        # Show Dramatic Wave Banner
        titles = {
            1: "WAVE 1: BOOT SEQUENCE",
            2: "WAVE 2: REINFORCEMENTS",
            3: "WAVE 3: GOLIATH PROTOCOL",
            4: "WAVE 4: CROSSFIRE GRID",
            5: "WAVE 5: FINAL SURGE"
        }
        banner_msg = titles.get(self.wave, f"WAVE {self.wave}: OVERDRIVE")
        self.banner.text = banner_msg
        self.banner.enabled = True
        self.banner.scale = 2.4
        self.banner.animate_scale(1.8, duration=0.4, curve=curve.out_expo)
        invoke(setattr, self.banner, 'enabled', False, delay=1.8)

        play_sfx('wave_clear.wav', vol=0.7)

        # Enemy composition per wave
        enemy_spawns = []
        if self.wave == 1:
            enemy_spawns = [
                ('DRONE', Vec3(-6, 0, 7)),
                ('DRONE', Vec3(6, 0, 7)),
                ('DRONE', Vec3(0, 0, 9))
            ]
        elif self.wave == 2:
            enemy_spawns = [
                ('TURRET', Vec3(-9, 0, 7)),
                ('TURRET', Vec3(9, 0, 7)),
                ('DRONE', Vec3(-4, 0, 8)),
                ('DRONE', Vec3(4, 0, 8))
            ]
        elif self.wave == 3:
            enemy_spawns = [
                ('GOLIATH', Vec3(0, 0, 8)),
                ('DRONE', Vec3(-8, 0, 6)),
                ('DRONE', Vec3(8, 0, 6))
            ]
        elif self.wave == 4:
            enemy_spawns = [
                ('TURRET', Vec3(-8, 0, 8)),
                ('TURRET', Vec3(8, 0, 8)),
                ('DRONE', Vec3(-5, 0, 5)),
                ('DRONE', Vec3(5, 0, 5)),
                ('DRONE', Vec3(0, 0, 9))
            ]
        else:
            # Wave 5+ (escalating boss waves)
            enemy_spawns = [
                ('GOLIATH', Vec3(-5, 0, 8)),
                ('GOLIATH', Vec3(5, 0, 8)),
                ('TURRET', Vec3(0, 0, 9)),
                ('DRONE', Vec3(-9, 0, 4)),
                ('DRONE', Vec3(9, 0, 4))
            ]

        for etype, pos in enemy_spawns:
            # Spawn cyber portal effect before enemy appears
            self.spawn_enemy_with_teleport(etype, pos)

    def spawn_enemy_with_teleport(self, etype, pos):
        """Materializes an enemy with a stylish cyber spawn ring."""
        ring = Entity(
            model='cylinder',
            position=pos + Vec3(0, 0.1, 0),
            scale=(2.5, 0.05, 2.5),
            color=color.hex('#ff0a54'),
            wireframe=True
        )
        ring.animate_scale((0.1, 0.05, 0.1), duration=0.6, curve=curve.in_quad)
        destroy(ring, delay=0.65)

        def materialize():
            if etype == 'DRONE':
                DroneScout(pos)
            elif etype == 'TURRET':
                TurretSentry(pos)
            elif etype == 'GOLIATH':
                GoliathTank(pos)

        invoke(materialize, delay=0.6)

    def add_score(self, amount):
        self.combo += 1
        self.combo_timer = 3.5
        combo_mult = min(5, 1 + self.combo // 2)
        added = amount * combo_mult
        self.score += added
        self.update_hud()

    def on_enemy_killed(self):
        # Check if wave is cleared
        if len(self.enemies) <= 1:  # Current dying enemy still counting down
            invoke(self.advance_wave, delay=1.5)

    def advance_wave(self):
        if self.state != 'PLAYING':
            return
        self.score += 500 * self.wave
        self.spawn_wave(self.wave + 1)
        self.update_hud()

    def on_player_death(self):
        self.state = 'GAMEOVER'
        self.game_over_panel.enabled = True
        self.go_score.text = f'FINAL SCORE: {self.score:,}'
        self.go_wave.text = f'WAVES CLEARED: {self.wave - 1}'

    def update_hud(self):
        if not self.player or not self.player.alive:
            self.hp_bar.scale_x = 0
            return

        # Smooth health bar
        hp_frac = max(0.0, self.player.hp / self.player.max_hp)
        self.hp_bar.scale_x = 0.32 * hp_frac
        if hp_frac > 0.5:
            self.hp_bar.color = color.hex('#00f0ff')
        elif hp_frac > 0.25:
            self.hp_bar.color = color.hex('#ffbe0b')
        else:
            self.hp_bar.color = color.hex('#ff0055')

        # Score display with formatted comma digits
        self.score_text.text = f'SCORE: {self.score:07d}'

    def update(self):
        dt = time.dt
        # Combo decay timer
        if self.combo > 0:
            self.combo_timer -= dt
            self.combo_text.text = f'COMBO x{min(5, 1 + self.combo // 2)}  [{self.combo_timer:.1f}s]'
            if self.combo_timer <= 0:
                self.combo = 0
                self.combo_text.text = ''

        # Dash Cooldown HUD
        if self.player and self.player.alive:
            if self.player.dash_cooldown > 0:
                frac = 1.0 - (self.player.dash_cooldown / 1.6)
                self.dash_bar.scale_x = 0.32 * max(0.01, frac)
                self.dash_bar.color = color.hex('#555555')
                self.dash_label.text = 'THRUSTERS: CHARGING...'
                self.dash_label.color = color.hex('#777777')
            else:
                self.dash_bar.scale_x = 0.32
                self.dash_bar.color = color.hex('#ffe600')
                self.dash_label.text = 'THRUSTERS: READY [RMB/SHIFT]'
                self.dash_label.color = color.hex('#ffbe0b')


# Instantiate Game Director
game = GameDirector()


# =============================================================================
#  INPUT DISPATCHER & MAIN LOOP
# =============================================================================
def input(key):
    if key == 'r':
        # Instant Restart
        game.start_game()
        return

    if key == 'escape':
        # Quit application
        application.quit()
        return

    if game.state != 'PLAYING' or not game.player or not game.player.alive:
        return

    # Trigger Thruster Dash
    if key in ('right mouse down', 'left shift', 'right shift'):
        game.player.trigger_dash()


def update():
    camera_shake.update()
    game.update()


# =============================================================================
#  ENTRY POINT
# =============================================================================
if __name__ == '__main__':
    app.run()
