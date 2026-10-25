"""
=============================================================================
   ZOMBIE SURVIVAL: NIGHTFALL OUTPOST  --  3D Survival FPS in Ursina Engine
=============================================================================
Features & Improvements:
  - 3 Arsenal Weapons: Assault Rifle (balanced), Shotgun (pellet spread), SMG (rapid fire)
  - Zombie Variety: Walkers (standard), Runners (fast/agile), Brutes (heavy tank with high HP)
  - Headshot Mechanic: Dedicated head hitbox granting 2.5x critical damage & sound
  - Wave Progression System: Increasing difficulty, enemy count, and wave clear bonuses
  - Dynamic World: Foggy nocturnal atmosphere, ambient lanterns, perimeter security walls
  - Tactical Explosive Barrels: Shootable barrels with area-of-effect chain explosions
  - Supply Drops: Health kits (+35 HP) and Ammo crates dropped by fallen zombies
  - Damage Vignette & Screen Shake: Reactive HUD feedback on damage and shooting
  - Procedural Sound Effects & Tension BGM: 15 full game sound cues via OpenAL
=============================================================================
"""

import os
import random
import math
from pathlib import Path
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

# ==========================================
# AUDIO MANAGER
# ==========================================
class AudioManager:
    """Handles sound effects and music with safe fallbacks and Panda3D Path compatibility."""
    def __init__(self):
        self.audio_dir = Path(__file__).resolve().parent / "assets" / "audio"
        self.bgm = None
        self.play_bgm()

    def play_sound(self, filename, volume=1.0, pitch=1.0):
        filepath = self.audio_dir / filename
        if filepath.exists():
            try:
                # Passing pathlib.Path triggers Panda3D OpenAL audio binding
                Audio(filepath, volume=volume, pitch=pitch, autoplay=True, auto_destroy=True)
            except Exception:
                pass

    def play_bgm(self):
        for candidate in ("bgm.wav", "bgm.ogg"):
            filepath = self.audio_dir / candidate
            if filepath.exists():
                try:
                    self.bgm = Audio(filepath, volume=0.35, loop=True, autoplay=True)
                    break
                except Exception:
                    pass

    def stop_bgm(self):
        if self.bgm:
            try:
                self.bgm.stop()
            except Exception:
                pass

audio_manager = None

# ==========================================
# VISUAL EFFECTS (VFX)
# ==========================================
class Particle(Entity):
    """Temporary physics particle for bullet impacts and explosions."""
    def __init__(self, position, color=color.orange, speed=4.0, lifetime=0.45, scale=0.12):
        super().__init__(
            model='cube',
            color=color,
            scale=scale,
            position=position,
            collider=None
        )
        self.velocity = Vec3(
            random.uniform(-speed, speed),
            random.uniform(0.5, speed * 1.5),
            random.uniform(-speed, speed)
        )
        self.lifetime = lifetime
        destroy(self, delay=self.lifetime)

    def update(self):
        self.position += self.velocity * time.dt
        self.velocity.y -= 9.8 * time.dt
        self.scale *= max(0.01, 1 - (time.dt * 2.2))

class MuzzleFlash(Entity):
    def __init__(self, parent_gun):
        super().__init__(
            parent=parent_gun,
            model='quad',
            texture='circle',
            color=color.yellow,
            scale=0.15,
            position=Vec3(0, 0, 1.25),
            double_sided=True,
            billboard=True,
            enabled=False
        )

    def flash(self):
        self.enabled = True
        self.rotation_z = random.randint(0, 360)
        invoke(setattr, self, 'enabled', False, delay=0.05)

