# GravSlam — ElbowOS

Original full-colour **Python 3 + pygame** neon gravity-basketball. Charge a launch pad, arc the ball through a sliding hoop, and bounce off floating court orbs. Not a clone of prior ElbowOS tide-hopper / pinball / light-cycle / pipe / grapple reels.

Featured account: [x.com/ElbowOS](https://x.com/ElbowOS)

## Play

```bash
pip install -r requirements.txt
python3 gravslam.py --play
```

Controls: **A/D** or **Left/Right** move pad, **W/S** aim, **SPACE / Up** charge then tap again to launch, **R** restart, **Esc** quit.

## Record a 9:16 reel

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 gravslam.py
```

Writes a 15s 1080×1920 H.264 MP4 (30 fps).

## Reel

Google Drive (view): https://drive.google.com/file/d/1gf7MZil_Y3I_jBD-5dFQx1RKRce8hwoU/view?usp=drivesdk

## License

MIT
