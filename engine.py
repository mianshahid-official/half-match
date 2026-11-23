"""
Match the Halves - Core Video Generation and Asset Discovery Engine.

Handles:
- Dynamic discovery of categories, pairs, backgrounds, and symbols
- Validation and error reporting
- Video frame rendering (1080x1920, 30fps)
- Animation math (slide in, ease out, pop, overshoot, fade out)
- Audio synthesis (music-box bed, pop, buzz, ding) and user music mixing
- Zero-leak audio buffer clamping
- FFmpeg streaming and encoding
"""

import os
import re
import math
import shutil
import subprocess
import tempfile
import wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Canvas specifications
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
FPS = 30
SAMPLE_RATE = 44100

def check_ffmpeg():
    """
    Checks if ffmpeg is available on PATH.
    Returns (is_available: bool, message: str)
    """
    path = shutil.which("ffmpeg")
    if path:
        return True, f"FFmpeg found at {path}"
    
    # Try running ffmpeg directly
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, "FFmpeg is available on PATH."
    except Exception:
        pass

    msg = (
        "FFmpeg is missing from your system PATH.\n\n"
        "To install FFmpeg on Windows:\n"
        "1. Open Command Prompt / PowerShell as Administrator and run:\n"
        "   winget install Gyan.FFmpeg\n"
        "2. Or download a build from https://www.gyan.dev/ffmpeg/builds/ (or https://ffmpeg.org/download.html),\n"
        "   extract the zip, and add the 'bin' folder to your System Environment PATH.\n"
        "3. Restart the application."
    )
    return False, msg

def discover_categories(sets_dir):
    """
    Discovers all subdirectories under sets_dir and matches image pairs.
    Pair naming conventions:
      <name>-1.<ext> & <name>-2.<ext>
      <name>-left.<ext> & <name>-right.<ext>
    Supported extensions: .png, .jpg, .jpeg, .webp
    
    Returns:
      categories: dict of {category_name: [{"name": str, "left": path, "right": path}, ...]}
      warnings: list of warning strings for unpaired files
    """
    categories = {}
    warnings = []
    
    if not os.path.exists(sets_dir):
        return categories, [f"Sets directory '{sets_dir}' does not exist."]
    
    valid_exts = {".png", ".jpg", ".jpeg", ".webp"}
    
    # Find all subdirectories dynamically
    subdirs = [d for d in os.listdir(sets_dir) if os.path.isdir(os.path.join(sets_dir, d))]
    
    for sub in sorted(subdirs):
        cat_path = os.path.join(sets_dir, sub)
        files = os.listdir(cat_path)
        
        # Categorize left and right files
        left_files = {}   # item_name -> filepath
        right_files = {}  # item_name -> filepath
        all_halves = set()
        
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in valid_exts:
                continue
            
            base = os.path.splitext(f)[0]
            # Match -1 / -2
            m_num = re.match(r"^(.*?)-(1|2)$", base, re.IGNORECASE)
            if m_num:
                name, part = m_num.group(1), m_num.group(2)
                all_halves.add(f)
                if part == "1":
                    left_files[name] = os.path.join(cat_path, f)
                else:
                    right_files[name] = os.path.join(cat_path, f)
                continue
                
            # Match -left / -right
            m_side = re.match(r"^(.*?)-(left|right)$", base, re.IGNORECASE)
            if m_side:
                name, part = m_side.group(1), m_side.group(2).lower()
                all_halves.add(f)
                if part == "left":
                    left_files[name] = os.path.join(cat_path, f)
                else:
                    right_files[name] = os.path.join(cat_path, f)
                continue
        
        # Match pairs
        pairs = []
        all_item_names = sorted(set(left_files.keys()).union(set(right_files.keys())))
        
        for item in all_item_names:
            has_left = item in left_files
            has_right = item in right_files
            
            if has_left and has_right:
                pairs.append({
                    "name": item,
                    "left": left_files[item],
                    "right": right_files[item]
                })
            else:
                missing = "right" if has_left else "left"
                present_file = os.path.basename(left_files[item] if has_left else right_files[item])
                warnings.append(
                    f"Category '{sub}': item '{item}' ({present_file}) has no {missing} partner and was skipped."
                )
                
        categories[sub] = pairs
        
    return categories, warnings

