# =============================================================================
#   OPEN WORLD RPG  -  Ursina Engine
#   Controls: WASD Move | Shift Sprint | E Interact | Tab Craft | F Use Item
#             LMB Attack | 1-8 Hotbar | Scroll Wheel Switch | F5 Save | F9 Load
# =============================================================================
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random, math, wave, struct, os, json

app = Ursina(borderless=False)
application.target_frame_rate = 60
window.title  = 'Open World RPG -- Survive & Explore'
window.fps_counter.enabled = True
window.exit_button.visible = False
random.seed(1337)

WORLD_HALF = 185

CYL  = Cylinder(resolution=10)
CONE = Cone(resolution=10)

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) or '.'
def _p(fname): return os.path.join(BASE_DIR, fname)

SR = 44100
def _wav(path, samples):
    if os.path.exists(path): return
    with wave.open(path,'w') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes(struct.pack(f'<{len(samples)}h',*samples))
def _tone(freq,dur,amp=16000):
    n=int(SR*dur)
    return [max(-32767,min(32767,int(amp*(1-i/n)*math.sin(2*math.pi*freq*i/SR))))for i in range(n)]
def _noise(dur,amp=14000):
    n=int(SR*dur)
    return [max(-32767,min(32767,int(amp*(1-i/n)*(random.random()*2-1))))for i in range(n)]

_wav(_p('snd_hit.wav'),   _tone(300,0.12,14000))
_wav(_p('snd_die.wav'),   _tone(130,0.45,18000))
_wav(_p('snd_get.wav'),   _tone(880,0.18,12000))
_wav(_p('snd_craft.wav'), _tone(660,0.15,11000))
_wav(_p('snd_sword.wav'), _noise(0.14,20000))
_wav(_p('snd_bow.wav'),   _tone(380,0.10,13000))
_wav(_p('snd_bgm.wav'),   [int(2200*math.sin(2*math.pi*110*i/SR))for i in range(SR*4)])

sfx_hit   = Audio(_p('snd_hit.wav'),   autoplay=False, volume=0.7)
sfx_die   = Audio(_p('snd_die.wav'),   autoplay=False, volume=0.8)
sfx_get   = Audio(_p('snd_get.wav'),   autoplay=False, volume=0.7)
sfx_craft = Audio(_p('snd_craft.wav'), autoplay=False, volume=0.6)
sfx_sword = Audio(_p('snd_sword.wav'), autoplay=False, volume=0.9)
sfx_bow   = Audio(_p('snd_bow.wav'),   autoplay=False, volume=0.8)
bgm       = Audio(_p('snd_bgm.wav'),   loop=True, autoplay=True, volume=0.18)

sky_ent = Sky(color=color.hex('#78b7e3'))
scene.fog_density = 0.004
scene.fog_color   = color.hex('#9ec5d9')
camera.clip_plane_far = 380

sun_light = DirectionalLight(y=120,z=100,x=80,shadows=True,rotation=(45,-35,0))
amb_light = AmbientLight(color=color.rgba(110,120,130,200))
sun_orb   = Entity(model='sphere',position=(100,120,100),scale=14,color=color.hex('#FFF68F'),unlit=True)
moon_orb  = Entity(model='sphere',position=(-100,-120,100),scale=8,color=color.hex('#CED8F0'),unlit=True)
stars     = [Entity(model='sphere',scale=0.35,unlit=True,color=color.white,enabled=False,
                    position=(random.uniform(-350,350),random.uniform(80,180),random.uniform(-350,350)))
             for _ in range(160)]

ground = Entity(model='plane',scale=(400,1,400),color=color.hex('#3b6634'),
                texture='grass',texture_scale=(200,200),collider='box')
for pos,sc in [((0,5,WORLD_HALF),(WORLD_HALF*2,10,2)),((0,5,-WORLD_HALF),(WORLD_HALF*2,10,2)),
               ((WORLD_HALF,5,0),(2,10,WORLD_HALF*2)),((-WORLD_HALF,5,0),(2,10,WORLD_HALF*2))]:
    Entity(model='cube',position=pos,scale=sc,collider='box',visible=False)
for bpos,bcol in [((95,0,95),'#1a4d20'),((-95,0,95),'#cde0ef'),((95,0,-95),'#c5a04a'),((-95,0,-95),'#344a18')]:
    Entity(model='plane',scale=(190,1,190),position=bpos,color=color.hex(bcol),y=0.01)

def get_biome(x,z):
    if x>0 and z>0: return 'Forest'
    if x<0 and z>0: return 'Tundra'
    if x>0 and z<0: return 'Desert'
    return 'Swamp'

ITEMS = {
    'wsword': (1, 'Wooden Sword', color.rgb(0.63,0.39,0.23)),
    'isword': (2, 'Iron Sword',   color.rgb(0.78,0.86,0.94)),
    'bow':    (3, 'Bow',          color.rgb(0.55,0.35,0.16)),
    'arrow':  (4, 'Arrow',        color.rgb(0.78,0.71,0.39)),
    'potion': (5, 'Health Potion',color.rgb(1.00,0.31,0.31)),
    'food':   (6, 'Cooked Food',  color.rgb(0.86,0.63,0.31)),
    'wood':   (7, 'Wood',         color.rgb(0.40,0.26,0.13)),
    'stone':  (8, 'Stone',        color.rgb(0.50,0.50,0.50)),
    'iron':   (9, 'Iron Ore',     color.rgb(0.70,0.47,0.31)),
    'herb':   (10,'Herb',         color.rgb(0.20,0.78,0.20)),
}
HOTBAR_KEYS = ['wsword', 'isword', 'bow', 'arrow', 'potion', 'food', 'wood', 'stone']
RECIPES = {
    'wsword':[('wood',5),('stone',3)], 'isword':[('wood',3),('iron',5)],
    'bow':   [('wood',4),('stone',2)], 'arrow': [('wood',2),('stone',1)],
    'potion':[('herb',3)],             'food':  [('herb',2)],
}

