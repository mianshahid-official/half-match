"""
Odd One Out — Kids Video Generator (Standalone CLI Renderer).

Turns image halves in sets/ into viral "Odd One Out" 2x2 grid quiz videos:
- 1080x1920, 30fps, H.264 + AAC MP4
- Configurable number of rounds (--rounds N, default: 5)
- Configurable wait time between reveals (--wait-time SECONDS, default: 5.0)
- Configurable reveal duration (--reveal-time SECONDS, default: 2.0)
- Enhanced viral kids graphics: vibrant typography, drop shadows, glowing badges, gradient timer
- Purely synthesized audio bed + landing pop / countdown ticks / reveal ding / fanfare SFX
"""

import os
import sys
import re
import math
import random
import shutil
import tempfile
import argparse
import subprocess
import wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# =====================================================================
# EDITABLE ROUNDS LIST (used with --sample flag)
# =====================================================================
ROUNDS = [
    # Round 1: 3 fruits + 1 vegetable (Carrot is a VEGETABLE!)
    {
        "majority_cat": "fruits",
        "majority_items": ["apple", "banana", "orange"],
        "odd_cat": "vegetables",
        "odd_item": "carrot",
        "odd_pos": 1
    },
    # Round 2: 3 cars + 1 fruit (Strawberry is a FRUIT!)
    {
        "majority_cat": "cars",
        "majority_items": ["sports_car", "taxi", "bus"],
        "odd_cat": "fruits",
        "odd_item": "strawberry",
        "odd_pos": 2
    },
    # Round 3: 3 vegetables + 1 fruit (Banana is a FRUIT!)
    {
        "majority_cat": "vegetables",
        "majority_items": ["broccoli", "cauliflower", "eggplant"],
        "odd_cat": "fruits",
        "odd_item": "banana",
        "odd_pos": 0
    },
    # Round 4: 3 characters + 1 car (Ferrari is a CAR!)
    {
        "majority_cat": "characters",
        "majority_items": ["patlu", "chhota_bheem", "shin_chan"],
        "odd_cat": "cars",
        "odd_item": "ferrari",
        "odd_pos": 3
    },
    # Round 5: 3 fruits + 1 vegetable (Corn is a VEGETABLE!)
    {
        "majority_cat": "fruits",
        "majority_items": ["banana", "mango", "lemon"],
        "odd_cat": "vegetables",
        "odd_item": "corn",
        "odd_pos": 1
    }
]

# Required Category Word Mapping
CATEGORY_WORD_MAP = {
    "fruits": "FRUIT",
    "fruit": "FRUIT",
    "vegetables": "VEGETABLE",
    "vegetable": "VEGETABLE",
    "cars": "CAR",
    "car": "CAR",
    "characters": "CHARACTER",
    "character": "CHARACTER"
}

# Canvas & Render Constants
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
FPS = 30
SAMPLE_RATE = 44100

INTRO_DURATION_SEC = 2.0
DEFAULT_WAIT_TIME_SEC = 5.0
DEFAULT_REVEAL_TIME_SEC = 2.0
END_DURATION_SEC = 2.5

# 2x2 Grid Layout
CELL_SIZE = 440
GRID_POSITIONS = [
    (60, 280),   # 0 = top-left
    (580, 280),  # 1 = top-right
    (60, 780),   # 2 = bottom-left
    (580, 780)   # 3 = bottom-right
]

def check_ffmpeg():
    """Checks if ffmpeg is available on PATH."""
    path = shutil.which("ffmpeg")
    if path:
        return True
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False

def get_font(size):
    """Fallback chain for bold font."""
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()

def draw_text_with_shadow(draw, text, xy, font, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), outline_width=4, shadow_offset=(3, 4), shadow_color=(0, 0, 0, 180), anchor="mm"):
    """
    Renders punchy cartoon-style typography with drop shadow and outline.
    """
    x, y = xy
    sx, sy = shadow_offset
    # Draw drop shadow
    if shadow_color:
        draw.text((x + sx, y + sy), text, font=font, fill=shadow_color, stroke_width=outline_width, stroke_fill=shadow_color, anchor=anchor)
    # Draw main text with outline
    draw.text((x, y), text, font=font, fill=fill, stroke_width=outline_width, stroke_fill=outline, anchor=anchor)

def rejoin_halves(left_path, right_path):
    """
    Rejoins left and right halves side by side into a single full image.
    Left+right rejoin pixel-identically to the full picture.
    """
    l_img = Image.open(left_path).convert("RGBA")
    r_img = Image.open(right_path).convert("RGBA")
    w = l_img.width + r_img.width
    h = max(l_img.height, r_img.height)
    full = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    full.paste(l_img, (0, 0))
    full.paste(r_img, (l_img.width, 0))
    return full

