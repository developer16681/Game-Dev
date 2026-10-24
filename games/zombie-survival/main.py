import os
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random

# ==========================================
# AUDIO MANAGER
# ==========================================
class AudioManager:
    """Handles sound effects and music with safe fallbacks."""
    def __init__(self):
        self.audio_dir = "assets/audio/"
        # Start BGM if exists
        self.play_bgm()

    def play_sound(self, filename, volume=1.0, pitch=1.0):
        filepath = os.path.join(self.audio_dir, filename)
        if os.path.exists(filepath):
            Audio(filepath, volume=volume, pitch=pitch, autoplay=True)
        else:
            # Fallback procedural blip if file missing
            Audio(ursina.prefabs.ursfx.Step(), volume=volume * 0.2, pitch=pitch, autoplay=True)

    def play_bgm(self):
        filepath = os.path.join(self.audio_dir, "bgm.ogg")
        if os.path.exists(filepath):
            Audio(filepath, volume=0.3, loop=True, autoplay=True)

audio_manager = None

# ==========================================
# VISUAL EFFECTS (VFX)
# ==========================================
class Particle(Entity):
    """Temporary particle for bullet impacts."""
    def __init__(self, position, color=color.orange):
        super().__init__(
            model='cube',
            color=color,
            scale=0.1,
            position=position,
            collider=None
        )
        self.velocity = Vec3(random.uniform(-2, 2), random.uniform(1, 4), random.uniform(-2, 2))
        self.lifetime = 0.5
        destroy(self, delay=self.lifetime)

    def update(self):
        self.position += self.velocity * time.dt
        self.scale *= 1 - (time.dt * 2)

class MuzzleFlash(Entity):
    def __init__(self, parent_gun):
        super().__init__(
            parent=parent_gun,
            model='quad',
            texture='circle',
            color=color.yellow,
            scale=0.1,
            position=Vec3(0, 0, 1.2),
            double_sided=True,
            billboard=True,
            enabled=False
        )

    def flash(self):
        self.enabled = True
        self.rotation_z = random.randint(0, 360)
        invoke(setattr, self, 'enabled', False, delay=0.05)

# ==========================================
# PLAYER CONTROLLER & WEAPON
# ==========================================
class Player(FirstPersonController):
    def __init__(self):
        super().__init__()
        self.speed = 8
        self.sprint_speed = 14
        self.jump_height = 1.5
        self.max_health = 100
        self.health = self.max_health
        
        # Weapon stats
        self.max_ammo = 30
        self.ammo = self.max_ammo
        self.fire_rate = 0.1  # Seconds between shots
        self.last_shot = 0
        self.damage = 25
        self.is_reloading = False

        # Weapon Viewmodel
        self.gun = Entity(
            parent=camera,
            model='cube',
            color=color.dark_gray,
            origin_y=-0.5,
            scale=(0.1, 0.2, 0.8),
            position=Vec3(0.5, -0.4, 0.8),
            collider=None
        )
        self.gun_default_pos = self.gun.position
        self.muzzle_flash = MuzzleFlash(self.gun)

        # UI
        self.crosshair = Entity(parent=camera.ui, model='quad', texture='circle', color=color.rgba(0,255,0,150), scale=0.015)
        self.ammo_text = Text(text=f'AMMO: {self.ammo}/{self.max_ammo}', position=(0.6, -0.4), origin=(0.5, 0), scale=2)
        self.health_bar = Entity(parent=camera.ui, model='quad', color=color.red, scale=(0.4, 0.03), position=(-0.6, -0.4), origin=(-0.5, 0))
        self.score = 0
        self.score_text = Text(text=f'KILLS: {self.score}', position=(-0.8, 0.45), scale=2)

    def update(self):
        super().update()
        if self.health <= 0:
            return

        # Sprinting
        if held_keys['shift']:
            self.speed = self.sprint_speed
        else:
            self.speed = 8

        # Gun Sway & Recoil interpolation
        target_pos = self.gun_default_pos
        if held_keys['w'] or held_keys['a'] or held_keys['s'] or held_keys['d']:
            # Bobbing effect
            target_pos += Vec3(0, math.sin(time.time() * self.speed) * 0.02, 0)
            self.crosshair.scale = lerp(self.crosshair.scale, Vec3(0.03, 0.03, 0.03), time.dt * 10)
        else:
            self.crosshair.scale = lerp(self.crosshair.scale, Vec3(0.015, 0.015, 0.015), time.dt * 10)

        self.gun.position = lerp(self.gun.position, target_pos, time.dt * 10)
        self.gun.rotation_x = lerp(self.gun.rotation_x, 0, time.dt * 10)

    def input(self, key):
        super().input(key)
        if self.health <= 0:
            return

        if key == 'left mouse down' and not self.is_reloading:
            self.shoot()
        if key == 'r' and self.ammo < self.max_ammo and not self.is_reloading:
            self.reload()

    def shoot(self):
        if time.time() - self.last_shot < self.fire_rate:
            return

        if self.ammo <= 0:
            audio_manager.play_sound('empty.wav')
            return

        self.last_shot = time.time()
        self.ammo -= 1
        self.update_ui()
        
        # Audio & VFX
        audio_manager.play_sound('shoot.wav', pitch=random.uniform(0.9, 1.1))
        self.muzzle_flash.flash()
        self.gun.rotation_x = -15  # Recoil kick
        self.gun.position += Vec3(0, 0, -0.1)

        # Raycast Hitscan
        hit_info = raycast(camera.world_position, camera.forward, distance=100, ignore=(self, self.gun))
        if hit_info.hit:
            for _ in range(3):
                Particle(hit_info.world_point)
            
            if hasattr(hit_info.entity, 'take_damage'):
                hit_info.entity.take_damage(self.damage)
                audio_manager.play_sound('hit.wav', volume=0.5)

    def reload(self):
        self.is_reloading = True
        self.ammo_text.text = "RELOADING..."
        audio_manager.play_sound('reload.wav')
        
        # Animation
        self.gun.animate_rotation(Vec3(60, 0, 0), duration=0.3)
        invoke(self.finish_reload, delay=1.5)

    def finish_reload(self):
        self.ammo = self.max_ammo
        self.is_reloading = False
        self.gun.animate_rotation(Vec3(0, 0, 0), duration=0.2)
        self.update_ui()

    def take_damage(self, amount):
        self.health -= amount
        self.health_bar.scale_x = (self.health / self.max_health) * 0.4
        audio_manager.play_sound('hurt.wav')
        
        if self.health <= 0:
            self.die()

    def add_score(self):
        self.score += 1
        self.score_text.text = f'KILLS: {self.score}'

    def update_ui(self):
        self.ammo_text.text = f'AMMO: {self.ammo}/{self.max_ammo}'

    def die(self):
        self.cursor.enabled = False
        self.crosshair.enabled = False
        self.gun.enabled = False
        Text(text='GAME OVER\nPress R to Restart', position=(0,0), origin=(0,0), scale=3, color=color.red)