class Inventory:
    def __init__(self):
        self.slots={k:0 for k in ITEMS}; self.selected=0
    def add(self,key,n=1):
        if key in self.slots: self.slots[key]=min(999,self.slots[key]+n)
    def remove(self,key,n=1):
        if self.has(key,n): self.slots[key]-=n; return True
        return False
    def has(self,key,n=1): return self.slots.get(key,0)>=n
    def craft(self,rk):
        if rk not in RECIPES: return
        if not all(self.has(k,c) for k,c in RECIPES[rk]):
            _notify('Not enough materials!'); return
        for k,c in RECIPES[rk]: self.remove(k,c)
        self.add(rk, 10 if rk=='arrow' else 1)
        sfx_craft.play(); _notify(f'Crafted: {ITEMS[rk][1]}')
        quest_mgr.on_craft(rk)
        if hud: hud.refresh_hotbar()
    @property
    def held(self): return HOTBAR_KEYS[min(self.selected,len(HOTBAR_KEYS)-1)]

inventory = Inventory()
inventory.add('wood',5); inventory.add('stone',3); inventory.add('food',2)

hud = None

class QuestManager:
    def __init__(self):
        self.quests = [
            {'name':'Chop Wood',      'type':'collect','item':'wood',   'target':10,'prog':0,'done':False,'rwd':('stone',12)},
            {'name':'Mine Stone',     'type':'collect','item':'stone',  'target':8, 'prog':0,'done':False,'rwd':('iron',4)},
            {'name':'Craft Sword',    'type':'craft',  'item':'wsword', 'target':1, 'prog':0,'done':False,'rwd':('potion',2)},
            {'name':'Slay Goblins',   'type':'kill',   'item':'goblin', 'target':5, 'prog':0,'done':False,'rwd':('herb',4)},
            {'name':'Gather Herbs',   'type':'collect','item':'herb',   'target':5, 'prog':0,'done':False,'rwd':('potion',1)},
            {'name':'Craft Bow',      'type':'craft',  'item':'bow',    'target':1, 'prog':0,'done':False,'rwd':('arrow',20)},
            {'name':'Kill the Troll', 'type':'kill',   'item':'troll',  'target':1, 'prog':0,'done':False,'rwd':('isword',1)},
            {'name':'Mine Iron',      'type':'collect','item':'iron',   'target':5, 'prog':0,'done':False,'rwd':('arrow',20)},
            {'name':'Hunt Wolves',    'type':'kill',   'item':'wolf',   'target':3, 'prog':0,'done':False,'rwd':('food',5)},
        ]
    def on_collect(self,item,amt=1): self._upd('collect',item,amt)
    def on_kill(self,name): self._upd('kill',name,1)
    def on_craft(self,rk): self._upd('craft',rk,1)
    def _upd(self,qt,item,amt):
        for q in self.quests:
            if not q['done'] and q['type']==qt and q['item']==item:
                q['prog']=min(q['target'],q['prog']+amt)
                if q['prog']>=q['target']:
                    q['done']=True; rk,rc=q['rwd']; inventory.add(rk,rc)
                    _notify(f"Quest Done: {q['name']}!  +{rc} {rk.title()}")
                break
        if hud: hud.refresh_quests()

quest_mgr = QuestManager()

interactables=[]
def _find_ia(e,d=0):
    if e is None or d>5: return None
    if getattr(e,'interactable',False): return e
    return _find_ia(getattr(e,'parent',None),d+1)

class TreeNode(Entity):
    def __init__(self,pos):
        super().__init__(position=pos)
        b=get_biome(pos[0],pos[2])
        tc={'Forest':color.hex('#4a2f1c'),'Tundra':color.hex('#5a6060'),'Desert':color.hex('#6a5030'),'Swamp':color.hex('#2a3020')}[b]
        lc={'Forest':color.hex('#1a5220'),'Tundra':color.hex('#cce0f0'),'Desert':color.hex('#8a7030'),'Swamp':color.hex('#2a4a10')}[b]
        Entity(parent=self,model=CYL,color=tc,scale=(0.7,4,0.7),y=2,collider='box')
        if b=='Desert':   Entity(parent=self,model='sphere',color=lc,scale=(4,1.5,4),y=5)
        elif b=='Tundra': Entity(parent=self,model=CONE,color=lc,scale=(3.5,2.5,3.5),y=3.5); Entity(parent=self,model=CONE,color=lc,scale=(2.5,2,2.5),y=5.2)
        elif b=='Swamp':  Entity(parent=self,model='sphere',color=lc,scale=(4,3,4),y=4.5)
        else:
            Entity(parent=self,model=CONE,color=lc,scale=(4,2.5,4),y=3.5)
            Entity(parent=self,model=CONE,color=color.hex('#265c2c'),scale=(3,2.5,3),y=5.2)
            Entity(parent=self,model=CONE,color=color.hex('#317838'),scale=(2,2,2),y=6.8)
        self.remaining=random.randint(3,6); self.interactable=True
        self.interact_label='Chop Tree [E]'; interactables.append(self)
    def interact(self):
        if self.remaining<=0: return
        amt=random.randint(1,2); self.remaining-=amt
        inventory.add('wood',amt); quest_mgr.on_collect('wood',amt)
        sfx_get.play(); _notify(f'+{amt} Wood'); hud.refresh_hotbar()
        if self.remaining<=0: self.interact_label='(Stump)'; self.interactable=False