def format_slug_name(slug):
    """Converts a slug like 'sports_car' or 'chhota-bheem' to 'Sports Car'."""
    clean = slug.replace("-", " ").replace("_", " ")
    return clean.title()

def get_category_word(cat_name):
    """Maps category to required singular uppercase word."""
    cat_lower = cat_name.lower().strip()
    if cat_lower in CATEGORY_WORD_MAP:
        return CATEGORY_WORD_MAP[cat_lower]
    if cat_lower.endswith("s"):
        return cat_lower[:-1].upper()
    return cat_lower.upper()

def discover_categories(sets_dir="sets"):
    """
    Dynamically discovers category subfolders and valid complete pairs.
    Skips empty categories and warns on unpaired halves.
    """
    categories = {}
    if not os.path.exists(sets_dir):
        print(f"[Warning] Sets folder '{sets_dir}' not found.")
        return categories

    valid_exts = {".png", ".jpg", ".jpeg", ".webp"}
    subdirs = [d for d in os.listdir(sets_dir) if os.path.isdir(os.path.join(sets_dir, d))]

    for sub in sorted(subdirs):
        cat_path = os.path.join(sets_dir, sub)
        # Scan files directly in category folder
        try:
            files = [f for f in os.listdir(cat_path) if os.path.isfile(os.path.join(cat_path, f))]
        except Exception:
            continue

        left_files = {}
        right_files = {}

        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in valid_exts:
                continue
            base = os.path.splitext(f)[0]
            m_num = re.match(r"^(.*?)-(1|2)$", base, re.IGNORECASE)
            if m_num:
                name, part = m_num.group(1), m_num.group(2)
                if part == "1":
                    left_files[name] = os.path.join(cat_path, f)
                else:
                    right_files[name] = os.path.join(cat_path, f)
                continue
            m_side = re.match(r"^(.*?)-(left|right)$", base, re.IGNORECASE)
            if m_side:
                name, part = m_side.group(1), m_side.group(2).lower()
                if part == "left":
                    left_files[name] = os.path.join(cat_path, f)
                else:
                    right_files[name] = os.path.join(cat_path, f)
                continue

        pairs = []
        all_items = sorted(set(left_files.keys()).union(set(right_files.keys())))
        for item in all_items:
            has_l = item in left_files
            has_r = item in right_files
            if has_l and has_r:
                pairs.append({
                    "name": item,
                    "left": left_files[item],
                    "right": right_files[item]
                })
            else:
                missing = "right" if has_l else "left"
                present_file = os.path.basename(left_files[item] if has_l else right_files[item])
                print(f"[Warning] Category '{sub}': item '{item}' ({present_file}) has no {missing} partner and was skipped.")

        if pairs:
            categories[sub] = pairs

    return categories

def prepare_background(bg_path, target_w=CANVAS_WIDTH, target_h=CANVAS_HEIGHT):
    """
    Center-crops any background (e.g. 1600x1600 or 1080x1920) to 9:16
    and resizes to 1080x1920.
    """
    if bg_path and os.path.exists(bg_path):
        try:
            im = Image.open(bg_path).convert("RGB")
            bw, bh = im.size
            target_ratio = target_w / target_h
            cur_ratio = bw / bh
            if cur_ratio > target_ratio:
                crop_w = int(bh * target_ratio)
                left = (bw - crop_w) // 2
                im = im.crop((left, 0, left + crop_w, bh))
            else:
                crop_h = int(bw / target_ratio)
                top = (bh - crop_h) // 2
                im = im.crop((0, top, bw, top + crop_h))
            return im.resize((target_w, target_h), Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"[Warning] Failed to load background '{bg_path}': {e}")

    # Fallback vibrant sunset sky kids background
    bg = Image.new("RGB", (target_w, target_h))
    arr = np.zeros((target_h, target_w, 3), dtype=np.uint8)
    for y in range(target_h):
        t = y / float(target_h)
        arr[y, :, 0] = int((1 - t) * 79 + t * 30)
        arr[y, :, 1] = int((1 - t) * 70 + t * 58)
        arr[y, :, 2] = int((1 - t) * 229 + t * 138)
    return Image.fromarray(arr)