# ==========================================
# ENEMY AI
# ==========================================
class Enemy(Entity):
    def __init__(self, position, target):
        super().__init__(
            model='cube',
            color=color.green,
            scale=(1, 2, 1),
            position=position,
            collider='box'
        )
        self.target = target
        self.health = 50
        self.speed = 3
        self.attack_range = 2
        self.attack_cooldown = 1.0
        self.last_attack = 0
        self.is_dead = False
        self.default_color = self.color

    def update(self):
        if self.is_dead or self.target.health <= 0:
            return

        dist = distance(self.position, self.target.position)
        
        if dist > self.attack_range:
            # Chase logic
            self.look_at_2d(self.target.position, 'y')
            self.position += self.forward * self.speed * time.dt
        else:
            # Attack logic
            if time.time() - self.last_attack > self.attack_cooldown:
                self.target.take_damage(15)
                self.last_attack = time.time()

    def take_damage(self, amount):
        if self.is_dead: return
        self.health -= amount
        
        # Hit flash
        self.color = color.red
        invoke(setattr, self, 'color', self.default_color, delay=0.1)

        if self.health <= 0:
            self.die()

    def die(self):
        self.is_dead = True
        self.target.add_score()
        audio_manager.play_sound('zombie_death.wav')
        
        # Ragdoll / Death animation
        self.animate_rotation(Vec3(90, 0, 0), duration=0.3)
        self.animate_position(self.position + Vec3(0, -1, 0), duration=0.3)
        destroy(self, delay=1.0)
        spawn_manager.enemy_count -= 1

# ==========================================
# SPAWN MANAGER
# ==========================================
class SpawnManager:
    def __init__(self, target_player):
        self.target = target_player
        self.max_enemies = 10
        self.enemy_count = 0
        self.spawn_points = [
            Vec3(20, 1, 20), Vec3(-20, 1, 20),
            Vec3(20, 1, -20), Vec3(-20, 1, -20)
        ]
        invoke(self.spawn_loop, delay=2)

    def spawn_loop(self):
        if self.target.health > 0 and self.enemy_count < self.max_enemies:
            spawn_pos = random.choice(self.spawn_points) + Vec3(random.uniform(-5, 5), 0, random.uniform(-5, 5))
            Enemy(spawn_pos, self.target)
            self.enemy_count += 1
        
        # Continue loop
        invoke(self.spawn_loop, delay=random.uniform(1, 3))

# ==========================================
# GAME SETUP & LOOP
# ==========================================
def restart_game():
    application.quit()
    os.system("python " + sys.argv[0])

def input(key):
    # Global restart handle
    if key == 'r' and hasattr(player, 'health') and player.health <= 0:
        restart_game()

if __name__ == '__main__':
    app = Ursina()

    # Environment Setup
    ground = Entity(model='plane', collider='box', scale=64, texture='grass', texture_scale=(4,4))
    Sky()

    # Obstacles
    for i in range(15):
        Entity(model='cube', collider='box', position=(random.randint(-20, 20), 1, random.randint(-20, 20)),
               scale=(random.randint(2, 5), random.randint(2, 10), random.randint(2, 5)),
               texture='white_cube', color=color.light_gray)

    # Initialize Managers & Entities
    audio_manager = AudioManager()
    player = Player()
    spawn_manager = SpawnManager(player)

    # Hide default mouse cursor
    mouse.visible = False

    app.run()