class RockNode(Entity):
    def __init__(self,pos):
        super().__init__(position=pos)
        b=get_biome(pos[0],pos[2])
        rc={'Forest':color.hex('#606060'),'Tundra':color.hex('#9ab0c0'),'Desert':color.hex('#9a7848'),'Swamp':color.hex('#4a5040')}[b]
        iron=random.random()<0.28; self.resource='iron' if iron else 'stone'
        for _ in range(random.randint(2,4)):
            sx=random.uniform(0.7,1.5)
            Entity(parent=self,model='sphere',color=rc,scale=(sx,random.uniform(0.5,1.2),sx),
                   position=(random.uniform(-0.7,0.7),0.4,random.uniform(-0.7,0.7)),collider='box')
        if iron: Entity(parent=self,model='sphere',color=color.hex('#c07030'),scale=0.35,y=0.9,unlit=True)
        self.remaining=random.randint(2,5); self.interactable=True
        self.interact_label=('Mine Iron [E]' if iron else 'Mine Stone [E]'); interactables.append(self)
    def interact(self):
        if self.remaining<=0: return
        self.remaining-=1; inventory.add(self.resource,1); quest_mgr.on_collect(self.resource,1)
        sfx_get.play(); _notify(f'+1 {ITEMS[self.resource][1]}'); hud.refresh_hotbar()
        if self.remaining<=0: self.interact_label='(Depleted)'; self.interactable=False

class HerbNode(Entity):
    def __init__(self,pos):
        super().__init__(position=pos)
        Entity(parent=self,model='sphere',color=color.hex('#20cc40'),scale=(0.5,0.35,0.5),y=0.17)
        Entity(parent=self,model='sphere',color=color.hex('#18a030'),scale=(0.3,0.5,0.3),y=0.42)
        self.remaining=random.randint(1,3); self.interactable=True
        self.interact_label='Gather Herb [E]'; interactables.append(self)
    def interact(self):
        if self.remaining<=0: return
        self.remaining-=1; inventory.add('herb',1); quest_mgr.on_collect('herb',1)
        sfx_get.play(); _notify('+1 Herb'); hud.refresh_hotbar()
        if self.remaining<=0: self.interactable=False; self.enabled=False

class House(Entity):
    def __init__(self,pos,ry=0):
        super().__init__(position=pos,rotation_y=ry)
        Entity(parent=self,model='cube',scale=(7,3.5,5.5),y=1.75,color=color.hex('#6e4c30'),collider='box')
        Entity(parent=self,model=CONE,scale=(7.8,2.8,6.2),y=4.6,rotation_y=45,color=color.hex('#3e2515'))
        Entity(parent=self,model='cube',scale=(1.2,2.1,0.2),position=(0,1.05,2.76),color=color.hex('#2e190e'))
        Entity(parent=self,model='cube',scale=(1.1,1.1,0.1),position=(-2,1.8,2.76),color=color.hex('#f4d06f'),unlit=True)
        Entity(parent=self,model='cube',scale=(1.1,1.1,0.1),position=(2,1.8,2.76),color=color.hex('#f4d06f'),unlit=True)

class Workbench(Entity):
    def __init__(self,pos):
        super().__init__(position=pos)
        Entity(parent=self,model='cube',scale=(1.5,0.8,0.8),y=0.45,color=color.hex('#6e4c30'),collider='box')
        Entity(parent=self,model='cube',scale=(1.6,0.07,0.9),y=0.84,color=color.hex('#8b5a30'))
        self.interactable=True; self.interact_label='Open Crafting [E]'; interactables.append(self)
    def interact(self): craft_ui.toggle()

class Chest(Entity):
    def __init__(self,pos,loot=None):
        super().__init__(position=pos)
        Entity(parent=self,model='cube',scale=(0.9,0.65,0.6),y=0.32,color=color.hex('#8b6040'),collider='box')
        Entity(parent=self,model='cube',scale=(0.9,0.32,0.6),y=0.81,color=color.hex('#5a3a20'))
        Entity(parent=self,model='cube',scale=(0.92,0.06,0.62),y=0.65,color=color.hex('#FFD700'),unlit=True)
        self.loot=loot or {'wood':3}; self.opened=False
        self.interactable=True; self.interact_label='Open Chest [E]'; interactables.append(self)
    def interact(self):
        if self.opened: return
        self.opened=True; self.interactable=False; self.interact_label='(Empty)'
        for k,v in self.loot.items(): inventory.add(k,v); _notify(f'+{v} {k.title()}')
        sfx_get.play(); hud.refresh_hotbar()

for cx,cz,hn in [(60,60,5),(-70,65,4),(65,-70,4)]:
    for i in range(hn):
        a=i*(360/hn)+10
        House((cx+math.cos(math.radians(a))*13,0,cz+math.sin(math.radians(a))*13),ry=a+180)
    Workbench((cx,0,cz)); Chest((cx+3.5,0,cz),loot={'wood':5,'stone':4,'herb':2})