# ==========================================
# PICKUPS & INTERACTIVES
# ==========================================
class Pickup(Entity):
    """Floating collectible dropped by zombies."""
    def __init__(self, position, pickup_type='ammo'):
        self.pickup_type = pickup_type
        cube_col = color.azure if pickup_type == 'ammo' else color.emerald
        super().__init__(
            model='cube',
            color=cube_col,
            scale=(0.4, 0.4, 0.4),
            position=position + Vec3(0, 0.5, 0),
            collider='box'
        )
        self.base_y = self.y
        self.lifetime = 25.0
        destroy(self, delay=self.lifetime)

    def update(self):
        self.rotation_y += 90 * time.dt
        self.y = self.base_y + math.sin(time.time() * 3.5) * 0.15
        if player and player.health > 0:
            if distance(self.position, player.position) < 1.8:
                self.collect()

    def collect(self):
        if self.pickup_type == 'ammo':
            player.add_ammo(25)
            player.show_hud_alert("+25 AMMO RESERVES", color.cyan)
        else:
            player.heal(35)
            player.show_hud_alert("+35 HEALTH RESTORED", color.green)
        audio_manager.play_sound('pickup.wav', volume=0.85)
        destroy(self)

class ExplosiveBarrel(Entity):
    """Red barrel that detonates when shot, damaging nearby enemies and player."""
    def __init__(self, position):
        super().__init__(
            model='cylinder',
            color=color.hex('#D32F2F'),
            scale=(1.1, 1.8, 1.1),
            position=position,
            collider='box'
        )
        self.health = 20
        self.exploded = False

    def take_damage(self, amount, is_headshot=False):
        if self.exploded:
            return
        self.health -= amount
        self.color = color.white
        invoke(setattr, self, 'color', color.hex('#D32F2F'), delay=0.08)
        if self.health <= 0:
            self.explode()

    def explode(self):
        if self.exploded:
            return
        self.exploded = True
        audio_manager.play_sound('explosion.wav', volume=1.2)
        
        # Explosion particles & visual shockwave
        for _ in range(25):
            Particle(self.position + Vec3(0, 1, 0), color=random.choice([color.red, color.orange, color.yellow]), speed=6.0, lifetime=0.6, scale=0.2)

        # Damage nearby entities
        radius = 8.5
        for enemy in list(spawn_manager.active_enemies):
            if enemy and hasattr(enemy, 'take_damage') and not enemy.is_dead:
                d = distance(self.position, enemy.position)
                if d <= radius:
                    dmg = int(120 * (1 - d / radius))
                    enemy.take_damage(dmg)

        if player and player.health > 0:
            pd = distance(self.position, player.position)
            if pd <= radius:
                p_dmg = int(45 * (1 - pd / radius))
                player.take_damage(p_dmg)

        destroy(self)