def discover_backgrounds(backgrounds_dir):
    """
    Finds all valid background images.
    """
    valid_exts = {".png", ".jpg", ".jpeg", ".webp"}
    if not os.path.exists(backgrounds_dir):
        return []
    bgs = [
        os.path.join(backgrounds_dir, f)
        for f in sorted(os.listdir(backgrounds_dir))
        if os.path.splitext(f)[1].lower() in valid_exts
    ]
    return bgs

def discover_symbols(symbols_dir):
    """
    Finds tick (correct) and cross (wrong) symbols.
    """
    valid_exts = {".png", ".jpg", ".jpeg", ".webp"}
    correct_path = None
    wrong_path = None
    
    if os.path.exists(symbols_dir):
        for f in os.listdir(symbols_dir):
            base, ext = os.path.splitext(f)
            if ext.lower() not in valid_exts:
                continue
            base_lower = base.lower()
            if base_lower in {"correct", "tick", "right", "check"}:
                if not correct_path:
                    correct_path = os.path.join(symbols_dir, f)
            elif base_lower in {"wrong", "cross", "x", "incorrect"}:
                if not wrong_path:
                    wrong_path = os.path.join(symbols_dir, f)
                    
    return correct_path, wrong_path

# --- Built-in Graphic Fallbacks ---

def draw_builtin_tick(size=200):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = int(size * 0.08)
    draw.ellipse([pad, pad, size - pad, size - pad], fill=(46, 204, 113, 255), outline=(39, 174, 96, 255), width=int(size * 0.04))
    # Checkmark
    p1 = (int(size * 0.28), int(size * 0.52))
    p2 = (int(size * 0.44), int(size * 0.68))
    p3 = (int(size * 0.72), int(size * 0.32))
    draw.line([p1, p2, p3], fill=(255, 255, 255, 255), width=int(size * 0.09), joint="curve")
    return img

def draw_builtin_cross(size=200):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = int(size * 0.08)
    draw.ellipse([pad, pad, size - pad, size - pad], fill=(231, 76, 60, 255), outline=(192, 57, 43, 255), width=int(size * 0.04))
    # X
    s = int(size * 0.28)
    e = int(size * 0.72)
    w = int(size * 0.09)
    draw.line([(s, s), (e, e)], fill=(255, 255, 255, 255), width=w)
    draw.line([(e, s), (s, e)], fill=(255, 255, 255, 255), width=w)
    return img

def draw_default_background(w=CANVAS_WIDTH, h=CANVAS_HEIGHT):
    img = Image.new("RGB", (w, h), (135, 206, 250))
    draw = ImageDraw.Draw(img)
    draw.ellipse([int(w*0.6), int(h*0.05), int(w*0.9), int(h*0.22)], fill=(255, 223, 0))
    draw.chord([int(-w*0.3), int(h*0.65), int(w*1.3), int(h*1.2)], start=0, end=180, fill=(46, 204, 113))
    return img

# --- Image Processing ---

def prepare_background(bg_path, target_w=CANVAS_WIDTH, target_h=CANVAS_HEIGHT):
    if not bg_path or not os.path.exists(bg_path):
        return draw_default_background(target_w, target_h)
    
    try:
        im = Image.open(bg_path).convert("RGB")
        bw, bh = im.size
        target_ratio = target_w / target_h
        current_ratio = bw / bh
        
        if current_ratio > target_ratio:
            # Crop horizontal sides
            crop_w = int(bh * target_ratio)
            left = (bw - crop_w) // 2
            im = im.crop((left, 0, left + crop_w, bh))
        else:
            # Crop vertical top/bottom
            crop_h = int(bw / target_ratio)
            top = (bh - crop_h) // 2
            im = im.crop((0, top, bw, top + crop_h))
            
        im = im.resize((target_w, target_h), Image.Resampling.LANCZOS)
        return im
    except Exception:
        return draw_default_background(target_w, target_h)