def rpos(md=8):
    while True:
        x=random.uniform(-WORLD_HALF+5,WORLD_HALF-5); z=random.uniform(-WORLD_HALF+5,WORLD_HALF-5)
        if math.hypot(x,z)>md: return (x,0,z)

for _ in range(175): TreeNode(rpos(5))
for _ in range(90):  RockNode(rpos(4))
for _ in range(55):  HerbNode(rpos(3))
for _ in range(10):
    Chest(rpos(12),random.choice([{'iron':3,'herb':2},{'wood':6,'stone':3},{'stone':5,'iron':2},{'herb':4}]))

enemies=[]

class EnemyBase(Entity):
    def __init__(self,pos,hp,spd,dmg,det,ename,bc,ac,sx=1,sy=1,sz=1):
        super().__init__(position=pos,name='enemy')
        self.max_hp=hp; self.hp=hp; self.speed=spd; self.damage=dmg
        self.detect=det; self.ename=ename; self.state='patrol'
        self.pdir=random.uniform(0,360); self.ptimer=random.uniform(2,5)
        self.atk_t=0; self.atk_cd=1.5
        Entity(parent=self,model='cube',scale=(0.8*sx,1.2*sy,0.5*sz),y=1.6*sy,color=bc,collider='box')
        Entity(parent=self,model='sphere',scale=0.5*sx,y=2.5*sy,color=ac)
        bg=Entity(parent=self,model='quad',scale=(1.2*sx,0.12),y=3.3*sy,color=color.rgba(0,0,0,200),billboard=True)
        self.hpf=Entity(parent=bg,model='quad',scale=(0.95,0.7),color=color.red,origin_x=-0.5,x=-0.475)
        enemies.append(self)
    def hit(self,dmg):
        self.hp-=dmg; self.hpf.scale_x=max(0,self.hp/self.max_hp)*0.95; sfx_hit.play()
        if self.hp<=0: self.die(); return True
        return False
    def die(self):
        sfx_die.play(); quest_mgr.on_kill(self.ename)
        for _ in range(6):
            p=Entity(model='sphere',scale=0.1,color=color.rgb(0.8,0.1,0.1),
                     position=self.position+Vec3(random.uniform(-0.4,0.4),random.uniform(0,1.2),random.uniform(-0.4,0.4)))
            destroy(p,delay=0.4)
        if self in enemies: enemies.remove(self)
        destroy(self)
    def ai_tick(self,dt,night):
        dist=distance(self.position,player.position)
        eff=self.detect*(1.6 if night else 1.0); self.atk_t-=dt
        self.state='attack' if dist<2.5 else ('chase' if dist<eff else 'patrol')
        if self.state=='attack':
            self.look_at_2d(player.position,'y')
            if self.atk_t<=0:
                self.atk_t=self.atk_cd
                ps.hurt(self.damage)
                sfx_hit.play()
                _notify(f"{self.ename.title()} attack! -{self.damage} HP")
        elif self.state=='chase':
            self.look_at_2d(player.position,'y'); self.position+=self.forward*self.speed*dt
        else:
            self.ptimer-=dt
            if self.ptimer<=0: self.pdir=random.uniform(0,360); self.ptimer=random.uniform(2,5)
            self.rotation_y=self.pdir; self.position+=self.forward*self.speed*0.35*dt
        self.y=0
        self.x=clamp(self.x,-WORLD_HALF,WORLD_HALF); self.z=clamp(self.z,-WORLD_HALF,WORLD_HALF)

class Goblin(EnemyBase):
    def __init__(self,p): super().__init__(p,40,2.8,8,22,'goblin',color.hex('#2a6a2a'),color.hex('#45a045'))
class Wolf(EnemyBase):
    def __init__(self,p): super().__init__(p,35,4.5,12,28,'wolf',color.hex('#555555'),color.hex('#888888'),sx=0.9,sy=0.7,sz=1.3)
class Skeleton(EnemyBase):
    def __init__(self,p):
        super().__init__(p,55,2.2,18,35,'skeleton',color.hex('#d0c8b8'),color.hex('#f0f0f0'))
        self.enabled=False
class Troll(EnemyBase):
    def __init__(self,p): super().__init__(p,280,1.8,32,30,'troll',color.hex('#4a5c3a'),color.hex('#2a3a20'),sx=1.7,sy=1.9,sz=1.5)

for _ in range(16): Goblin(rpos(14))
for _ in range(10): Wolf(rpos(14))
for _ in range(8):  Skeleton(rpos(14))
for _ in range(2):  Troll(rpos(30))
skeletons=[e for e in enemies if isinstance(e,Skeleton)]

player=FirstPersonController(speed=10,jump_height=1.8,origin_y=-0.5,position=(0,2,0))
player.cursor.color=color.rgba(255,60,60,200); player.cursor.scale=0.014
vm_rig=Entity(parent=camera,position=(0.4,-0.3,0.65))