# ==========================================
# PLAYER CONTROLLER & WEAPONS
# ==========================================
class Player(FirstPersonController):
    def __init__(self):
        super().__init__()
        self.speed = 8
        self.sprint_speed = 13
        self.jump_height = 1.4
        self.max_health = 100
        self.health = self.max_health
        self.score = 0
        self.is_reloading = False
        self.last_shot = 0

        # Weapons Configuration
        self.weapons = {
            'rifle': {
                'name': 'ASSAULT RIFLE',
                'damage': 28,
                'fire_rate': 0.11,
                'max_clip': 30,
                'clip': 30,
                'reserves': 90,
                'pellets': 1,
                'spread': 0.015,
                'sound': 'shoot.wav',
                'gun_scale': (0.1, 0.18, 0.8),
                'gun_color': color.dark_gray
            },
            'shotgun': {
                'name': 'TACTICAL SHOTGUN',
                'damage': 18,
                'fire_rate': 0.65,
                'max_clip': 8,
                'clip': 8,
                'reserves': 32,
                'pellets': 6,
                'spread': 0.065,
                'sound': 'shotgun.wav',
                'gun_scale': (0.14, 0.22, 0.7),
                'gun_color': color.hex('#37474F')
            },
            'smg': {
                'name': 'RAPID SMG',
                'damage': 16,
                'fire_rate': 0.065,
                'max_clip': 45,
                'clip': 45,
                'reserves': 135,
                'pellets': 1,
                'spread': 0.035,
                'sound': 'smg.wav',
                'gun_scale': (0.09, 0.16, 0.6),
                'gun_color': color.hex('#263238')
            }
        }
        self.weapon_order = ['rifle', 'shotgun', 'smg']
        self.current_weapon_idx = 0
        self.current_weapon = self.weapon_order[self.current_weapon_idx]

        # Weapon Viewmodel
        self.gun = Entity(
            parent=camera,
            model='cube',
            color=color.dark_gray,
            origin_y=-0.5,
            scale=(0.1, 0.18, 0.8),
            position=Vec3(0.5, -0.4, 0.8),
            collider=None
        )
        self.gun_default_pos = self.gun.position
        self.muzzle_flash = MuzzleFlash(self.gun)

        # Full-Screen Damage Vignette
        self.damage_overlay = Entity(
            parent=camera.ui,
            model='quad',
            scale=(2, 2),
            color=color.rgba(255, 0, 0, 0),
            z=-0.05
        )

        # UI Overlay Elements
        self.crosshair = Entity(parent=camera.ui, model='quad', texture='circle', color=color.rgba(0, 255, 120, 180), scale=0.015)
        
        # Ammo HUD (bottom-right)
        self.weapon_name_text = Text(text='', position=(0.58, -0.34), origin=(0.5, 0), scale=1.4, color=color.gold)
        self.ammo_text = Text(text='', position=(0.58, -0.40), origin=(0.5, 0), scale=2.0)
        
        # Health HUD (bottom-left)
        self.health_bar_bg = Entity(parent=camera.ui, model='quad', color=color.dark_gray, scale=(0.42, 0.04), position=(-0.6, -0.4), origin=(-0.5, 0))
        self.health_bar = Entity(parent=camera.ui, model='quad', color=color.red, scale=(0.4, 0.03), position=(-0.59, -0.4), origin=(-0.5, 0))
        self.health_text = Text(text=f'HP: {self.health}', position=(-0.59, -0.34), scale=1.4, color=color.white)

        # Wave & Score HUD (top-left)
        self.wave_text = Text(text='WAVE 1', position=(-0.82, 0.45), scale=2.4, color=color.yellow)
        self.score_text = Text(text='KILLS: 0', position=(-0.82, 0.39), scale=1.6, color=color.light_gray)
        self.enemies_left_text = Text(text='ENEMIES: 0', position=(-0.82, 0.34), scale=1.3, color=color.orange)

        # Center Alert Banner
        self.alert_text = Text(text='', position=(0, 0.25), origin=(0, 0), scale=2.0, color=color.yellow)
        self.alert_timer = 0

        self.update_ui()

    def update(self):
        super().update()
        if self.health <= 0:
            return

        # Sprinting
        if held_keys['shift']:
            self.speed = self.sprint_speed
        else:
            self.speed = 8

        # Gun Bobbing & Sway
        target_pos = self.gun_default_pos
        is_moving = held_keys['w'] or held_keys['a'] or held_keys['s'] or held_keys['d']
        if is_moving:
            bob = math.sin(time.time() * (self.speed * 1.4)) * 0.025
            target_pos += Vec3(0, bob, 0)
            self.crosshair.scale = lerp(self.crosshair.scale, Vec3(0.025, 0.025, 0.025), time.dt * 10)
        else:
            self.crosshair.scale = lerp(self.crosshair.scale, Vec3(0.015, 0.015, 0.015), time.dt * 10)

        self.gun.position = lerp(self.gun.position, target_pos, time.dt * 10)
        self.gun.rotation_x = lerp(self.gun.rotation_x, 0, time.dt * 10)

        # Alert fade timer
        if self.alert_timer > 0:
            self.alert_timer -= time.dt
            if self.alert_timer <= 0:
                self.alert_text.text = ''

        # Auto-fire for SMG and Rifle when left mouse is held
        w = self.weapons[self.current_weapon]
        if held_keys['left mouse'] and not self.is_reloading:
            if time.time() - self.last_shot >= w['fire_rate']:
                self.shoot()

    def input(self, key):
        super().input(key)
        if self.health <= 0:
            return

        if key == 'left mouse down' and not self.is_reloading:
            self.shoot()
        elif key == 'r' and not self.is_reloading:
            self.reload()
        elif key in ('1', '2', '3'):
            idx = int(key) - 1
            if idx < len(self.weapon_order) and idx != self.current_weapon_idx and not self.is_reloading:
                self.switch_weapon(idx)
        elif key in ('scroll up', 'q') and not self.is_reloading:
            next_idx = (self.current_weapon_idx + 1) % len(self.weapon_order)
            self.switch_weapon(next_idx)
        elif key in ('scroll down', 'e') and not self.is_reloading:
            prev_idx = (self.current_weapon_idx - 1) % len(self.weapon_order)
            self.switch_weapon(prev_idx)

    def switch_weapon(self, idx):
        self.current_weapon_idx = idx
        self.current_weapon = self.weapon_order[idx]
        w = self.weapons[self.current_weapon]
        self.gun.scale = w['gun_scale']
        self.gun.color = w['gun_color']
        audio_manager.play_sound('switch.wav', volume=0.8)
        self.update_ui()
        self.show_hud_alert(f"{w['name']} EQUIPPED", color.gold, duration=1.0)

    def shoot(self):
        w = self.weapons[self.current_weapon]
        if time.time() - self.last_shot < w['fire_rate']:
            return

        if w['clip'] <= 0:
            audio_manager.play_sound('empty.wav')
            self.last_shot = time.time()
            return

        self.last_shot = time.time()
        w['clip'] -= 1
        self.update_ui()

        # Audio & Recoil Kick
        audio_manager.play_sound(w['sound'], pitch=random.uniform(0.95, 1.05))
        self.muzzle_flash.flash()
        self.gun.rotation_x = -18
        self.gun.position += Vec3(0, 0, -0.12)

        # Pellet Raycasts
        pellet_count = w['pellets']
        spread = w['spread']

        for _ in range(pellet_count):
            aim_dir = camera.forward
            if spread > 0:
                aim_dir = (camera.forward +
                           camera.right * random.uniform(-spread, spread) +
                           camera.up * random.uniform(-spread, spread)).normalized()

            hit_info = raycast(camera.world_position, aim_dir, distance=120, ignore=(self, self.gun))
            if hit_info.hit:
                # Spawn Impact Particles
                Particle(hit_info.world_point, color=color.orange)

                # Check for Headshot Hitbox first
                hit_ent = hit_info.entity
                if hasattr(hit_ent, 'is_head') and hit_ent.is_head:
                    # Parent enemy takes critical 2.5x headshot damage
                    enemy = hit_ent.parent_enemy
                    if enemy and hasattr(enemy, 'take_damage'):
                        dmg = int(w['damage'] * 2.5)
                        enemy.take_damage(dmg, is_headshot=True)
                        audio_manager.play_sound('hit.wav', volume=0.9, pitch=1.4)
                elif hasattr(hit_ent, 'take_damage'):
                    hit_ent.take_damage(w['damage'])
                    audio_manager.play_sound('hit.wav', volume=0.55)

    def reload(self):
        w = self.weapons[self.current_weapon]
        if w['clip'] == w['max_clip'] or w['reserves'] <= 0:
            return

        self.is_reloading = True
        self.ammo_text.text = "RELOADING..."
        audio_manager.play_sound('reload.wav')

        # Gun reload twist animation
        self.gun.animate_rotation(Vec3(60, 20, -10), duration=0.3)
        invoke(self.finish_reload, delay=1.2)

    def finish_reload(self):
        w = self.weapons[self.current_weapon]
        needed = w['max_clip'] - w['clip']
        to_add = min(needed, w['reserves'])
        w['clip'] += to_add
        w['reserves'] -= to_add
        self.is_reloading = False
        self.gun.animate_rotation(Vec3(0, 0, 0), duration=0.2)
        self.update_ui()

    def add_ammo(self, amount):
        for w in self.weapons.values():
            w['reserves'] += amount
        self.update_ui()

    def heal(self, amount):
        self.health = min(self.max_health, self.health + amount)
        self.update_ui()

    def take_damage(self, amount):
        self.health -= amount
        audio_manager.play_sound('hurt.wav')
        
        # Red Vignette Damage Flash
        self.damage_overlay.color = color.rgba(255, 0, 0, 0.45)
        self.damage_overlay.animate_color(color.rgba(255, 0, 0, 0), duration=0.35)

        self.update_ui()
        if self.health <= 0:
            self.die()

    def add_score(self, amount=1):
        self.score += amount
        self.score_text.text = f'KILLS: {self.score}'

    def show_hud_alert(self, text, alert_color=color.yellow, duration=2.0):
        self.alert_text.text = text
        self.alert_text.color = alert_color
        self.alert_timer = duration

    def update_ui(self):
        w = self.weapons[self.current_weapon]
        self.weapon_name_text.text = w['name']
        self.ammo_text.text = f"{w['clip']} / {w['reserves']}"
        self.health_bar.scale_x = max(0.001, (self.health / self.max_health) * 0.4)
        self.health_text.text = f'HP: {max(0, self.health)}'

    def die(self):
        self.cursor.enabled = False
        self.crosshair.enabled = False
        self.gun.enabled = False
        if audio_manager:
            audio_manager.stop_bgm()
            audio_manager.play_sound('game_over.wav')
        
        Text(text='OUTPOST OVERRUN\n\nPress R to Restart', position=(0, 0.05), origin=(0, 0), scale=2.8, color=color.red)

