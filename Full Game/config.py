"""Central tuning file for Neon Runner. Change numbers here, not in the logic."""
from pathlib import Path

# ---------------------------------------------------------------- paths
BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "assets" / "audio"            # drop your .wav/.ogg/.mp3 files here
GENERATED_AUDIO_DIR = AUDIO_DIR / "_generated"       # auto-made fallback sounds live here
HIGHSCORE_FILE = BASE_DIR / "highscore.json"

# ---------------------------------------------------------------- track
LANES = (-3, 0, 3)               # X position of each lane
CHUNK_LENGTH = 30                # length of one track chunk along Z
NUM_CHUNKS = 9                   # chunks kept alive (pooled)
RECYCLE_Z = -(CHUNK_LENGTH / 2) - 22   # a chunk whose centre drops below this is recycled
TRACK_WIDTH = 10.5

# ---------------------------------------------------------------- player
LANE_LERP = 14                   # higher = snappier lane change
JUMP_VELOCITY = 12.0
GRAVITY = 34.0
FAST_FALL_VELOCITY = -24.0       # pressing slide in mid-air slams the player down
SLIDE_DURATION = 0.75
SLIDE_SCALE_Y = 0.5              # player (and hitbox) height multiplier while sliding

# ---------------------------------------------------------------- speed & difficulty
MENU_SPEED = 12.0
BASE_SPEED = 20.0
MAX_SPEED = 44.0
SPEED_PER_METER = 0.009          # speed gained per metre travelled
DIFFICULTY_METERS = 3500         # distance at which obstacle density reaches its maximum
GAP_EASY = (34.0, 46.0)          # min/max metres between obstacle rows at the start
GAP_HARD = (20.0, 28.0)          # ... and at full difficulty
FIRST_OBSTACLE_Z = 45.0          # grace distance before the first obstacle

# ---------------------------------------------------------------- camera
CAM_POS = (0, 6.5, -12)
CAM_PITCH = 20
CAM_FOV = 80
CAM_FOLLOW_X = 0.6               # camera follows the player's X by this factor

# ---------------------------------------------------------------- misc
DEBUG_COLLIDERS = False          # True = draw collider wireframes
SHOW_FPS = False