def update_viewmodel():
    for c in list(vm_rig.children): destroy(c)
    hk = inventory.held
    cnt = inventory.slots.get(hk, 0)
    if cnt <= 0 and hk not in ('wsword', 'isword', 'bow'):
        Entity(parent=vm_rig, model='sphere', scale=(0.08, 0.08, 0.12), color=color.hex('#d69a65'), position=(0, -0.05, 0))
        return
    if hk == 'wsword':
        Entity(parent=vm_rig, model=CYL, scale=(0.025, 0.16, 0.025), color=color.hex('#4a2e18'), position=(0, -0.05, 0))
        Entity(parent=vm_rig, model='cube', scale=(0.14, 0.025, 0.035), color=color.hex('#6e4c30'), position=(0, 0.03, 0.01))
        Entity(parent=vm_rig, model='cube', scale=(0.045, 0.52, 0.02), color=color.hex('#8b5a2b'), position=(0, 0.30, 0.03))
    elif hk == 'isword':
        Entity(parent=vm_rig, model=CYL, scale=(0.025, 0.16, 0.025), color=color.hex('#222222'), position=(0, -0.05, 0))
        Entity(parent=vm_rig, model='cube', scale=(0.16, 0.025, 0.035), color=color.hex('#d4af37'), position=(0, 0.03, 0.01))
        Entity(parent=vm_rig, model='cube', scale=(0.048, 0.62, 0.02), color=color.hex('#e6f0fa'), position=(0, 0.35, 0.03))
    elif hk == 'bow':
        Entity(parent=vm_rig, model=CYL, scale=(0.022, 0.62, 0.022), color=color.hex('#5c3818'), position=(0, 0.08, 0), rotation=(0, 0, 16))
        Entity(parent=vm_rig, model='cube', scale=(0.005, 0.60, 0.005), color=color.white, position=(-0.04, 0.08, 0))
    elif hk == 'arrow':
        Entity(parent=vm_rig, model=CYL, scale=(0.012, 0.5, 0.012), color=color.hex('#bfa76f'), position=(0, 0.1, 0), rotation=(75, 0, 0))
        Entity(parent=vm_rig, model=CONE, scale=(0.035, 0.08, 0.035), color=color.hex('#888888'), position=(0, 0.1, 0.26), rotation=(-90, 0, 0))
    elif hk == 'potion':
        Entity(parent=vm_rig, model=CYL, scale=(0.07, 0.12, 0.07), color=color.hex('#ff3344'), position=(0, -0.02, 0))
        Entity(parent=vm_rig, model=CYL, scale=(0.035, 0.06, 0.035), color=color.hex('#ffffff'), position=(0, 0.06, 0))
        Entity(parent=vm_rig, model='cube', scale=(0.038, 0.03, 0.038), color=color.hex('#8b5a2b'), position=(0, 0.10, 0))
    elif hk == 'food':
        Entity(parent=vm_rig, model='sphere', scale=(0.09, 0.07, 0.14), color=color.hex('#b85d19'), position=(0, 0, 0))
        Entity(parent=vm_rig, model=CYL, scale=(0.022, 0.09, 0.022), color=color.hex('#f0ede4'), position=(0, 0, -0.09), rotation=(90, 0, 0))
    elif hk == 'wood':
        Entity(parent=vm_rig, model=CYL, scale=(0.06, 0.38, 0.06), color=color.hex('#5c3818'), position=(0, 0.05, 0), rotation=(60, 20, 0))
    elif hk == 'stone':
        Entity(parent=vm_rig, model='sphere', scale=(0.09, 0.08, 0.09), color=color.hex('#777777'), position=(0, 0, 0))
    else:
        Entity(parent=vm_rig, model='sphere', scale=(0.08, 0.08, 0.12), color=color.hex('#d69a65'), position=(0, -0.05, 0))

weather_state='Clear'

class PlayerStats:
    def __init__(self):
        self.health=self.max_health=100; self.stamina=self.max_stamina=100
        self.hunger=self.max_hunger=100; self.dead=False
        self.hunger_t=0.0; self.regen_t=0.0
    def hurt(self,n):
        self.health=max(0,self.health-n)
        if self.health==0 and not self.dead: self.dead=True; death_panel.enabled=True
    def heal(self,n): self.health=min(self.max_health,self.health+n)
    def tick(self,dt):
        mov=any(held_keys[k] for k in('w','a','s','d'))
        spr=held_keys['left shift'] and mov and self.stamina>0
        ws=0.85 if weather_state in('Rain','Storm') else 1.0
        player.speed=(15 if spr else 9)*ws
        self.stamina=max(0,self.stamina-22*dt) if spr else min(100,self.stamina+(18 if not mov else 9)*dt)
        self.hunger_t+=dt
        if self.hunger_t>=8: self.hunger_t=0; self.hunger=max(0,self.hunger-2)
        if self.hunger==0: self.hurt(4)
        if self.hunger>50 and self.health<100:
            self.regen_t+=dt
            if self.regen_t>=3: self.regen_t=0; self.heal(1)
        if player.y<-20: player.position=Vec3(0,3,0); self.hurt(15)

ps=PlayerStats()

melee_cd=0.0
DMG={'wsword':20,'isword':40,'bow':4,'wood':6,'stone':8}

def _find_enemy(e,d=0):
    if e is None or d>4: return None
    if isinstance(e,EnemyBase): return e
    return _find_enemy(getattr(e,'parent',None),d+1)

def do_melee():
    global melee_cd
    if melee_cd>0: return
    melee_cd=0.42; dmg=DMG.get(inventory.held,6)
    if inventory.held in('wsword','isword'): sfx_sword.play()
    else: sfx_hit.play()
    vm_rig.animate_rotation((45, -28, -35), duration=0.10, curve=curve.out_quad)
    invoke(lambda: vm_rig.animate_rotation((0, 0, 0), duration=0.20, curve=curve.in_out_quad), delay=0.11)
    hit=False
    for e in list(enemies):
        if distance(e.position,player.position)<4.0:
            e.hit(dmg); hit=True
            e.position -= e.forward * 0.7
            break
    _notify(f'Hit! -{dmg}' if hit else 'Swing!')

