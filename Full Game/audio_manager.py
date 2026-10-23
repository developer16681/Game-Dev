"""
AudioManager - background music + sound effects with defensive loading.

WHERE TO PUT YOUR OWN AUDIO
---------------------------
Drop files into  neon_runner/assets/audio/  using these names (.ogg, .wav or .mp3):

    bgm.*            looping background music
    lane_switch.*    whoosh when changing lane
    jump.*           jump
    slide.*          slide
    land.*           landing thud
    crash.*          obstacle collision
    game_over.*      game-over jingle
    start.*          "go!" sound when a run begins

Anything missing is replaced by a procedurally generated chiptune sound (see audio_synth.py),
so the game always has audio. If even that fails (read-only disk, no audio device ...) the sound
becomes a silent no-op and the game keeps running.
"""
import config as C
import audio_synth

# key -> (loops?, base volume multiplier)
SOUND_TABLE = {
    "bgm": (True, 1.0),
    "lane_switch": (False, 0.55),
    "jump": (False, 0.60),
    "slide": (False, 0.60),
    "land": (False, 0.40),
    "crash": (False, 1.00),
    "game_over": (False, 0.85),
    "start": (False, 0.70),
}
EXTENSIONS = (".ogg", ".wav", ".mp3")


class _Sound:
    """Wraps ursina.Audio, falls back to a raw Panda3D sound, then to a silent dummy."""

    def __init__(self, path, loop=False):
        self._ursina = None
        self._panda = None
        self.loop = loop
        if path is None:
            return
        try:
            from ursina import Audio
            snd = Audio(str(path), loop=loop, autoplay=False)
            if getattr(snd, "clip", None) is None:
                raise RuntimeError("clip not loaded")
            self._ursina = snd
            return
        except Exception as exc:
            print(f"[audio] ursina.Audio failed for {path.name}: {exc}")
        try:
            from panda3d.core import Filename
            from ursina import application
            snd = application.base.loader.loadSfx(Filename.from_os_specific(str(path)))
            if snd is None:
                raise RuntimeError("loadSfx returned None")
            snd.setLoop(bool(loop))
            self._panda = snd
        except Exception as exc:
            print(f"[audio] panda3d fallback failed for {path.name}: {exc}")

    @property
    def ok(self):
        return self._ursina is not None or self._panda is not None

    def set_volume(self, v):
        try:
            if self._ursina is not None:
                self._ursina.volume = v
            elif self._panda is not None:
                self._panda.setVolume(v)
        except Exception:
            pass

    def play(self, volume):
        try:
            self.stop()
            self.set_volume(volume)
            if self._ursina is not None:
                self._ursina.loop = self.loop
                self._ursina.play()
            elif self._panda is not None:
                self._panda.play()
        except Exception as exc:
            print(f"[audio] play failed: {exc}")

    def stop(self):
        try:
            if self._ursina is not None:
                try:
                    self._ursina.stop(destroy=False)
                except TypeError:
                    self._ursina.clip.stop()
            elif self._panda is not None:
                self._panda.stop()
        except Exception:
            pass


class AudioManager:
    def __init__(self, music_volume=0.5, sfx_volume=0.8):
        self.music_volume = music_volume
        self.sfx_volume = sfx_volume
        self.muted = False
        self.sounds = {}
        stats = {"custom": 0, "generated": 0, "silent": 0}
        for key, (loop, _base) in SOUND_TABLE.items():
            snd, source = self._load(key, loop)
            self.sounds[key] = snd
            stats[source] += 1
        print(f"[audio] custom={stats['custom']} generated={stats['generated']} silent={stats['silent']}")

    # ----------------------------------------------------------- loading
    @staticmethod
    def _find_custom(key):
        for ext in EXTENSIONS:
            p = C.AUDIO_DIR / f"{key}{ext}"
            try:
                if p.exists():
                    return p
            except OSError:
                pass
        return None

    def _load(self, key, loop):
        custom = self._find_custom(key)
        if custom is not None:
            snd = _Sound(custom, loop)
            if snd.ok:
                return snd, "custom"
        try:
            snd = _Sound(audio_synth.generate(key, C.GENERATED_AUDIO_DIR), loop)
            if snd.ok:
                return snd, "generated"
        except Exception as exc:
            print(f"[audio] could not synthesise '{key}': {exc}")
        return _Sound(None, loop), "silent"

    # ----------------------------------------------------------- SFX
    def play(self, key, volume=1.0):
        snd = self.sounds.get(key)
        if snd is None or self.muted:
            return
        snd.play(SOUND_TABLE[key][1] * self.sfx_volume * volume)

    # ----------------------------------------------------------- music
    def _music_level(self):
        return 0.0 if self.muted else self.music_volume * SOUND_TABLE["bgm"][1]

    def play_music(self, restart=True):
        music = self.sounds["bgm"]
        if restart:
            music.play(self._music_level())
        else:
            music.set_volume(self._music_level())

    def stop_music(self):
        self.sounds["bgm"].stop()

    def set_music_volume(self, v):
        self.music_volume = max(0.0, min(1.0, v))
        self.sounds["bgm"].set_volume(self._music_level())

    def set_sfx_volume(self, v):
        self.sfx_volume = max(0.0, min(1.0, v))

    def toggle_mute(self):
        self.muted = not self.muted
        self.sounds["bgm"].set_volume(self._music_level())
        return self.muted