def prepare_half(image_path, target_w, target_h):
    """
    Loads an image half and resizes to target_w x target_h with RGBA.
    """
    im = Image.open(image_path).convert("RGBA")
    return im.resize((target_w, target_h), Image.Resampling.LANCZOS)

def prepare_symbol(symbol_path, fallback_fn, target_size):
    if symbol_path and os.path.exists(symbol_path):
        try:
            im = Image.open(symbol_path).convert("RGBA")
            im.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)
            # Create a centered square transparent canvas
            sq = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
            ox = (target_size - im.width) // 2
            oy = (target_size - im.height) // 2
            sq.paste(im, (ox, oy), im)
            return sq
        except Exception:
            pass
    return fallback_fn(target_size)

# --- Easing Functions ---

def ease_out_cubic(t):
    return 1.0 - math.pow(1.0 - t, 3)

def ease_in_out_quad(t):
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - math.pow(-2.0 * t + 2.0, 2) / 2.0

def symbol_overshoot_scale(t_norm):
    """
    Pops in with overshoot: 0.0 -> 1.15 -> 1.0.
    t_norm in [0, 1] for the pop-in phase.
    """
    if t_norm <= 0.0:
        return 0.0
    if t_norm >= 1.0:
        return 1.0
    # Overshoot spring curve
    return math.sin(t_norm * math.pi * 0.75) * 1.15 if t_norm < 0.7 else (1.15 - 0.15 * ((t_norm - 0.7) / 0.3))

# --- Audio Synthesis & Clamped Mixer ---

def mix_audio_track(base_buffer, sfx, start_sample, volume=1.0):
    """
    Mixes sfx into base_buffer starting at start_sample.
    Guaranteed zero-leak clamping: never indexes past base_buffer.
    """
    if start_sample < 0 or start_sample >= len(base_buffer):
        return
    end_sample = min(start_sample + len(sfx), len(base_buffer))
    count = end_sample - start_sample
    if count > 0:
        base_buffer[start_sample:end_sample] += sfx[:count] * volume

def synth_pop_sfx(sample_rate=SAMPLE_RATE):
    """
    Pop sound when a half lands.
    Rapid sine frequency drop from 650Hz to 160Hz over 0.08s.
    """
    dur = 0.08
    n_samples = int(dur * sample_rate)
    t = np.linspace(0, dur, n_samples, endpoint=False)
    freq = 650.0 - 490.0 * (t / dur)
    phase = 2 * np.pi * np.cumsum(freq) / sample_rate
    env = np.exp(-t * 35.0)
    audio = 0.8 * np.sin(phase) * env
    return audio.astype(np.float32)

def synth_buzz_sfx(sample_rate=SAMPLE_RATE):
    """
    Buzz sound for wrong match (X).
    Dissonant dual frequency buzz (140Hz + 185Hz) with decaying envelope.
    """
    dur = 0.38
    n_samples = int(dur * sample_rate)
    t = np.linspace(0, dur, n_samples, endpoint=False)
    wave1 = np.sign(np.sin(2 * np.pi * 140.0 * t))
    wave2 = np.sign(np.sin(2 * np.pi * 185.0 * t))
    mix = 0.4 * wave1 + 0.3 * wave2
    env = np.clip(1.0 - t / dur, 0.0, 1.0) * np.exp(-t * 2.5)
    audio = mix * env * 0.6
    return audio.astype(np.float32)

def synth_ding_sfx(sample_rate=SAMPLE_RATE):
    """
    Ding sound for correct match (Tick).
    Bright sweet bell chime (1046.5Hz [C6] + 2093Hz [C7] + 3136Hz) with exponential ring.
    """
    dur = 0.70
    n_samples = int(dur * sample_rate)
    t = np.linspace(0, dur, n_samples, endpoint=False)
    c6 = 0.55 * np.sin(2 * np.pi * 1046.5 * t) * np.exp(-t * 4.0)
    c7 = 0.35 * np.sin(2 * np.pi * 2093.0 * t) * np.exp(-t * 6.5)
    g7 = 0.15 * np.sin(2 * np.pi * 3136.0 * t) * np.exp(-t * 9.0)
    audio = (c6 + c7 + g7) * 0.85
    return audio.astype(np.float32)

