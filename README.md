# Match the Halves — Kids Video Generator

**Match the Halves** is a Windows desktop application (built with Python & PySide6) that automatically turns split images into viral, kid-friendly "match the halves" puzzle videos ready to post on YouTube Shorts, Instagram Reels, and TikTok.

---

## Features
- **Auto-Discovery**: Dynamically scans the `sets/` folder for categories without hardcoded names. Add any new category just by creating a new subfolder!
- **Pair Matching**: Automatically matches item halves named `<name>-1.png` + `<name>-2.png` or `<name>-left.png` + `<name>-right.png`. Unpaired halves are cleanly skipped with warnings.
- **Viral Social Format**: Renders crisp 9:16 vertical videos (`1080x1920` at 30 FPS, H.264 MP4).
- **Smooth Animation Mechanics**:
  - Left halves slide in during the intro to form the vertical stack.
  - Active right half slides in from off-screen right with an ease-out curve.
  - Rounds run bottom-item first: tries each row from top to bottom.
  - Wrong match triggers an animated **X** (pop in with overshoot) and buzzer SFX.
  - Correct match triggers an animated **Tick** and bell chime SFX.
  - Finished items stay whole; final hold on the completed stack.
- **Three Audio Modes**:
  - **Built-in tune (Default)**: Gentle music-box arpeggio synthesized purely in code (zero audio asset dependencies!) plus pop, buzz, and ding sound effects.
  - **My music file**: Load your own `.mp3` or `.wav`, automatically looped or trimmed to match video length, mixed under sound effects with an adjustable volume slider.
  - **Mute**: Generates video with strictly no audio stream (`-an`).
- **Zero-Crash Clamped Audio Mixer**: Strict slice clamping prevents past-buffer indexing and broadcast crashes.

---

## System Requirements & Setup

### 1. Python Environment
Python 3.10+ (tested on Python 3.10 – 3.14 on Windows).

Install dependencies via `pip`:
```bash
pip install -r requirements.txt
```

### 2. FFmpeg Installation (Required for Video Encoding)
FFmpeg must be accessible on your system PATH.
- **Option A (Recommended via Windows Package Manager)**:
  Open Command Prompt or PowerShell and run:
  ```powershell
  winget install Gyan.FFmpeg
  ```
- **Option B (Manual Download)**:
  1. Download an FFmpeg release build from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or [ffmpeg.org](https://ffmpeg.org/download.html).
  2. Extract the archive (e.g. to `C:\ffmpeg`).
  3. Add the `bin` directory (`C:\ffmpeg\bin`) to your Windows User or System Environment Variables under `PATH`.
  4. Open a new terminal and verify with `ffmpeg -version`.

---

## Folder Layout

The project uses the following directory structure:

```
Shortsgen/
├── main.py                  # Primary application entry point
├── gui.py                   # PySide6 desktop GUI interface
├── engine.py                # Video rendering, animation & audio synthesis engine
├── requirements.txt         # Python package dependencies
├── backgrounds/             # Background images (.png, .jpg, .webp)
│   └── README.txt
├── symbols/                 # Correct (tick) & wrong (X) icons
│   └── README.txt
└── sets/                    # Category sets root folder
    ├── cars/                # Cars category
    ├── characters/          # Characters category
    ├── fruits/              # Fruits category
    └── vegetables/          # Vegetables category
```

### File Naming Conventions:
- **Left & Right Halves**:
  - `<item_name>-1.png` (LEFT half) and `<item_name>-2.png` (RIGHT half)
  - OR `<item_name>-left.png` and `<item_name>-right.png`
  - Any image dimensions are supported as long as a pair's two halves have identical dimensions.
- **Backgrounds**:
  - Place any `.png`, `.jpg`, or `.webp` in `backgrounds/`. The engine automatically center-crops and resizes to 9:16 (`1080x1920`).
- **Symbols**:
  - `correct.png`, `tick.png`, `right.png`, or `check.png` (Tick symbol).
  - `wrong.png`, `cross.png`, `x.png`, or `incorrect.png` (Cross symbol).
  - *Fallback*: If either symbol is missing, the engine automatically draws a clean vector tick or X in code.

---

## How to Add a New Category

To add a new category (e.g., `animals`, `superheroes`, `instruments`):
1. Create a new folder inside `sets/`, e.g., `sets/animals/`.
2. Add your paired halves:
   - `lion-1.png` and `lion-2.png`
   - `elephant-left.png` and `elephant-right.png`
   - `zebra-1.png` and `zebra-2.png`
3. Launch the app or click **Refresh Folders**. The app automatically discovers the new folder and lists it in the Category dropdown. No code changes needed!

---

## How the Three Audio Modes Work

1. **Built-in tune (Default)**:
   - Synthesizes a calming music-box arpeggio bed directly in code using NumPy.
   - Synchronizes a **pop** sound when a half lands, a **buzz** sound for wrong matches, and a bright **ding** chime for correct matches.
2. **My music file**:
   - Opens a file selector for any `.mp3` or `.wav` soundtrack.
   - Seamlessly loops short tracks or trims long tracks to match the exact duration of the video.
   - Mixes the music bed under the pop, buzz, and ding sound effects with an interactive volume slider (0% to 100%).
3. **Mute**:
   - Renders the video with strictly no audio track at all (`-an` in FFmpeg).

---

## Running the Application

### Launch the Desktop GUI:
```bash
python main.py
```
*(or `python gui.py`)*

### Headless CLI Mode:
You can also generate videos from the command line:
```bash
# 3 fruits with built-in audio
python main.py --cli --category fruits --count 3 --output fruit_short.mp4

# 4 cars with custom music file
python main.py --cli --category cars --count 4 --audio-mode custom --music-file sample_music.wav --output cars_short.mp4

# Mute mode
python main.py --cli --category fruits --count 3 --audio-mode mute --output mute_short.mp4
```