# ==========================================
# ENEMY AI & VARIETIES
# ==========================================
class HeadCollider(Entity):
    """Critical hitbox located on top of the enemy model."""
    def __init__(self, parent_enemy):
        super().__init__(
            parent=parent_enemy,
            model='cube',
            color=color.rgba(255, 0, 0, 0),
            scale=(0.8, 0.5, 0.8),
            position=(0, 1.25, 0),
            collider='box'
        )
        self.is_head = True
        self.parent_enemy = parent_enemy

class Enemy(Entity):
    def __init__(self, position, target, enemy_type='walker'):
        self.enemy_type = enemy_type
        self.target = target
        self.is_dead = False
        self.last_attack = 0

        # Configuration by Type
        if enemy_type == 'runner':
            col = color.hex('#FF9800')
            body_scale = (0.8, 1.7, 0.8)
            self.health = 35
            self.speed = 5.2
            self.attack_dmg = 10
            self.attack_cooldown = 0.75
            self.attack_range = 1.9
        elif enemy_type == 'brute':
            col = color.hex('#2E7D32')
            body_scale = (1.6, 2.6, 1.6)
            self.health = 160
            self.speed = 2.1
            self.attack_dmg = 30
            self.attack_cooldown = 1.4
            self.attack_range = 2.5
        else:  # 'walker'
            col = color.hex('#4CAF50')
            body_scale = (1.0, 2.0, 1.0)
            self.health = 60
            self.speed = 3.3
            self.attack_dmg = 15
            self.attack_cooldown = 1.0
            self.attack_range = 2.0

        super().__init__(
            model='cube',
            color=col,
            scale=body_scale,
            position=position,
            collider='box'
        )
        self.default_color = self.color
        
        # Attach dedicated headshot hitbox
        self.head_hitbox = HeadCollider(self)

    def update(self):
        if self.is_dead or not self.target or self.target.health <= 0:
            return

        dist = distance(self.position, self.target.position)
        if dist > self.attack_range:
            # Chase player
            self.look_at_2d(self.target.position, 'y')
            self.position += self.forward * self.speed * time.dt
        else:
            # Attack player
            if time.time() - self.last_attack > self.attack_cooldown:
                self.target.take_damage(self.attack_dmg)
                audio_manager.play_sound('zombie_attack.wav', pitch=random.uniform(0.9, 1.1))
                self.last_attack = time.time()

    def take_damage(self, amount, is_headshot=False):
        if self.is_dead:
            return
        self.health -= amount

        # Visual hit flash
        self.color = color.white if is_headshot else color.red
        invoke(setattr, self, 'color', self.default_color, delay=0.1)

        # Floating headshot indicator
        if is_headshot:
            Text(text='CRIT!', position=self.position + Vec3(0, 2.2, 0), scale=1.5, color=color.yellow, duration=0.5)

        if self.health <= 0:
            self.die()

    def die(self):
        self.is_dead = True
        self.collider = None
        if self.head_hitbox:
            self.head_hitbox.collider = None

        self.target.add_score(1)
        audio_manager.play_sound('zombie_death.wav', pitch=0.8 if self.enemy_type == 'brute' else 1.0)

        # Drop pickup randomly
        rng = random.random()
        if rng < 0.28:
            Pickup(self.position, pickup_type='ammo')
        elif rng < 0.44:
            Pickup(self.position, pickup_type='health')

        # Ragdoll tumble
        self.animate_rotation(Vec3(90, random.uniform(-40, 40), 0), duration=0.3)
        self.animate_position(self.position + Vec3(0, -0.9, 0), duration=0.3)
        destroy(self, delay=1.2)
        spawn_manager.on_enemy_killed(self)