def synth_music_box_bed(duration_sec, sample_rate=SAMPLE_RATE):
    """
    Gentle music-box arpeggio bed.
    """
    n_samples = int(duration_sec * sample_rate)
    bed = np.zeros(n_samples, dtype=np.float32)
    
    # Music box melody progression (frequencies in Hz)
    melody_notes = [
        523.25, 659.25, 783.99, 1046.50, # C5, E5, G5, C6
        587.33, 698.46, 880.00, 1174.66, # D5, F5, A5, D6
        659.25, 783.99, 987.77, 1318.51, # E5, G5, B5, E6
        698.46, 880.00, 1046.50, 1396.91 # F5, A5, C6, F6
    ]
    note_dur = 0.28
    
    for i, freq in enumerate(melody_notes * int(duration_sec / (len(melody_notes) * note_dur) + 2)):
        t_start = i * note_dur
        if t_start >= duration_sec:
            break
        note_len = 0.60
        s_count = int(note_len * sample_rate)
        t_note = np.linspace(0, note_len, s_count, endpoint=False)
        tone = (
            0.6 * np.sin(2 * np.pi * freq * t_note) +
            0.25 * np.sin(2 * np.pi * freq * 2 * t_note) +
            0.15 * np.sin(2 * np.pi * freq * 3 * t_note)
        ) * np.exp(-t_note * 5.0) * 0.25
        
        start_idx = int(t_start * sample_rate)
        mix_audio_track(bed, tone.astype(np.float32), start_idx, volume=1.0)
        
    return bed

def load_user_music(file_path, duration_sec, sample_rate=SAMPLE_RATE):
    """
    Loads user's audio file using ffmpeg, loops or trims to duration_sec.
    """
    n_target = int(duration_sec * sample_rate)
    cmd = [
        "ffmpeg", "-y",
        "-i", file_path,
        "-f", "s16le",
        "-ac", "1",
        "-ar", str(sample_rate),
        "pipe:1"
    ]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        raw_bytes = proc.stdout
        if not raw_bytes:
            raise RuntimeError("Could not decode audio from user file.")
        audio = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Loop or trim
        if len(audio) < n_target:
            repeats = int(math.ceil(n_target / len(audio)))
            audio = np.tile(audio, repeats)
        audio = audio[:n_target]
        return audio
    except Exception as e:
        raise RuntimeError(f"Failed to load music file '{file_path}': {e}")

# --- Render Timeline Generation ---

class TimelineStep:
    def __init__(self, step_type, item_idx, target_row, from_row=None, duration_sec=1.0):
        self.step_type = step_type  # 'intro', 'slide_in', 'move_row', 'try_wrong', 'try_correct', 'final_hold'
        self.item_idx = item_idx
        self.target_row = target_row
        self.from_row = from_row
        self.duration_sec = duration_sec
        self.start_frame = 0
        self.end_frame = 0