def prepare_grid_item_card(rejoined_img, cell_size=CELL_SIZE, is_dimmed=False):
    """
    Renders an item inside a 440x440 glossy rounded card with drop shadow.
    If is_dimmed=True, applies a semi-transparent darkening overlay so the item
    remains clearly visible through the dimming.
    """
    card = Image.new("RGBA", (cell_size, cell_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    # Card backing
    draw.rounded_rectangle(
        [0, 0, cell_size - 1, cell_size - 1],
        radius=26,
        fill=(255, 255, 255, 230),
        outline=(255, 255, 255, 255),
        width=3
    )

    # Scale item with padding
    pad = 28
    max_dim = cell_size - pad * 2
    item_copy = rejoined_img.copy()
    item_copy.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    # Center inside card
    ox = (cell_size - item_copy.width) // 2
    oy = (cell_size - item_copy.height) // 2
    card.paste(item_copy, (ox, oy), item_copy)

    if is_dimmed:
        dim_layer = Image.new("RGBA", (cell_size, cell_size), (0, 0, 0, 0))
        d_dim = ImageDraw.Draw(dim_layer)
        d_dim.rounded_rectangle([0, 0, cell_size - 1, cell_size - 1], radius=26, fill=(15, 23, 42, 160))
        card = Image.alpha_composite(card, dim_layer)

    return card

def draw_green_tick_badge(size=80):
    """Creates a circular green badge with drop shadow and checkmark."""
    badge = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    # Circle
    draw.ellipse([2, 2, size - 3, size - 3], fill=(34, 197, 94, 255), outline=(255, 255, 255, 255), width=4)
    # Checkmark
    p1 = (int(size * 0.28), int(size * 0.52))
    p2 = (int(size * 0.44), int(size * 0.68))
    p3 = (int(size * 0.72), int(size * 0.32))
    draw.line([p1, p2, p3], fill=(255, 255, 255, 255), width=int(size * 0.12), joint="curve")
    return badge

# =====================================================================
# AUDIO SYNTHESIS & ZERO-LEAK CLAMPED MIXER
# =====================================================================

def mix_audio(buffer, sfx, start_idx, volume=1.0):
    """Mixes sfx into buffer with strict boundary clamping."""
    if start_idx < 0 or start_idx >= len(buffer):
        return
    end_idx = min(start_idx + len(sfx), len(buffer))
    count = end_idx - start_idx
    if count > 0:
        buffer[start_idx:end_idx] += sfx[:count] * volume

def synth_pop_sfx(sample_rate=SAMPLE_RATE):
    """Pop sound when items appear (~0.08s)."""
    dur = 0.08
    n = int(dur * sample_rate)
    t = np.linspace(0, dur, n, endpoint=False)
    freq = 680.0 - 500.0 * (t / dur)
    phase = 2 * np.pi * np.cumsum(freq) / sample_rate
    env = np.exp(-t * 36.0)
    return (0.7 * np.sin(phase) * env).astype(np.float32)

def synth_tick_sfx(sample_rate=SAMPLE_RATE):
    """Sharp clock tick for each countdown second (~0.04s)."""
    dur = 0.04
    n = int(dur * sample_rate)
    t = np.linspace(0, dur, n, endpoint=False)
    click = np.sin(2 * np.pi * 1800.0 * t) * np.exp(-t * 90.0)
    noise = (np.random.rand(n) * 2 - 1) * np.exp(-t * 120.0) * 0.3
    return ((click + noise) * 0.65).astype(np.float32)

def synth_ding_sfx(sample_rate=SAMPLE_RATE):
    """Bright bell chime on reveal (~0.8s)."""
    dur = 0.80
    n = int(dur * sample_rate)
    t = np.linspace(0, dur, n, endpoint=False)
    c6 = 0.50 * np.sin(2 * np.pi * 1046.5 * t) * np.exp(-t * 4.0)
    c7 = 0.35 * np.sin(2 * np.pi * 2093.0 * t) * np.exp(-t * 6.5)
    g7 = 0.15 * np.sin(2 * np.pi * 3136.0 * t) * np.exp(-t * 9.0)
    return ((c6 + c7 + g7) * 0.85).astype(np.float32)

def synth_fanfare_sfx(sample_rate=SAMPLE_RATE):
    """Short triumphant celebration fanfare on the end card (~1.6s)."""
    dur = 1.6
    n = int(dur * sample_rate)
    out = np.zeros(n, dtype=np.float32)
    notes = [
        (0.00, 392.00, 0.14),
        (0.14, 523.25, 0.14),
        (0.28, 659.25, 0.14),
        (0.42, 783.99, 0.22),
        (0.64, 1046.50, 0.90),
        (0.64, 1318.51, 0.90),
        (0.64, 1567.98, 0.90),
    ]
    for start_t, freq, note_dur in notes:
        start_idx = int(start_t * sample_rate)
        sub_n = int(note_dur * sample_rate)
        t = np.linspace(0, note_dur, sub_n, endpoint=False)
        tone = (np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(4 * np.pi * freq * t)) * np.exp(-t * 3.5)
        mix_audio(out, tone.astype(np.float32), start_idx, volume=0.45)
    return out

def synth_music_bed(total_sec, sample_rate=SAMPLE_RATE):
    """
    Gentle music-box melody loop + grounding low bass note.
    """
    n = int(total_sec * sample_rate)
    bed = np.zeros(n, dtype=np.float32)

    chord_bass = [65.41, 49.00, 55.00, 43.65] # C2, G1, A1, F1
    arpeggio = [
        [523.25, 659.25, 783.99, 1046.50], # C5, E5, G5, C6
        [392.00, 587.33, 783.99, 987.77],  # G4, D5, G5, B5
        [440.00, 523.25, 659.25, 880.00],  # A4, C5, E5, A5
        [349.23, 440.00, 523.25, 698.46],  # F4, A4, C5, F5
    ]
    chord_len = 2.0
    note_len = 0.50

    total_chords = int(math.ceil(total_sec / chord_len)) + 1
    for c_i in range(total_chords):
        idx = c_i % 4
        c_start = c_i * chord_len
        if c_start >= total_sec:
            break

        # Grounding low bass note
        bass_freq = chord_bass[idx]
        b_n = int(chord_len * sample_rate)
        t_b = np.linspace(0, chord_len, b_n, endpoint=False)
        bass_tone = (0.35 * np.sin(2 * np.pi * bass_freq * t_b) + 0.15 * np.sin(4 * np.pi * bass_freq * t_b)) * np.exp(-t_b * 1.2)
        mix_audio(bed, bass_tone.astype(np.float32), int(c_start * sample_rate), volume=0.45)

        # Arpeggio notes
        for n_i, freq in enumerate(arpeggio[idx]):
            n_start = c_start + n_i * note_len
            if n_start >= total_sec:
                break
            s_n = int(0.70 * sample_rate)
            t_s = np.linspace(0, 0.70, s_n, endpoint=False)
            celesta = (0.5 * np.sin(2 * np.pi * freq * t_s) + 0.25 * np.sin(4 * np.pi * freq * t_s) + 0.1 * np.sin(6 * np.pi * freq * t_s)) * np.exp(-t_s * 5.0)
            mix_audio(bed, celesta.astype(np.float32), int(n_start * sample_rate), volume=0.35)

    return bed

# =====================================================================
# ROUND STRUCTURING
# =====================================================================

def build_random_rounds(categories, count=5):
    """
    Builds N random rounds:
    - 3 from majority category + 1 from different category
    - Shuffles odd item's position (0..3) ensuring no repeat on consecutive rounds.
    """
    eligible_majority = [c for c, items in categories.items() if len(items) >= 3]
    if not eligible_majority:
        raise ValueError("Cannot build rounds: Need at least one category with >= 3 items.")

    rounds_data = []
    last_pos = -1

    for _ in range(count):
        maj_cat = random.choice(eligible_majority)
        other_cats = [c for c in categories.keys() if c != maj_cat and len(categories[c]) >= 1]
        if not other_cats:
            raise ValueError(f"Need at least 2 distinct non-empty categories to create an Odd One Out round (only '{maj_cat}' available).")
        odd_cat = random.choice(other_cats)

        # Pick 3 items from majority category, 1 from odd
        maj_items = random.sample(categories[maj_cat], 3)
        odd_item = random.choice(categories[odd_cat])

        # Pick position (0..3) different from last position
        available_positions = [p for p in [0, 1, 2, 3] if p != last_pos]
        odd_pos = random.choice(available_positions)
        last_pos = odd_pos

        rounds_data.append({
            "maj_cat": maj_cat,
            "maj_items": maj_items,
            "odd_cat": odd_cat,
            "odd_item": odd_item,
            "odd_pos": odd_pos
        })

    return rounds_data

def build_sample_rounds(categories):
    """Builds rounds from the editable ROUNDS list, with graceful fallback."""
    rounds_data = []
    last_pos = -1

    for r in ROUNDS:
        m_cat = r["majority_cat"]
        o_cat = r["odd_cat"]

        if m_cat in categories and o_cat in categories:
            cat_map_m = {it["name"]: it for it in categories[m_cat]}
            cat_map_o = {it["name"]: it for it in categories[o_cat]}

            maj_items = [cat_map_m[name] for name in r["majority_items"] if name in cat_map_m]
            odd_item = cat_map_o.get(r["odd_item"])

            if len(maj_items) < 3 and len(categories[m_cat]) >= 3:
                maj_items = categories[m_cat][:3]
            if not odd_item and categories[o_cat]:
                odd_item = categories[o_cat][0]

            if len(maj_items) == 3 and odd_item:
                pos = r.get("odd_pos")
                if pos is None or pos == last_pos:
                    pos = random.choice([p for p in [0, 1, 2, 3] if p != last_pos])
                last_pos = pos
                rounds_data.append({
                    "maj_cat": m_cat,
                    "maj_items": maj_items,
                    "odd_cat": o_cat,
                    "odd_item": odd_item,
                    "odd_pos": pos
                })
                continue

        fallback_r = build_random_rounds(categories, count=1)[0]
        rounds_data.append(fallback_r)

    return rounds_data

# =====================================================================
# VIDEO GENERATION ENGINE
# =====================================================================

def render_odd_one_out_video(rounds, bg_path, output_path="odd-one-out.mp4", wait_time_sec=DEFAULT_WAIT_TIME_SEC, reveal_time_sec=DEFAULT_REVEAL_TIME_SEC, progress_cb=None):
    """
    Renders the complete Odd One Out video with configurable wait and reveal timing.
    """
    if not check_ffmpeg():
        print("\n[ERROR] FFmpeg is missing from your system PATH!")
        print("Install FFmpeg with:")
        print("  winget install Gyan.FFmpeg")
        print("or download from https://www.gyan.dev/ffmpeg/builds/\n")
        sys.exit(1)

    num_rounds = len(rounds)
    round_duration_sec = float(wait_time_sec) + float(reveal_time_sec)
    total_sec = INTRO_DURATION_SEC + (num_rounds * round_duration_sec) + END_DURATION_SEC
    total_frames = int(round(total_sec * FPS))

    if progress_cb:
        progress_cb(0.05, "Preloading assets and preparing cards...")

    # Load Background
    bg_img = prepare_background(bg_path)

    # Preload and rejoin all round items
    tick_badge = draw_green_tick_badge(84)
    rounds_prepared = []

    for r in rounds:
        grid_items = [None] * 4
        # Place odd item
        odd_full = rejoin_halves(r["odd_item"]["left"], r["odd_item"]["right"])
        grid_items[r["odd_pos"]] = {
            "name": r["odd_item"]["name"],
            "cat": r["odd_cat"],
            "full": odd_full,
            "is_odd": True
        }

        # Place majority items in other 3 positions
        maj_idx = 0
        for p in range(4):
            if p != r["odd_pos"]:
                m_it = r["maj_items"][maj_idx]
                m_full = rejoin_halves(m_it["left"], m_it["right"])
                grid_items[p] = {
                    "name": m_it["name"],
                    "cat": r["maj_cat"],
                    "full": m_full,
                    "is_odd": False
                }
                maj_idx += 1

        cards_normal = [prepare_grid_item_card(it["full"], CELL_SIZE, is_dimmed=False) for it in grid_items]
        cards_dimmed = [prepare_grid_item_card(it["full"], CELL_SIZE, is_dimmed=True) for it in grid_items]

        odd_display_name = format_slug_name(r["odd_item"]["name"])
        odd_cat_word = get_category_word(r["odd_cat"])
        reason_text = f"{odd_display_name} is a {odd_cat_word}!"

        rounds_prepared.append({
            "grid_items": grid_items,
            "cards_normal": cards_normal,
            "cards_dimmed": cards_dimmed,
            "odd_pos": r["odd_pos"],
            "odd_name": odd_display_name,
            "odd_cat_word": odd_cat_word,
            "reason_text": reason_text
        })

    # -------------------------------------------------------------
    # Synthesize Audio Track
    # -------------------------------------------------------------
    if progress_cb:
        progress_cb(0.12, "Composing synthesized soundtrack & SFX...")

    audio_mix = synth_music_bed(total_sec, SAMPLE_RATE)

    pop_sfx = synth_pop_sfx(SAMPLE_RATE)
    tick_sfx = synth_tick_sfx(SAMPLE_RATE)
    ding_sfx = synth_ding_sfx(SAMPLE_RATE)
    fanfare_sfx = synth_fanfare_sfx(SAMPLE_RATE)

    # Schedule SFX across timeline
    for r_idx in range(num_rounds):
        round_start_t = INTRO_DURATION_SEC + (r_idx * round_duration_sec)

        # Pop when items appear
        mix_audio(audio_mix, pop_sfx, int(round_start_t * SAMPLE_RATE), volume=0.85)

        # Countdown ticks for each second of wait_time
        num_ticks = int(math.floor(wait_time_sec))
        for s in range(num_ticks):
            t_tick = round_start_t + s
            mix_audio(audio_mix, tick_sfx, int(t_tick * SAMPLE_RATE), volume=0.75)

        # Ding on reveal
        t_reveal = round_start_t + wait_time_sec
        mix_audio(audio_mix, ding_sfx, int(t_reveal * SAMPLE_RATE), volume=1.0)

    # Fanfare on end card
    end_card_t = INTRO_DURATION_SEC + (num_rounds * round_duration_sec)
    mix_audio(audio_mix, fanfare_sfx, int(end_card_t * SAMPLE_RATE), volume=1.0)

    # Normalize audio cleanly below 0 dB
    max_amp = np.max(np.abs(audio_mix))
    if max_amp > 0:
        target_peak = 0.88 # -1.1 dBFS
        audio_mix = (audio_mix / max_amp) * target_peak

    stereo_audio = np.column_stack((audio_mix, audio_mix))
    int16_audio = (stereo_audio * 32767).astype(np.int16)

    temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_wav_path = temp_wav.name
    temp_wav.close()

    with wave.open(temp_wav_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(int16_audio.tobytes())

    # -------------------------------------------------------------
    # Launch FFmpeg Streaming Process
    # -------------------------------------------------------------
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-loglevel", "error",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{CANVAS_WIDTH}x{CANVAS_HEIGHT}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-",
        "-i", temp_wav_path,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        output_path
    ]

    stderr_temp = tempfile.TemporaryFile()
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=stderr_temp)

    # High-impact fonts
    font_main_title = get_font(72)
    font_sub_title = get_font(44)
    font_note = get_font(38)

    font_header_title = get_font(58)
    font_badge = get_font(38)
    font_question = get_font(48)
    font_countdown = get_font(120)
    font_reason_main = get_font(52)

    try:
        intro_end_frame = int(round(INTRO_DURATION_SEC * FPS))
        round_len_frames = int(round(round_duration_sec * FPS))
        guess_len_frames = int(round(wait_time_sec * FPS))

        for f in range(total_frames):
            frame = bg_img.copy()
            draw = ImageDraw.Draw(frame)

            # ---------------------------------------------------------
            # 1. INTRO CARD (0.0s to 2.0s)
            # ---------------------------------------------------------
            if f < intro_end_frame:
                # Translucent dark glassmorphic card with gradient border
                draw.rounded_rectangle([90, 520, 990, 1160], radius=36, fill=(15, 23, 42, 230), outline=(56, 189, 248, 255), width=5)
                # Inner decorative glow
                draw.rounded_rectangle([102, 532, 978, 1148], radius=28, outline=(14, 165, 233, 100), width=2)

                draw_text_with_shadow(draw, "ODD ONE OUT", (540, 660), font_main_title, fill=(255, 255, 255), outline=(15, 23, 42), outline_width=6)
                draw_text_with_shadow(draw, "Can you spot it?", (540, 800), font_sub_title, fill=(253, 224, 71), outline=(15, 23, 42), outline_width=5)
                
                # Pill indicator for rounds
                draw.rounded_rectangle([240, 915, 840, 1005], radius=26, fill=(30, 41, 59, 240), outline=(250, 204, 21, 255), width=3)
                draw_text_with_shadow(draw, f"{num_rounds} Rounds — Comment Score!", (540, 960), font_note, fill=(248, 250, 252), outline=(15, 23, 42), outline_width=4)

            # ---------------------------------------------------------
            # 2. END CARD (Last 2.5s)
            # ---------------------------------------------------------
            elif f >= (total_frames - int(round(END_DURATION_SEC * FPS))):
                draw.rounded_rectangle([90, 520, 990, 1160], radius=36, fill=(15, 23, 42, 235), outline=(34, 197, 94, 255), width=5)
                draw.rounded_rectangle([102, 532, 978, 1148], radius=28, outline=(74, 222, 128, 100), width=2)

                draw_text_with_shadow(draw, "How many did you get?", (540, 660), font_main_title, fill=(255, 255, 255), outline=(15, 23, 42), outline_width=6)
                draw_text_with_shadow(draw, "Comment your score!", (540, 810), font_sub_title, fill=(250, 204, 21), outline=(15, 23, 42), outline_width=5)

                draw.rounded_rectangle([280, 925, 800, 1015], radius=26, fill=(30, 41, 59, 240), outline=(56, 189, 248, 255), width=3)
                draw_text_with_shadow(draw, "Follow for more!", (540, 970), font_note, fill=(56, 189, 248), outline=(15, 23, 42), outline_width=4)

            # ---------------------------------------------------------
            # 3. QUIZ ROUNDS
            # ---------------------------------------------------------
            else:
                round_f = f - intro_end_frame
                r_idx = min(int(round_f // round_len_frames), num_rounds - 1)
                f_in_round = int(round_f % round_len_frames)
                is_reveal = (f_in_round >= guess_len_frames)

                r_data = rounds_prepared[r_idx]

                # Top Title Banner
                draw_text_with_shadow(draw, "ODD ONE OUT", (540, 105), font_header_title, fill=(255, 255, 255), outline=(15, 23, 42), outline_width=5)

                # Round Pill Badge
                badge_w = 340
                badge_h = 58
                bx1 = 540 - badge_w // 2
                by1 = 160
                draw.rounded_rectangle([bx1, by1, bx1 + badge_w, by1 + badge_h], radius=22, fill=(15, 23, 42, 220), outline=(250, 204, 21, 255), width=3)
                draw_text_with_shadow(draw, f"ROUND {r_idx + 1} / {num_rounds}", (540, by1 + badge_h // 2), font_badge, fill=(253, 224, 71), outline=(15, 23, 42), outline_width=3)

                # Render 2x2 Grid with Soft Shadows
                for pos_idx in range(4):
                    gx, gy = GRID_POSITIONS[pos_idx]
                    is_odd_item = (pos_idx == r_data["odd_pos"])

                    # Draw soft card drop shadow
                    draw.rounded_rectangle([gx + 4, gy + 8, gx + CELL_SIZE + 4, gy + CELL_SIZE + 8], radius=28, fill=(0, 0, 0, 75))

                    if not is_reveal:
                        # Guess phase: all 4 cards appear normal
                        frame.paste(r_data["cards_normal"][pos_idx], (gx, gy), r_data["cards_normal"][pos_idx])
                    else:
                        # Reveal phase: highlight odd item, dim others
                        if is_odd_item:
                            frame.paste(r_data["cards_normal"][pos_idx], (gx, gy), r_data["cards_normal"][pos_idx])
                            # Outer soft glow ring
                            draw.rounded_rectangle([gx - 4, gy - 4, gx + CELL_SIZE + 3, gy + CELL_SIZE + 3], radius=30, outline=(74, 222, 128, 120), width=6)
                            # Inner thick vibrant green ring
                            draw.rounded_rectangle([gx, gy, gx + CELL_SIZE - 1, gy + CELL_SIZE - 1], radius=26, outline=(34, 197, 94, 255), width=10)
                            # Green tick badge
                            frame.paste(tick_badge, (gx + CELL_SIZE - 70, gy - 14), tick_badge)
                        else:
                            frame.paste(r_data["cards_dimmed"][pos_idx], (gx, gy), r_data["cards_dimmed"][pos_idx])

                # Bottom Controls
                if not is_reveal:
                    # Question Pill Banner
                    draw.rounded_rectangle([140, 1270, 940, 1365], radius=26, fill=(15, 23, 42, 225), outline=(56, 189, 248, 255), width=3)
                    draw_text_with_shadow(draw, "Which one is different?", (540, 1317), font_question, fill=(255, 255, 255), outline=(15, 23, 42), outline_width=4)

                    # Big Countdown Number (in circular glowing badge)
                    sec_elapsed = f_in_round / float(FPS)
                    total_countdown = max(1, int(wait_time_sec))
                    countdown_num = max(1, total_countdown - int(sec_elapsed))

                    draw.ellipse([460, 1385, 620, 1545], fill=(15, 23, 42, 235), outline=(250, 204, 21, 255), width=5)
                    draw_text_with_shadow(draw, str(countdown_num), (540, 1465), font_countdown, fill=(253, 224, 71), outline=(15, 23, 42), outline_width=6)

                    # Animated Shrinking Timer Bar
                    bar_w = 820
                    bar_h = 26
                    bar_x = 130
                    bar_y = 1575

                    time_left_frac = max(0.0, 1.0 - (f_in_round / float(guess_len_frames)))
                    fill_w = int(bar_w * time_left_frac)

                    # Outer bar track
                    draw.rounded_rectangle([bar_x - 3, bar_y - 3, bar_x + bar_w + 3, bar_y + bar_h + 3], radius=16, fill=(15, 23, 42, 220), outline=(71, 85, 105, 255), width=2)
                    if fill_w > 8:
                        if time_left_frac > 0.5:
                            bar_color = (34, 197, 94) # Green
                        elif time_left_frac > 0.25:
                            bar_color = (245, 158, 11) # Amber
                        else:
                            bar_color = (239, 68, 68) # Red
                        draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=13, fill=bar_color)

                else:
                    # Reveal Phase: Reason Card
                    draw.rounded_rectangle([70, 1340, 1010, 1550], radius=30, fill=(15, 23, 42, 235), outline=(34, 197, 94, 255), width=4)
                    draw.rounded_rectangle([82, 1352, 998, 1538], radius=22, outline=(74, 222, 128, 90), width=2)
                    
                    # Centered Reason Text
                    draw_text_with_shadow(draw, r_data["reason_text"], (540, 1445), font_reason_main, fill=(255, 255, 255), outline=(15, 23, 42), outline_width=5)

            # Stream raw frame to FFmpeg
            proc.stdin.write(frame.tobytes())

            if progress_cb and f % 30 == 0:
                frac = 0.15 + 0.80 * (f / float(total_frames))
                progress_cb(frac, f"Rendering frame {f + 1}/{total_frames} ({int(frac * 100)}%)...")

        proc.stdin.close()
        proc.wait()

        stderr_temp.seek(0)
        err_out = stderr_temp.read()
        stderr_temp.close()

        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg encoding failed (code {proc.returncode}):\n{err_out.decode('utf-8', errors='ignore')}")

        if progress_cb:
            progress_cb(1.0, f"Odd One Out video created: {output_path}")

    finally:
        try:
            stderr_temp.close()
        except Exception:
            pass
        if temp_wav_path and os.path.exists(temp_wav_path):
            try:
                os.remove(temp_wav_path)
            except Exception:
                pass

def main():
    parser = argparse.ArgumentParser(description="Odd One Out — Kids Video Generator")
    parser.add_argument("-r", "--rounds", type=int, default=None, help="Number of rounds (default: 5)")
    parser.add_argument("--random", type=int, default=None, help="Alias for --rounds N")
    parser.add_argument("-w", "--wait-time", type=float, default=DEFAULT_WAIT_TIME_SEC, help="Wait time before reveal in seconds (default: 5.0)")
    parser.add_argument("--guess-time", type=float, default=None, help="Alias for --wait-time")
    parser.add_argument("--reveal-time", type=float, default=DEFAULT_REVEAL_TIME_SEC, help="Reveal display duration in seconds (default: 2.0)")
    parser.add_argument("--sample", action="store_true", help="Use editable ROUNDS list at top of script")
    parser.add_argument("-b", "--background", default=None, help="Background image filename or path")
    parser.add_argument("-o", "--out", default="odd-one-out.mp4", help="Output MP4 file path (default: odd-one-out.mp4)")
    parser.add_argument("--sets", default="sets", help="Sets directory (default: sets)")
    args = parser.parse_args()

    # Determine rounds count
    num_rounds = 5
    if args.rounds is not None:
        num_rounds = args.rounds
    elif args.random is not None:
        num_rounds = args.random

    # Determine wait time
    wait_time = args.wait_time
    if args.guess_time is not None:
        wait_time = args.guess_time

    reveal_time = args.reveal_time

    print("==================================================")
    print("  ODD ONE OUT — Kids Video Generator")
    print("==================================================")
    print(f" • Rounds: {num_rounds}")
    print(f" • Wait Time (Guess Phase): {wait_time}s")
    print(f" • Reveal Time: {reveal_time}s")
    print(f" • Output File: {args.out}")

    if not check_ffmpeg():
        print("\n[ERROR] FFmpeg is missing from your system PATH!")
        print("Install FFmpeg with:")
        print("  winget install Gyan.FFmpeg")
        print("or download from https://www.gyan.dev/ffmpeg/builds/\n")
        sys.exit(1)

    # 1. Discover categories
    categories = discover_categories(args.sets)
    cat_summary = [f"{c} ({len(items)} items)" for c, items in categories.items()]
    print(f"\nDiscovered categories: {', '.join(cat_summary) if cat_summary else 'None'}")

    if len(categories) < 2:
        print("[ERROR] Need at least 2 non-empty categories to generate Odd One Out rounds.")
        sys.exit(1)

    # 2. Pick background
    bg_path = None
    if args.background:
        if os.path.exists(args.background):
            bg_path = args.background
        elif os.path.exists(os.path.join("backgrounds", args.background)):
            bg_path = os.path.join("backgrounds", args.background)
        else:
            print(f"[Warning] Background '{args.background}' not found, picking random background.")
    if not bg_path:
        bgs = [os.path.join("backgrounds", f) for f in os.listdir("backgrounds") if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))] if os.path.exists("backgrounds") else []
        bg_path = random.choice(bgs) if bgs else None

    # 3. Build rounds
    if args.sample:
        print("\nUsing editable ROUNDS list...")
        rounds = build_sample_rounds(categories)
    else:
        print(f"\nBuilding {num_rounds} random rounds...")
        rounds = build_random_rounds(categories, count=num_rounds)

    print(f"Rounds configured: {len(rounds)}")
    for i, r in enumerate(rounds):
        odd_name = format_slug_name(r["odd_item"]["name"])
        odd_word = get_category_word(r["odd_cat"])
        maj_names = ", ".join([format_slug_name(it["name"]) for it in r["maj_items"]])
        print(f" - Round {i + 1}: {maj_names} ({r['maj_cat']}) vs. {odd_name} ({odd_word}) at pos {r['odd_pos']}")

    # 4. Render
    print(f"\nRendering video to {args.out}...")
    render_odd_one_out_video(
        rounds=rounds,
        bg_path=bg_path,
        output_path=args.out,
        wait_time_sec=wait_time,
        reveal_time_sec=reveal_time,
        progress_cb=lambda frac, text: print(f"[{int(frac * 100)}%] {text}")
    )
    print("\n[Done] Video generation complete!")

if __name__ == "__main__":
    main()