# ==========================================
# WAVE & SPAWN DIRECTOR
# ==========================================
class WaveDirector:
    """Controls dynamic waves, increasing horde sizes, and pacing."""
    def __init__(self, target_player):
        self.target = target_player
        self.current_wave = 1
        self.enemies_remaining_to_spawn = 0
        self.active_enemies = []
        self.wave_in_progress = False

        self.spawn_points = [
            Vec3(32, 1, 32), Vec3(-32, 1, 32),
            Vec3(32, 1, -32), Vec3(-32, 1, -32),
            Vec3(0, 1, 38), Vec3(0, 1, -38),
            Vec3(38, 1, 0), Vec3(-38, 1, 0)
        ]
        invoke(self.start_wave, delay=2.5)

    def start_wave(self):
        self.wave_in_progress = True
        self.enemies_remaining_to_spawn = 6 + (self.current_wave * 4)
        self.target.wave_text.text = f'WAVE {self.current_wave}'
        self.target.show_hud_alert(f"--- WAVE {self.current_wave} COMMENCING ---", color.yellow, duration=3.0)
        self.update_enemies_ui()
        invoke(self.spawn_tick, delay=1.0)

    def spawn_tick(self):
        if not self.wave_in_progress or self.target.health <= 0:
            return

        # Max 14 active at any time for balanced performance & intense pressure
        if self.enemies_remaining_to_spawn > 0 and len(self.active_enemies) < 14:
            # Enemy variety weighting scales with wave
            r = random.random()
            if self.current_wave >= 3 and r < 0.22:
                e_type = 'brute'
            elif self.current_wave >= 2 and r < 0.55:
                e_type = 'runner'
            else:
                e_type = 'walker'

            spawn_pos = random.choice(self.spawn_points) + Vec3(random.uniform(-4, 4), 0, random.uniform(-4, 4))
            enemy = Enemy(spawn_pos, self.target, enemy_type=e_type)
            self.active_enemies.append(enemy)
            self.enemies_remaining_to_spawn -= 1
            self.update_enemies_ui()

        # Reschedule next spawn check
        if self.enemies_remaining_to_spawn > 0:
            invoke(self.spawn_tick, delay=random.uniform(0.8, 1.8))

    def on_enemy_killed(self, enemy):
        if enemy in self.active_enemies:
            self.active_enemies.remove(enemy)
        self.update_enemies_ui()

        # Check wave completion
        if self.enemies_remaining_to_spawn <= 0 and len(self.active_enemies) == 0 and self.wave_in_progress:
            self.wave_in_progress = False
            self.on_wave_cleared()

    def on_wave_cleared(self):
        audio_manager.play_sound('wave_clear.wav', volume=1.0)
        self.target.show_hud_alert(f"WAVE {self.current_wave} CLEARED! RESUPPLYING...", color.green, duration=4.0)
        # Resupply bonus
        self.target.add_ammo(30)
        self.target.heal(25)
        self.current_wave += 1
        invoke(self.start_wave, delay=5.0)

    def update_enemies_ui(self):
        total_remaining = self.enemies_remaining_to_spawn + len(self.active_enemies)
        self.target.enemies_left_text.text = f'REMAINING: {total_remaining}'