def do_ranged():
    if inventory.held!='bow': return
    if not inventory.has('arrow'): _notify('No arrows! Craft arrows with Wood + Stone'); return
    inventory.remove('arrow'); sfx_bow.play()
    vm_rig.animate_position((0.4, -0.3, 0.50), duration=0.06)
    invoke(lambda: vm_rig.animate_position((0.4, -0.3, 0.65), duration=0.18), delay=0.07)
    hi=raycast(camera.world_position,camera.forward,distance=70,ignore=[player,vm_rig]+vm_rig.children)
    if hi.hit:
        tgt=_find_enemy(hi.entity)
        if tgt: tgt.hit(28); _notify('Arrow Hit! -28')
        for _ in range(5):
            p=Entity(model='sphere',scale=0.08,color=color.yellow,
                     position=hi.world_point+Vec3(random.uniform(-0.2,0.2),random.uniform(-0.2,0.2),random.uniform(-0.2,0.2)))
            destroy(p,delay=0.25)
    hud.refresh_hotbar()

solar=0.0; is_night=False; DAY_LEN=120

def day_night_tick(dt):
    global solar,is_night
    solar+=dt/DAY_LEN*2*math.pi
    sx=math.cos(solar)*200; sy=math.sin(solar)*200
    sun_orb.position=Vec3(sx,sy,100); sun_light.position=sun_orb.position
    sun_light.look_at(Vec3(0,0,0)); moon_orb.position=Vec3(-sx,-sy,100)
    df=clamp(math.sin(solar),0.05,1.0)
    sky_ent.color=color.rgba(int(120*df),int(183*df),int(227*df),255)
    scene.fog_color=color.rgba(int(158*df),int(197*df),int(217*df),255)
    amb_light.color=color.rgba(int(110*df),int(120*df),int(130*df),200)
    was=is_night; is_night=df<0.22
    if is_night!=was:
        for sk in skeletons:
            try: sk.enabled=is_night
            except: pass
        for st in stars: st.enabled=is_night
        _notify('Night falls... Beware!' if is_night else 'Dawn breaks!')

clouds=[]
for _ in range(22):
    ce=Entity(position=(random.uniform(-180,180),random.uniform(38,55),random.uniform(-180,180)))
    ce.drift=random.uniform(1.8,3.5)
    for ox,oy,oz,csx,csy,csz in [(0,0,0,7,3.5,6),(-4,-0.5,0.5,5,2.5,4.5),(3.5,-0.5,-0.5,5.2,2.8,4.8)]:
        Entity(parent=ce,model='sphere',position=(ox,oy,oz),scale=(csx,csy,csz),color=color.rgba(240,245,255,210),unlit=True)
    clouds.append(ce)

rain_ents=[Entity(model='cube',scale=(0.025,0.38,0.025),color=color.rgba(150,180,230,200),unlit=True,enabled=False)
           for _ in range(160)]
weather_t=random.uniform(60,100)
WSTATES=['Clear','Cloudy','Rain','Storm']; WWTS=[0.45,0.30,0.18,0.07]

def apply_weather(s):
    r=s in('Rain','Storm')
    for re in rain_ents: re.enabled=r
    scene.fog_density={'Clear':0.003,'Cloudy':0.006,'Rain':0.011,'Storm':0.018}[s]

def weather_tick(dt):
    global weather_state,weather_t
    weather_t-=dt
    if weather_t<=0:
        weather_state=random.choices(WSTATES,WWTS)[0]; weather_t=random.uniform(45,100)
        apply_weather(weather_state); _notify(f'Weather: {weather_state}')
    if weather_state in('Rain','Storm'):
        px,py,pz=player.x,player.y,player.z
        for r in rain_ents:
            r.y-=20*dt
            if r.y<py-2: r.position=Vec3(px+random.uniform(-18,18),py+random.uniform(7,14),pz+random.uniform(-18,18))

death_panel=Entity(parent=camera.ui,model='quad',scale=(2,2),color=color.rgba(160,0,0,200),enabled=False,z=-1)
Text(parent=death_panel,text='YOU DIED',origin=(0,0),scale=4,color=color.white,y=0.1)
Text(parent=death_panel,text='Press R to Respawn',origin=(0,0),scale=1.8,color=color.rgb(0.9,0.4,0.4),y=-0.06)

def do_respawn():
    ps.dead=False; ps.health=60; ps.hunger=70
    player.position=Vec3(0,3,0); death_panel.enabled=False; _notify('Respawned. Stay safe.')

_ntxt=None; _ntimer=0.0
def _notify(msg):
    global _ntimer
    if _ntxt: _ntxt.text=msg; _ntimer=2.8

