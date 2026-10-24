# Neon Runner (Ursina)

    pip install -r requirements.txt
    python main.py

| Key | Action |
|---|---|
| A / D, ← / → | change lane |
| Space (W, ↑) | jump |
| S, ↓ | slide (in mid-air: slam down, then slide) |
| R | instant restart |
| M | mute, `-` / `=` music volume |
| Tab | back to menu |

* Tune everything in `config.py` (speed curve, gaps, jump, camera, `DEBUG_COLLIDERS`).
* Put your own audio in `assets/audio/` (see `assets/audio/README.txt`); missing sounds are generated automatically.
* High score is stored in `highscore.json`.

Files: `main.py` (state machine, camera, input) · `world.py` (pooled chunks/obstacles, generator) · `player.py` · `effects.py` · `ui.py` · `audio_manager.py` / `audio_synth.py` · `storage.py` · `config.py`