# ==========================================
# GAME SETUP & MAP GENERATION
# ==========================================
def restart_game():
    application.quit()
    os.system("python " + sys.argv[0])

def input(key):
    if key == 'r' and hasattr(player, 'health') and player.health <= 0:
        restart_game()

if __name__ == '__main__':
    app = Ursina(title='Zombie Survival: Nightfall Outpost', borderless=False)

    # Nocturnal Atmosphere & Fog
    Sky(color=color.hex('#0D1117'))
    scene.fog_color = color.hex('#0D1B2A')
    scene.fog_density = (20, 75)

    # Moody Outpost Lighting
    sun = DirectionalLight()
    sun.look_at(Vec3(1, -2, -1))
    sun.color = color.rgba(80, 100, 140, 255)
    AmbientLight(color=color.rgba(40, 50, 70, 255))

    # Ground Outpost Terrain
    ground = Entity(model='plane', collider='box', scale=90, texture='grass', texture_scale=(16, 16), color=color.hex('#2E3B2F'))

    # Perimeter Defensive Security Walls
    wall_height = 5
    Entity(model='cube', collider='box', scale=(90, wall_height, 2), position=(0, wall_height/2, 45), color=color.hex('#1C2833'))
    Entity(model='cube', collider='box', scale=(90, wall_height, 2), position=(0, wall_height/2, -45), color=color.hex('#1C2833'))
    Entity(model='cube', collider='box', scale=(2, wall_height, 90), position=(45, wall_height/2, 0), color=color.hex('#1C2833'))
    Entity(model='cube', collider='box', scale=(2, wall_height, 90), position=(-45, wall_height/2, 0), color=color.hex('#1C2833'))

    # Tactical Obstacles, Bunkers & Sandbags
    random.seed(42)
    for _ in range(18):
        ox = random.choice([x for x in range(-35, 35) if abs(x) > 6])
        oz = random.choice([z for z in range(-35, 35) if abs(z) > 6])
        Entity(
            model='cube',
            collider='box',
            position=(ox, random.uniform(1.0, 2.5), oz),
            scale=(random.uniform(2.5, 5.0), random.uniform(2.0, 4.5), random.uniform(2.5, 5.0)),
            color=random.choice([color.hex('#3E2723'), color.hex('#424242'), color.hex('#546E7A')])
        )

    # Perimeter Warning Lanterns
    lamp_positions = [Vec3(25, 0, 25), Vec3(-25, 0, 25), Vec3(25, 0, -25), Vec3(-25, 0, -25)]
    for lp in lamp_positions:
        Entity(model='cylinder', scale=(0.3, 4, 0.3), position=lp + Vec3(0, 2, 0), color=color.black)
        Entity(model='sphere', scale=0.8, position=lp + Vec3(0, 4.2, 0), color=color.yellow, emissive=True)
        PointLight(position=lp + Vec3(0, 4.5, 0), color=color.rgba(255, 200, 100, 180), radius=15)

    # Tactical Explosive Barrels placed around outpost
    barrel_positions = [
        Vec3(12, 0.9, 14), Vec3(-14, 0.9, 12),
        Vec3(16, 0.9, -15), Vec3(-15, 0.9, -18),
        Vec3(0, 0.9, 22), Vec3(22, 0.9, 0), Vec3(-22, 0.9, 0)
    ]
    for bp in barrel_positions:
        ExplosiveBarrel(bp)

    # Initialize Managers & Core Game Loop
    audio_manager = AudioManager()
    player = Player()
    spawn_manager = WaveDirector(player)

    # Hide default OS mouse pointer
    mouse.visible = False

    app.run()