def build_timeline(num_items):
    """
    Constructs the exact sequence of animation steps based on user specs:
    - Stack slides in during first second (~1.0s)
    - Rounds run bottom item first:
      - its right half tries each left half top to bottom (X on wrong for ~1.2s, tick on right for ~1.5s)
      - next item's half tries remaining rows, and so on.
      - last half lands on the right one straight away (~1.5s).
      - finished items stay whole.
    - Final hold on finished stack ~1.3s.
    """
    steps = []
    
    # 1. Stack entry: left halves slide in
    steps.append(TimelineStep("intro", item_idx=-1, target_row=-1, duration_sec=1.0))
    
    # 2. Rounds run bottom item first: k = num_items - 1 down to 0
    for k in range(num_items - 1, -1, -1):
        if k > 0:
            # Tries rows 0 up to k
            for r in range(0, k + 1):
                is_correct = (r == k)
                if r == 0:
                    # Slides in from offscreen right to row 0 (~0.7s)
                    steps.append(TimelineStep("slide_in", item_idx=k, target_row=0, duration_sec=0.7))
                else:
                    # Moves down from row r-1 to row r (~0.35s)
                    steps.append(TimelineStep("move_row", item_idx=k, target_row=r, from_row=r-1, duration_sec=0.35))
                
                # Evaluation on row r
                if not is_correct:
                    # Wrong match (X for ~1.2s)
                    steps.append(TimelineStep("try_wrong", item_idx=k, target_row=r, duration_sec=1.2))
                else:
                    # Right match (tick for ~1.5s)
                    steps.append(TimelineStep("try_correct", item_idx=k, target_row=k, duration_sec=1.5))
        else:
            # Last item (k == 0): "lands on the right one straight away"
            steps.append(TimelineStep("slide_in", item_idx=0, target_row=0, duration_sec=0.7))
            steps.append(TimelineStep("try_correct", item_idx=0, target_row=0, duration_sec=1.5))
            
    # 3. Final hold on finished stack ~1.3s
    steps.append(TimelineStep("final_hold", item_idx=-1, target_row=-1, duration_sec=1.3))
    
    # Assign start and end frame numbers
    curr_frame = 0
    for s in steps:
        s.start_frame = curr_frame
        frame_count = int(round(s.duration_sec * FPS))
        s.end_frame = curr_frame + frame_count
        curr_frame = s.end_frame
        
    total_frames = curr_frame
    return steps, total_frames

# --- Video Renderer ---

