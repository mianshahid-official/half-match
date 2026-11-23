# Odd One Out — Kids Video Generator

**Odd One Out** is a standalone CLI video renderer that turns split item halves in `sets/` into viral, kid-friendly 9:16 vertical quiz videos (`1080x1920`, 30 FPS, H.264 + AAC MP4) for YouTube Shorts, Reels, and TikTok.

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
4. **Round Timing (7.0s per round)**:
   - **5s Guess Phase**: Title, round counter, "Which one is different?", animated shrinking timer bar, and countdown number (5 → 1) with clock ticks.
   - **2s Reveal Phase**: Bell ding chime, the 3 wrong items dim, a thick green ring and green tick badge highlight the odd item, and the explanation reason appears at the bottom (e.g., *"Carrot is a VEGETABLE!"*).
   - **Intro Card (2.0s)** + **End Card (2.5s)**: Total video for 5 rounds = **39.5s** (or **25.5s** for 3 rounds).
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

## How to Make Rounds

### 1. Default Run (5 Random Rounds)
Simply double-click `run-odd-one-out.bat` or run:
```bash
python odd_one_out.py
```

### 2. Custom Number of Random Rounds (`--random N`)
```bash
python odd_one_out.py --random 3 --out 3_rounds_quiz.mp4
```

### 3. Hand-Made Rounds (`--sample`)
You can edit the `ROUNDS` list directly at the top of `odd_one_out.py`:
```python
ROUNDS = [
    {
        "majority_cat": "fruits",
        "majority_items": ["apple", "banana", "orange"],
        "odd_cat": "vegetables",
        "odd_item": "carrot",
        "odd_pos": 1
    },
    ...
]
```
Run with `--sample` to render your curated list:
```bash
python odd_one_out.py --sample --out curated_odd_one_out.mp4
```

### 4. Background Selection
```bash
python odd_one_out.py --background sunny_park.png
```
Any image size works (e.g. `1080x1920` or `1600x1600`); backgrounds are center-cropped to 9:16 and scaled to `1080x1920`.

### 5. Adding New Categories
Drop any paired halves into a subfolder in `sets/` (e.g. `sets/animals/lion-1.png` and `sets/animals/lion-2.png`). The script immediately discovers the new category and incorporates it into the quiz rounds.
