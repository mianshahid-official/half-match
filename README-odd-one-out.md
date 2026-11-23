# Odd One Out — Kids Video Generator

**Odd One Out** is a standalone CLI video renderer that turns split item halves in `sets/` into viral, kid-friendly 9:16 vertical quiz videos (`1080x1920`, 30 FPS, H.264 + AAC MP4) optimized for YouTube Shorts, Instagram Reels, and TikTok.

---

## What's New

- **Configurable Rounds & Timing**: Select any number of rounds (`--rounds N` / `-r N`) and custom guess wait time before reveal (`--wait-time SECONDS` / `-w SECONDS`).
- **Interactive Launcher**: Double-clicking `run-odd-one-out.bat` interactively prompts for the number of rounds and wait time (press Enter to accept default 5 rounds / 5.0s wait).
- **Vibrant Kids Visuals & Typography**:
  - Punchy cartoon typography with drop shadows and contrasting borders.
  - Glassmorphic translucent cards with gradient gold accent borders.
  - 2x2 grid item cards with soft shadows and glossy white backdrops.
  - Animated dynamic gradient countdown timer bar (smooth transition from neon green → amber → coral red).
  - Prominent countdown timer circle with glowing ring.
  - Reveal highlight: dual neon green ring, vibrant green tick badge, dimmed non-odd items, and highlighted reason banner (e.g., *"Carrot is a VEGETABLE!"*).
- **Expanded Asset Pack**: Full support for all 4 categories (`cars`, `characters`, `fruits`, `vegetables`) and 47+ scenic backgrounds.

---

## How It Works

1. **Rejoining Halves at Runtime**:
   The repository stores items split into two halves: `<name>-1.png` (left) and `<name>-2.png` (right), or `<name>-left.png` and `<name>-right.png`. Odd One Out joins the left and right halves side by side at runtime to reconstruct the complete image pixel-identically.
2. **Dynamic Discovery**:
   Subfolders under `sets/` are discovered automatically. Empty categories are safely skipped. Unpaired halves (like `lonely_pear-1.png`) trigger a printed warning and are skipped without crashing.
3. **2x2 Grid Gameplay**:
   Each round displays 4 items in a 2x2 grid (`440x440` each):
   - **3 items** from a majority category
   - **1 item** from a different category (the "Odd One Out")
   - The odd item's position changes every round (`0=top-left`, `1=top-right`, `2=bottom-left`, `3=bottom-right`).
4. **Customizable Round Timing**:
   - **Guess Phase (Default: 5.0s)**: Title badge, round counter, "Which one is different?", animated shrinking color-shifting timer bar, and countdown number with clock ticks.
   - **Reveal Phase (Default: 2.0s)**: Bell ding chime, 3 wrong items dimmed, double neon-green ring + green tick badge on the odd item, and explanation banner at the bottom.
   - **Intro Card (2.0s)** + **End Card (2.5s)**: Total duration is `2.0 + (rounds * (wait_time + reveal_time)) + 2.5` seconds.
5. **Purely Synthesized Audio**:
   Zero audio files required. Uses a music-box arpeggio loop, deep bass notes, landing pops, clock ticks, reveal ding chime, and end celebration fanfare normalized cleanly below 0 dB.

---

## Setup & Requirements

- **Python**: 3.10+
- **Packages**: `Pillow`, `numpy` (no additional packages required):
  ```bash
  pip install -r requirements.txt
  ```
- **FFmpeg**: Must be on your system `PATH` (e.g. `winget install Gyan.FFmpeg`).

---

## How to Run

### 1. Interactive Double-Click Launcher
Double-click `run-odd-one-out.bat`. It checks dependencies and prompts:
```text
Video Settings (Press Enter to use defaults)
---------------------------------------------------
Number of rounds [default: 5]: 3
Wait time before reveal in seconds [default: 5.0]: 4.0
```
Press Enter to accept defaults, or enter custom values.

### 2. Command Line Options

```bash
# Default (5 rounds, 5s wait time)
python odd_one_out.py

# Custom rounds and custom wait time
python odd_one_out.py --rounds 3 --wait-time 4.0 --out my_quiz.mp4

# Short aliases
python odd_one_out.py -r 4 -w 3.5 -o quick_quiz.mp4

# Custom reveal duration
python odd_one_out.py -r 5 -w 5.0 --reveal-time 2.5

# Specific background
python odd_one_out.py -b sunny_park.png

# Curated sample rounds (from editable ROUNDS list at top of script)
python odd_one_out.py --sample --out curated.mp4
```

### 3. Command Line Flags Reference

| Flag | Short | Default | Description |
|---|---|---|---|
| `--rounds` / `--random` | `-r` | `5` | Number of quiz rounds to generate |
| `--wait-time` / `--guess-time` | `-w` | `5.0` | Wait / guessing time before reveal (seconds) |
| `--reveal-time` | | `2.0` | Duration to display the reveal solution (seconds) |
| `--background` | `-b` | random | Background image filename or path from `backgrounds/` |
| `--out` | `-o` | `odd-one-out.mp4` | Output MP4 video filename |
| `--sample` | | `False` | Render the curated `ROUNDS` list defined in `odd_one_out.py` |
| `--sets` | | `sets` | Directory containing category subfolders with image halves |

---

## Adding New Categories

Drop any paired halves into a subfolder in `sets/` (e.g. `sets/animals/lion-1.png` and `sets/animals/lion-2.png`). The script immediately discovers the new category and incorporates it into the quiz rounds without any code changes.