class HUD:
    BW=0.155; BCX=-0.78
    def __init__(self):
        global _ntxt
        self._hpf=self._bar(self.BCX,0.43,'HP',color.rgb(0.8,0.2,0.2))
        self._stf=self._bar(self.BCX,0.35,'ST',color.rgb(0.2,0.8,0.3))
        self._hnf=self._bar(self.BCX,0.27,'HN',color.rgb(0.9,0.6,0.2))
        Entity(parent=camera.ui,model='quad',scale=(0.18,0.044),position=(0,0.46),color=color.rgba(0,0,0,160))
        self._dir=Text(parent=camera.ui,text='N',position=(-0.008,0.455),scale=1.1,color=color.gold)
        self._bio=Text(parent=camera.ui,text='Forest',position=(-0.04,0.44),scale=0.65,color=color.cyan)
        self._hbgs=[]; self._hics=[]; self._hcnt=[]
        sw=0.073; sx0=-4*sw+sw/2
        for i in range(8):
            sx=sx0+i*sw
            bg=Entity(parent=camera.ui,model='quad',scale=(0.066,0.066),position=(sx,-0.44),color=color.rgba(0,0,0,160))
            ic=Entity(parent=camera.ui,model='quad',scale=(0.053,0.053),position=(sx,-0.44),color=color.rgba(80,80,80,80))
            Text(parent=camera.ui,text=str(i+1),position=(sx-0.031,-0.416),scale=0.5,color=color.rgba(200,200,200,160))
            ct=Text(parent=camera.ui,text='',position=(sx-0.022,-0.456),scale=0.6)
            self._hbgs.append(bg); self._hics.append(ic); self._hcnt.append(ct)
        self.refresh_hotbar()
        Entity(parent=camera.ui,model='quad',scale=(0.33,0.25),position=(-0.70,-0.33),color=color.rgba(0,0,0,140))
        Text(parent=camera.ui,text='-- QUESTS --',position=(-0.85,-0.22),scale=0.76,color=color.gold)
        self._qls=[Text(parent=camera.ui,text='',position=(-0.85,-0.27-i*0.038),scale=0.55,color=color.white)for i in range(5)]
        self.refresh_quests()
        mx,my,mr=0.77,0.35,0.065; self._mmx=mx; self._mmy=my; self._mmr=mr
        Entity(parent=camera.ui,model='circle',scale=(mr*2+0.007,mr*2+0.007),position=(mx,my),color=color.rgba(0,180,0,180))
        Entity(parent=camera.ui,model='circle',scale=(mr*2,mr*2),position=(mx,my),color=color.rgba(0,20,5,210))
        Text(parent=camera.ui,text='MAP',position=(mx-0.025,my+mr+0.008),scale=0.55,color=color.green)
        self._mmp=Entity(parent=camera.ui,model='circle',scale=0.009,position=(mx,my),color=color.white)
        self._mmed=[]; self._mmtick=0.0
        _ntxt=Text(parent=camera.ui,text='',position=(0,0.12),scale=1.2,color=color.gold,origin=(0,0))
        self._ip=Text(parent=camera.ui,text='',position=(0,-0.1),scale=1.0,color=color.yellow,origin=(0,0),enabled=False)
        self._it=None; self._irt=0.0
        Text(parent=camera.ui,text='WASD Move | Shift Sprint | E Interact | Tab Craft | F Use | LMB Attack | 1-8 Hotbar | F5 Save | F9 Load',
             position=(0,-0.47),scale=0.45,color=color.rgba(200,200,200,160),origin=(0,0))
    def _bar(self,cx,cy,lbl,col):
        bw,bh=self.BW,0.022
        Entity(parent=camera.ui,model='quad',scale=(bw,bh),position=(cx,cy),color=color.rgba(0,0,0,160))
        f=Entity(parent=camera.ui,model='quad',scale=(bw,bh*0.70),position=(cx-bw/2,cy),color=col,origin_x=-0.5)
        Text(parent=camera.ui,text=lbl,position=(cx-bw/2+0.005,cy-0.008),scale=0.65,color=color.white)
        return f
    def update(self,dt):
        global _ntimer
        bw=self.BW
        self._hpf.scale_x=max(0,ps.health/ps.max_health)*bw
        self._stf.scale_x=max(0,ps.stamina/ps.max_stamina)*bw
        self._hnf.scale_x=max(0,ps.hunger/ps.max_hunger)*bw
        dirs=['N','NE','E','SE','S','SW','W','NW']
        self._dir.text=dirs[int((player.rotation_y%360+22.5)/45)%8]
        self._bio.text=get_biome(player.x,player.z)
        if _ntimer>0:
            _ntimer-=dt; a=max(0,int(_ntimer/2.8*255))
            _ntxt.color=color.rgba(255,215,0,a)
            if _ntimer<=0: _ntxt.text=''
        self._irt-=dt
        if self._irt<=0:
            self._irt=1/30
            hi=raycast(camera.world_position,camera.forward,distance=4,ignore=[player,vm_rig]+vm_rig.children)
            tgt=_find_ia(hi.entity) if hi.hit else None
            if tgt: self._ip.text=tgt.interact_label; self._ip.enabled=True; self._it=tgt
            else:   self._ip.enabled=False; self._it=None
        self._mmtick-=dt
        if self._mmtick<=0:
            self._mmtick=0.5
            def w2m(wx,wz): return(self._mmx+wx/WORLD_HALF*self._mmr,self._mmy+wz/WORLD_HALF*self._mmr)
            px,py=w2m(player.x,player.z); self._mmp.position=(px,py)
            for d in self._mmed: destroy(d)
            self._mmed.clear()
            for e in enemies[:25]:
                ex,ey=w2m(e.x,e.z)
                self._mmed.append(Entity(parent=camera.ui,model='circle',scale=0.005,position=(ex,ey),color=color.red))
    def refresh_hotbar(self):
        for i,k in enumerate(HOTBAR_KEYS):
            cnt=inventory.slots.get(k,0)
            self._hcnt[i].text=str(cnt) if cnt else ''
            self._hics[i].color=ITEMS[k][2] if cnt>0 else color.rgba(60,60,60,60)
            self._hbgs[i].color=color.rgba(255,230,80,220) if i==inventory.selected else color.rgba(0,0,0,160)
        update_viewmodel()
    def refresh_quests(self):
        active=[q for q in quest_mgr.quests if not q['done']][:3]
        done_=[q for q in quest_mgr.quests if q['done']][:2]
        shown=active+done_
        for i,ql in enumerate(self._qls):
            if i<len(shown):
                q=shown[i]; s='Done' if q['done'] else f"{q['prog']}/{q['target']}"
                ql.text=f"{'v' if q['done'] else 'o'} {q['name']}: {s}"
                ql.color=color.green if q['done'] else color.white
            else: ql.text=''

