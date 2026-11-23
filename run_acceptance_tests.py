"""
Acceptance Test Suite for 'Match the Halves'.
Runs all required verification tests and outputs structured results.
"""

import os
import sys
import json
import subprocess
import wave
import numpy as np
from PIL import Image

import engine

def ffprobe_info(file_path):
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)

def check_audio_not_silent(file_path):
    # Extract audio to pcm and check RMS
    cmd = [
        "ffmpeg", "-y",
        "-i", file_path,
        "-f", "s16le",
        "-ac", "1",
        "-ar", "44100",
        "pipe:1"
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    raw = res.stdout
    if not raw:
        return False, 0.0
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    rms = np.sqrt(np.mean(audio**2))
    return (rms > 0.01), float(rms)

def extract_frame_at_time(video_path, time_sec, out_png):
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(time_sec),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        out_png
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return out_png

def run_tests():
    print("==================================================")
    print("STARTING ACCEPTANCE TESTS: MATCH THE HALVES")
    print("==================================================\n")

    test_results = {}

    # -----------------------------------------------------------------
    # TEST 1: Discovery
    # -----------------------------------------------------------------
    print("[TEST 1] Running Discovery on 'sets', 'backgrounds', 'symbols'...")
    cats, warnings = engine.discover_categories("sets")
    bgs = engine.discover_backgrounds("backgrounds")
    tick_sym, cross_sym = engine.discover_symbols("symbols")

    print(f"Categories found: {len(cats)}")
    for c, items in cats.items():
        print(f" - {c}: {len(items)} items ({', '.join([it['name'] for it in items])})")
    print(f"Warnings recorded: {len(warnings)}")
    for w in warnings:
        print(f" - {w}")
    print(f"Backgrounds found: {len(bgs)} ({[os.path.basename(b) for b in bgs]})")
    print(f"Symbols found: tick={os.path.basename(tick_sym) if tick_sym else 'Built-in'}, cross={os.path.basename(cross_sym) if cross_sym else 'Built-in'}")

    assert len(cats) >= 2, "Failed to discover categories"
    assert "fruits" in cats and len(cats["fruits"]) >= 5, "Fruits items missing"
    assert "cars" in cats and len(cats["cars"]) >= 5, "Cars items missing"
    assert len(warnings) >= 1, "Unpaired item warning test failed"
    test_results["Test 1: Discovery"] = "PASSED"
    print(">>> TEST 1 PASSED\n")

    # -----------------------------------------------------------------
    # TEST 2: Generate 3-Fruit & 4-Car Videos
    # -----------------------------------------------------------------
    print("[TEST 2] Generating 3-fruit and 4-car videos...")
    out_3fruits = "test_3fruits.mp4"
    out_4cars = "test_4cars.mp4"
    
    # 3 Fruits
    fruit_items = cats["fruits"][:3]
    engine.generate_video(
        items=fruit_items,
        background_path=bgs[0] if bgs else None,
        symbols_dir="symbols",
        output_path=out_3fruits,
        audio_mode="builtin"
    )
    
    # 4 Cars
    car_items = cats["cars"][:4]
    engine.generate_video(
        items=car_items,
        background_path=bgs[1] if len(bgs) > 1 else bgs[0],
        symbols_dir="symbols",
        output_path=out_4cars,
        audio_mode="builtin"
    )

    # Verify 3-fruits
    meta_3f = ffprobe_info(out_3fruits)
    v_3f = next(s for s in meta_3f["streams"] if s["codec_type"] == "video")
    a_3f = next(s for s in meta_3f["streams"] if s["codec_type"] == "audio")
    dur_3f = float(meta_3f["format"]["duration"])
    not_silent_3f, rms_3f = check_audio_not_silent(out_3fruits)
    
    print(f"3-Fruit Video Verification:")
    print(f" - Resolution: {v_3f['width']}x{v_3f['height']} (Expected 1080x1920)")
    print(f" - FPS: {eval(v_3f['r_frame_rate']):.1f} (Expected 30)")
    print(f" - Duration: {dur_3f:.2f}s")
    print(f" - Audio: {a_3f['codec_name']} ({a_3f['sample_rate']}Hz, RMS={rms_3f:.4f}, Non-silent={not_silent_3f})")
    
    assert v_3f["width"] == 1080 and v_3f["height"] == 1920
    assert eval(v_3f["r_frame_rate"]) == 30.0
    assert not_silent_3f, "Audio was silent"

    # Verify 4-cars
    meta_4c = ffprobe_info(out_4cars)
    v_4c = next(s for s in meta_4c["streams"] if s["codec_type"] == "video")
    a_4c = next(s for s in meta_4c["streams"] if s["codec_type"] == "audio")
    dur_4c = float(meta_4c["format"]["duration"])
    not_silent_4c, rms_4c = check_audio_not_silent(out_4cars)

    print(f"4-Car Video Verification:")
    print(f" - Resolution: {v_4c['width']}x{v_4c['height']} (Expected 1080x1920)")
    print(f" - FPS: {eval(v_4c['r_frame_rate']):.1f} (Expected 30)")
    print(f" - Duration: {dur_4c:.2f}s")
    print(f" - Audio: {a_4c['codec_name']} ({a_4c['sample_rate']}Hz, RMS={rms_4c:.4f}, Non-silent={not_silent_4c})")

    assert v_4c["width"] == 1080 and v_4c["height"] == 1920
    assert eval(v_4c["r_frame_rate"]) == 30.0
    assert not_silent_4c, "Audio was silent"
    test_results["Test 2: 3-Fruit & 4-Car Generation & FFprobe"] = "PASSED"
    print(">>> TEST 2 PASSED\n")

    # -----------------------------------------------------------------
    # TEST 3: Frame Inspection (Wrong match X, Right match Tick, Finished items whole)
    # -----------------------------------------------------------------
    print("[TEST 3] Extracting and inspecting keyframes from 3-fruit video...")
    os.makedirs("test_frames", exist_ok=True)
    
    # In 3-fruits:
    # 0-1.0s: intro
    # 1.0-1.7s: bottom item slides in to row 0
    # ~2.2s: row 0 evaluation (Wrong match: X)
    # ~4.6s: row 2 evaluation (Right match: Tick)
    # ~13.0s: final hold (all items complete and whole)
    f_wrong = extract_frame_at_time(out_3fruits, 2.2, "test_frames/3fruits_wrong_match.png")
    f_correct = extract_frame_at_time(out_3fruits, 4.8, "test_frames/3fruits_correct_match.png")
    f_final = extract_frame_at_time(out_3fruits, dur_3f - 0.5, "test_frames/3fruits_final_hold.png")

    print(f" - Extracted wrong match frame: {f_wrong}")
    print(f" - Extracted correct match frame: {f_correct}")
    print(f" - Extracted final hold frame: {f_final}")

    # Inspect colors in symbol area (around x=810, y=row 0 center)
    im_w = Image.open(f_wrong)
    arr_w = np.array(im_w)
    # The X symbol has red color: check if red channel is significantly higher than blue/green
    sym_region_w = arr_w[200:400, 750:950]
    red_pixels = np.sum((sym_region_w[:, :, 0] > 180) & (sym_region_w[:, :, 1] < 120))
    print(f"   Wrong match symbol red pixel count: {red_pixels}")
    assert red_pixels > 200, "X symbol not clearly present in wrong match frame"

    # Inspect correct match tick (green symbol around row 2: y=1300:1500, x=750:950)
    im_c = Image.open(f_correct)
    arr_c = np.array(im_c)
    sym_region_c = arr_c[1300:1550, 750:950]
    green_pixels = np.sum((sym_region_c[:, :, 1] > 160) & (sym_region_c[:, :, 0] < 100))
    print(f"   Right match symbol green pixel count: {green_pixels}")
    assert green_pixels > 200, "Tick symbol not clearly present in right match frame"

    # Inspect final hold: all 3 items have right halves in place (x=420 to 700)
    im_fin = Image.open(f_final)
    arr_fin = np.array(im_fin)
    # Check that rows 0, 1, 2 all have non-background pixels in the right-half area (x=450..650)
    for r_idx, y_val in enumerate([200, 800, 1400]):
        row_slice = arr_fin[y_val:y_val+100, 450:650]
        # Compare with pure background at bottom
        diff = np.mean(np.abs(row_slice.astype(float) - arr_fin[1800:1900, 450:650].astype(float)))
        print(f"   Row {r_idx} item right-half presence diff: {diff:.1f}")
        assert diff > 15.0, f"Row {r_idx} right half missing in final hold"

    test_results["Test 3: Frame Inspection (X, Tick, Finished whole)"] = "PASSED"
    print(">>> TEST 3 PASSED\n")

    # -----------------------------------------------------------------
    # TEST 4: Named Items & Exact Stack Order
    # -----------------------------------------------------------------
    print("[TEST 4] Testing exact stack order with named items...")
    out_named = "test_named_order.mp4"
    # Choose specific order: [banana, strawberry, apple]
    item_lookup = {it["name"]: it for it in cats["fruits"]}
    named_order = [item_lookup["banana"], item_lookup["strawberry"], item_lookup["apple"]]
    
    engine.generate_video(
        items=named_order,
        background_path=bgs[0] if bgs else None,
        symbols_dir="symbols",
        output_path=out_named,
        audio_mode="builtin"
    )
    
    # Check top row (banana), middle row (strawberry), bottom row (apple) in final frame
    meta_named = ffprobe_info(out_named)
    dur_named = float(meta_named["format"]["duration"])
    f_named = extract_frame_at_time(out_named, dur_named - 0.5, "test_frames/named_order_final.png")
    im_named = Image.open(f_named)
    arr_named = np.array(im_named)
    
    # Banana is yellow (high red + high green, low blue) at Row 0 (y=100..400)
    top_yellow = np.sum((arr_named[100:400, 200:400, 0] > 180) & (arr_named[100:400, 200:400, 1] > 180) & (arr_named[100:400, 200:400, 2] < 100))
    # Strawberry is red at Row 1 (y=700..1000)
    mid_red = np.sum((arr_named[700:1000, 200:400, 0] > 180) & (arr_named[700:1000, 200:400, 1] < 80))
    
    print(f" - Top row yellow (banana) pixel count: {top_yellow}")
    print(f" - Mid row red (strawberry) pixel count: {mid_red}")
    assert top_yellow > 100, "Banana not at Row 0 as requested"
    assert mid_red > 100, "Strawberry not at Row 1 as requested"

    test_results["Test 4: Named Items Stack Order"] = "PASSED"
    print(">>> TEST 4 PASSED\n")

    # -----------------------------------------------------------------
    # TEST 5: Custom Music File
    # -----------------------------------------------------------------
    print("[TEST 5] Generating video with user music file...")
    out_music = "test_custom_music.mp4"
    engine.generate_video(
        items=fruit_items,
        background_path=bgs[0] if bgs else None,
        symbols_dir="symbols",
        output_path=out_music,
        audio_mode="custom",
        custom_audio_path="sample_music.wav",
        music_volume=0.6
    )
    
    meta_mus = ffprobe_info(out_music)
    a_mus = next((s for s in meta_mus["streams"] if s["codec_type"] == "audio"), None)
    dur_mus = float(meta_mus["format"]["duration"])
    not_silent_mus, rms_mus = check_audio_not_silent(out_music)
    
    print(f"Custom Music Video Verification:")
    print(f" - Duration: {dur_mus:.2f}s (Matches 3-fruit duration ~{dur_3f:.2f}s)")
    print(f" - Audio stream: {a_mus['codec_name'] if a_mus else 'NONE'} ({a_mus['sample_rate']}Hz, RMS={rms_mus:.4f})")
    
    assert a_mus is not None, "Audio stream missing in custom music mode"
    assert not_silent_mus, "Audio is silent"
    assert abs(dur_mus - dur_3f) < 0.5, "Duration mismatch"

    test_results["Test 5: Custom Music File Mode"] = "PASSED"
    print(">>> TEST 5 PASSED\n")

    # -----------------------------------------------------------------
    # TEST 6: Mute Mode
    # -----------------------------------------------------------------
    print("[TEST 6] Generating video in Mute mode...")
    out_mute = "test_mute.mp4"
    engine.generate_video(
        items=fruit_items,
        background_path=bgs[0] if bgs else None,
        symbols_dir="symbols",
        output_path=out_mute,
        audio_mode="mute"
    )

    meta_mute = ffprobe_info(out_mute)
    audio_streams = [s for s in meta_mute["streams"] if s["codec_type"] == "audio"]
    video_streams = [s for s in meta_mute["streams"] if s["codec_type"] == "video"]
    
    print(f"Mute Mode Video Verification:")
    print(f" - Video streams: {len(video_streams)}")
    print(f" - Audio streams: {len(audio_streams)} (Expected 0)")

    assert len(video_streams) == 1, "Video stream missing"
    assert len(audio_streams) == 0, "Audio stream must not exist in Mute mode!"

    test_results["Test 6: Mute Mode (No Audio Stream)"] = "PASSED"
    print(">>> TEST 6 PASSED\n")

    print("==================================================")
    print("ALL ACCEPTANCE TESTS COMPLETED SUCCESSFULLY!")
    print("==================================================")
    for t_name, status in test_results.items():
        print(f" - {t_name}: {status}")

if __name__ == "__main__":
    run_tests()