def generate_video(
    items,                  # List of item dicts: [{"name": ..., "left": ..., "right": ...}] (3 or 4)
    background_path,        # Background image path
    symbols_dir,            # Symbols folder
    output_path,            # Destination mp4 path
    audio_mode="builtin",   # "builtin", "custom", or "mute"
    custom_audio_path=None, # Path to custom mp3/wav if audio_mode == "custom"
    music_volume=0.5,       # 0.0 to 1.0
    progress_callback=None  # Optional callback fn(fraction, status_text)
):
    """
    Renders the complete 'Match the Halves' video to output_path.
    """
    num_items = len(items)
    if num_items not in (3, 4):
        raise ValueError(f"Expected 3 or 4 items, got {num_items}.")
        
    ffmpeg_ok, ffmpeg_msg = check_ffmpeg()
    if not ffmpeg_ok:
        raise RuntimeError(ffmpeg_msg)

    # 1. Determine Layout Geometry
    if num_items == 3:
        half_w = 280
        half_h = 560
        x_left = 140
        x_seam = 140 + half_w  # 420
        x_right = x_seam        # 420
        y_top = 40
        y_gap = 40
        row_y = [y_top + i * (half_h + y_gap) for i in range(3)]
        sym_size = 180
        sym_x = 810
    else: # 4 items
        half_w = 220
        half_h = 440
        x_left = 160
        x_seam = 160 + half_w  # 380
        x_right = x_seam        # 380
        y_top = 30
        y_gap = 30
        row_y = [y_top + i * (half_h + y_gap) for i in range(4)]
        sym_size = 150
        sym_x = 810
        
    sym_y = [row_y[i] + (half_h - sym_size) // 2 for i in range(num_items)]

    if progress_callback:
        progress_callback(0.05, "Loading and resizing assets...")

    # 2. Preload & Resize Assets
    bg_img = prepare_background(background_path, CANVAS_WIDTH, CANVAS_HEIGHT)
    
    left_imgs = [prepare_half(it["left"], half_w, half_h) for it in items]
    right_imgs = [prepare_half(it["right"], half_w, half_h) for it in items]
    
    correct_sym_path, wrong_sym_path = discover_symbols(symbols_dir)
    tick_img = prepare_symbol(correct_sym_path, draw_builtin_tick, sym_size)
    cross_img = prepare_symbol(wrong_sym_path, draw_builtin_cross, sym_size)
    
    # 3. Build Timeline
    steps, total_frames = build_timeline(num_items)
    total_seconds = total_frames / float(FPS)

    # 4. Synthesize Audio Track (if not mute)
    temp_wav_path = None
    if audio_mode != "mute":
        if progress_callback:
            progress_callback(0.12, "Composing audio track...")
            
        n_samples = int(total_seconds * SAMPLE_RATE)
        mix_buffer = np.zeros(n_samples, dtype=np.float32)
        
        # Bed
        if audio_mode == "builtin":
            bed = synth_music_box_bed(total_seconds, SAMPLE_RATE)
            mix_audio_track(mix_buffer, bed, 0, volume=1.0)
        elif audio_mode == "custom":
            if not custom_audio_path or not os.path.exists(custom_audio_path):
                raise ValueError("Custom audio file not found or not specified.")
            user_bed = load_user_music(custom_audio_path, total_seconds, SAMPLE_RATE)
            mix_audio_track(mix_buffer, user_bed, 0, volume=float(music_volume))
            
        # SFX
        pop_sfx = synth_pop_sfx(SAMPLE_RATE)
        buzz_sfx = synth_buzz_sfx(SAMPLE_RATE)
        ding_sfx = synth_ding_sfx(SAMPLE_RATE)
        
        for s in steps:
            t_sec = s.start_frame / float(FPS)
            sample_pos = int(t_sec * SAMPLE_RATE)
            if s.step_type in ("slide_in", "move_row"):
                # Pop triggers at landing (end of motion)
                land_pos = int((s.end_frame / float(FPS)) * SAMPLE_RATE)
                mix_audio_track(mix_buffer, pop_sfx, land_pos, volume=1.0)
            elif s.step_type == "try_wrong":
                mix_audio_track(mix_buffer, buzz_sfx, sample_pos, volume=1.0)
            elif s.step_type == "try_correct":
                mix_audio_track(mix_buffer, ding_sfx, sample_pos, volume=1.0)

        # Normalize and clamp audio to 16-bit PCM
        max_val = np.max(np.abs(mix_buffer))
        if max_val > 0.95:
            mix_buffer = mix_buffer / max_val * 0.95
            
        stereo = np.column_stack((mix_buffer, mix_buffer))
        int_audio = (stereo * 32767).astype(np.int16)
        
        temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_wav_path = temp_wav.name
        temp_wav.close()
        
        with wave.open(temp_wav_path, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(int_audio.tobytes())

    # 5. Launch FFmpeg Process
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-loglevel", "error",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{CANVAS_WIDTH}x{CANVAS_HEIGHT}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-"
    ]
    if temp_wav_path and os.path.exists(temp_wav_path):
        ffmpeg_cmd.extend([
            "-i", temp_wav_path,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path
        ])
    else:
        # Mute mode: Strictly NO audio stream
        ffmpeg_cmd.extend([
            "-an",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            output_path
        ])

    stderr_temp = tempfile.TemporaryFile()
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=stderr_temp)

    try:
        # 6. Render Frames
        finished_rows = set()
        
        for f_idx in range(total_frames):
            # Locate active timeline step
            active_step = None
            for s in steps:
                if s.start_frame <= f_idx < s.end_frame:
                    active_step = s
                    break
            if active_step is None:
                active_step = steps[-1]

            # Start with background
            frame_img = bg_img.copy()

            # A. Draw Stack Left Halves
            if active_step.step_type == "intro":
                # Stack slides in from left during intro
                prog = (f_idx - active_step.start_frame) / float(active_step.end_frame - active_step.start_frame)
                eased = ease_out_cubic(min(max(prog, 0.0), 1.0))
                curr_left_x = int(-half_w + (x_left - (-half_w)) * eased)
            else:
                curr_left_x = x_left
                
            for r in range(num_items):
                frame_img.paste(left_imgs[r], (curr_left_x, row_y[r]), left_imgs[r])

            # B. Draw Finished Items (Stay Whole)
            for r in finished_rows:
                # Right half firmly in place
                frame_img.paste(right_imgs[r], (x_right, row_y[r]), right_imgs[r])

            # C. Draw Active Right Half (if in motion or evaluation)
            st = active_step.step_type
            if st == "slide_in":
                # Slides in from right (CANVAS_WIDTH -> x_right) at target_row
                prog = (f_idx - active_step.start_frame) / float(active_step.end_frame - active_step.start_frame)
                eased = ease_out_cubic(min(max(prog, 0.0), 1.0))
                cur_x = int(CANVAS_WIDTH + (x_right - CANVAS_WIDTH) * eased)
                cur_y = row_y[active_step.target_row]
                it_idx = active_step.item_idx
                frame_img.paste(right_imgs[it_idx], (cur_x, cur_y), right_imgs[it_idx])
                
            elif st == "move_row":
                # Moves from from_row to target_row at x_right
                prog = (f_idx - active_step.start_frame) / float(active_step.end_frame - active_step.start_frame)
                eased = ease_in_out_quad(min(max(prog, 0.0), 1.0))
                y_start = row_y[active_step.from_row]
                y_end = row_y[active_step.target_row]
                cur_y = int(y_start + (y_end - y_start) * eased)
                it_idx = active_step.item_idx
                frame_img.paste(right_imgs[it_idx], (x_right, cur_y), right_imgs[it_idx])
                
            elif st in ("try_wrong", "try_correct"):
                # Resting on target_row
                cur_y = row_y[active_step.target_row]
                it_idx = active_step.item_idx
                frame_img.paste(right_imgs[it_idx], (x_right, cur_y), right_imgs[it_idx])
                
                # Overlay Symbol (pop in with overshoot, fade out at end)
                step_len = float(active_step.end_frame - active_step.start_frame)
                local_f = f_idx - active_step.start_frame
                
                # Pop-in takes 7 frames (~0.23s)
                pop_frames = 7
                fade_frames = 7
                scale = 1.0
                alpha = 1.0
                
                if local_f < pop_frames:
                    scale = symbol_overshoot_scale(local_f / float(pop_frames))
                elif local_f >= (step_len - fade_frames):
                    alpha = max(0.0, (step_len - local_f) / float(fade_frames))
                    
                sym_base = cross_img if st == "try_wrong" else tick_img
                if scale > 0.05 and alpha > 0.05:
                    w_scaled = int(sym_size * scale)
                    h_scaled = int(sym_size * scale)
                    if w_scaled > 0 and h_scaled > 0:
                        sym_curr = sym_base.resize((w_scaled, h_scaled), Image.Resampling.BILINEAR)
                        if alpha < 0.99:
                            # Apply alpha fade
                            arr = np.array(sym_curr).astype(np.float32)
                            arr[:, :, 3] *= alpha
                            sym_curr = Image.fromarray(arr.astype(np.uint8))
                        # Center symbol in symbol slot
                        cx = sym_x + (sym_size - w_scaled) // 2
                        cy = sym_y[active_step.target_row] + (sym_size - h_scaled) // 2
                        frame_img.paste(sym_curr, (cx, cy), sym_curr)
                        
                # If this was a correct try and we reach the end of the step, mark row finished
                if st == "try_correct" and (f_idx == active_step.end_frame - 1):
                    finished_rows.add(active_step.target_row)

            # Write raw RGB bytes to ffmpeg
            raw_rgb = frame_img.tobytes()
            proc.stdin.write(raw_rgb)

            # Update progress
            if progress_callback and f_idx % 15 == 0:
                fraction = 0.15 + 0.80 * (f_idx / float(total_frames))
                progress_callback(fraction, f"Rendering video frames ({f_idx + 1}/{total_frames})...")

        proc.stdin.close()
        proc.wait()
        
        stderr_temp.seek(0)
        stderr_output = stderr_temp.read()
        stderr_temp.close()
        
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg encoding failed (exit code {proc.returncode}):\n{stderr_output.decode('utf-8', errors='ignore')}")

        if progress_callback:
            progress_callback(1.0, "Video generated successfully!")

    finally:
        try:
            stderr_temp.close()
        except Exception:
            pass
        # Clean up temporary audio file
        if temp_wav_path and os.path.exists(temp_wav_path):
            try:
                os.remove(temp_wav_path)
            except Exception:
                pass