hud=HUD()

class CraftUI:
    def __init__(self):
        self.open=False
        self.panel=Entity(parent=camera.ui,model='quad',scale=(0.60,0.72),position=(0,0),
                          color=color.rgba(8,12,22,232),enabled=False,z=-0.5)
        Text(parent=self.panel,text='** CRAFTING **',position=(0,0.31),scale=1.9,color=color.gold)
        Text(parent=self.panel,text='[Tab] to Close',position=(0,-0.35),scale=0.85,color=color.gray)
        self.btns=[]
        for i,(rk,recipe) in enumerate(RECIPES.items()):
            y=0.23-i*0.085
            Entity(parent=self.panel,model='quad',scale=(0.93,0.07),position=(0,y),color=color.rgba(25,35,55,210))
            istr=' + '.join(f"{c} {ITEMS[k][1]}" for k,c in recipe)
            lbl=Text(parent=self.panel,text=f"{ITEMS[rk][1]}  <-  {istr}",position=(-0.44,y-0.012),scale=0.82,color=color.white)
            btn=Button(parent=self.panel,text='CRAFT',model='quad',scale=(0.17,0.052),
                       position=(0.38,y),color=color.rgb(0.1,0.4,0.8),highlight_color=color.rgb(0.2,0.6,1.0))
            btn.on_click=lambda key=rk: self._do(key)
            self.btns.append((btn,lbl,rk))
    def _do(self,rk): inventory.craft(rk); self.refresh()
    def toggle(self):
        self.open=not self.open; self.panel.enabled=self.open
        mouse.locked=not self.open; player.enabled=not self.open
        if self.open: self.refresh()
    def refresh(self):
        for btn,lbl,rk in self.btns:
            ok=all(inventory.has(k,c) for k,c in RECIPES[rk])
            btn.color=color.rgb(0.1,0.45,0.1) if ok else color.rgb(0.4,0.1,0.1)
            lbl.color=color.white if ok else color.rgb(0.62,0.62,0.62)

craft_ui=CraftUI()

SAVE=os.path.join(os.path.dirname(__file__) or '.','rpg_save.json')
def save_game():
    with open(SAVE,'w') as f:
        json.dump({'pos':[round(player.x,2),round(player.y,2),round(player.z,2)],
                   'health':ps.health,'hunger':ps.hunger,
                   'inv':{k:v for k,v in inventory.slots.items() if v>0},
                   'quests':[{'prog':q['prog'],'done':q['done']} for q in quest_mgr.quests]},f,indent=2)
    _notify('Game Saved!')

def load_game():
    if not os.path.exists(SAVE): _notify('No save file!'); return
    try:
        d=json.load(open(SAVE))
        player.position=Vec3(*d['pos']); ps.health=d.get('health',100); ps.hunger=d.get('hunger',100)
        for k,v in d.get('inv',{}).items():
            if k in inventory.slots: inventory.slots[k]=v
        for i,q in enumerate(d.get('quests',[])):
            if i<len(quest_mgr.quests):
                quest_mgr.quests[i]['prog']=q.get('prog',0); quest_mgr.quests[i]['done']=q.get('done',False)
        hud.refresh_hotbar(); hud.refresh_quests(); _notify('Game Loaded!')
    except Exception as e: _notify(f'Load error: {e}')

def update():
    global melee_cd
    dt=time.dt
    if ps.dead: return
    melee_cd=max(0,melee_cd-dt); ps.tick(dt)
    day_night_tick(dt); weather_tick(dt); hud.update(dt)
    for e in list(enemies):
        if e.enabled and hasattr(e,'ai_tick'): e.ai_tick(dt,is_night)
    for c in clouds:
        c.x+=c.drift*dt
        if c.x>200: c.x=-200

def input(key):
    if ps.dead:
        if key=='r': do_respawn()
        return
    if key=='left mouse down':
        do_ranged() if inventory.held=='bow' else do_melee()
    if key=='e':
        if hud._it: hud._it.interact()
    if key=='tab': craft_ui.toggle()
    if key=='f':
        hk=inventory.held
        if hk=='food' and inventory.has('food'):
            inventory.remove('food'); ps.hunger=min(100,ps.hunger+35); _notify('+35 Hunger'); hud.refresh_hotbar()
        elif hk=='potion' and inventory.has('potion'):
            inventory.remove('potion'); ps.heal(50); _notify('+50 HP'); hud.refresh_hotbar()
    for i in range(1,9):
        if key==str(i): inventory.selected=i-1; hud.refresh_hotbar()
    if key=='scroll up':   inventory.selected=(inventory.selected-1)%8; hud.refresh_hotbar()
    if key=='scroll down': inventory.selected=(inventory.selected+1)%8; hud.refresh_hotbar()
    if key=='f5': save_game()
    if key=='f9': load_game()
    if key=='escape': application.quit()

invoke(lambda: _notify('Welcome! Explore, gather, craft & survive. Quests are on the left!'), delay=1.5)
app.run()
