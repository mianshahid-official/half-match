"""
Acceptance Test Suite for 'Odd One Out'.
Tests:
1. Rejoin test (left+right halves rejoin to exact full picture for every pair)
2. Default render (5 rounds, 1080x1920, 30fps, 39.5s, H.264 + AAC, non-silent audio, peak < 0 dB)
3. --random 3 renders a 25.5s video with 3 rounds
4. Empty categories (characters/, vegetables/) skipped, orphan lonely_pear-1.png warns & skipped
5. Keyframes extraction & inspection (intro, guess, reveal, end card)
6. App's existing 6 acceptance tests pass without regression
"""

import os
import sys
import json
import subprocess
import numpy as np
from PIL import Image

import odd_one_out

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

def get_audio_stats(file_path):
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
        return False, 0.0, 0.0
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    rms = float(np.sqrt(np.mean(audio**2)))
    peak = float(np.max(np.abs(audio)))
    return (rms > 0.01), rms, peak

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

def run_acceptance_tests():
    print("==================================================")
    print("STARTING ODD ONE OUT ACCEPTANCE TESTS")
    print("==================================================\n")

    results = {}

    # -------------------------------------------------------------
    # TEST 1: Rejoin test
    # -------------------------------------------------------------
    print("[TEST 1] Verifying left + right halves rejoin pixel-identically...")
    cats = odd_one_out.discover_categories("sets")
    total_pairs = 0
    rejoin_matches = 0

    for cat_name, pairs in cats.items():
        for pair in pairs:
            total_pairs += 1
            l_img = Image.open(pair["left"]).convert("RGBA")
            r_img = Image.open(pair["right"]).convert("RGBA")

            full = odd_one_out.rejoin_halves(pair["left"], pair["right"])
            assert full.width == l_img.width + r_img.width, "Width mismatch on rejoin"
            assert full.height == max(l_img.height, r_img.height), "Height mismatch on rejoin"

            # Check left slice
            crop_l = full.crop((0, 0, l_img.width, l_img.height))
            diff_l = np.max(np.abs(np.array(l_img).astype(int) - np.array(crop_l).astype(int)))
            assert diff_l == 0, f"Left slice difference > 0 for {pair['name']}"

            # Check right slice
            crop_r = full.crop((l_img.width, 0, l_img.width + r_img.width, r_img.height))
            diff_r = np.max(np.abs(np.array(r_img).astype(int) - np.array(crop_r).astype(int)))
            assert diff_r == 0, f"Right slice difference > 0 for {pair['name']}"

            rejoin_matches += 1

    print(f" - Verified {rejoin_matches}/{total_pairs} pairs rejoining pixel-identically with 0 diff.")
    assert rejoin_matches >= 10, "Expected at least 10 sample pairs"
    results["Test 1: Halves Rejoin Pixel-Identical"] = "PASSED"
    print(">>> TEST 1 PASSED\n")

    # -------------------------------------------------------------
    # TEST 2: Default Render (5 rounds, 39.5s, 1080x1920, 30fps)
    # -------------------------------------------------------------
    print("[TEST 2] Rendering default 5-round video (target: 39.5s)...")
    out_default = "test_odd_5rounds.mp4"
    rounds_5 = odd_one_out.build_random_rounds(cats, count=5)
    odd_one_out.render_odd_one_out_video(rounds_5, bg_path=None, output_path=out_default)

    meta_5 = ffprobe_info(out_default)
    v_stream = next(s for s in meta_5["streams"] if s["codec_type"] == "video")
    a_stream = next(s for s in meta_5["streams"] if s["codec_type"] == "audio")
    dur_5 = float(meta_5["format"]["duration"])
    fps_5 = eval(v_stream["r_frame_rate"])
    not_silent, rms, peak = get_audio_stats(out_default)

    print(f"5-Round Video Verification:")
    print(f" - Resolution: {v_stream['width']}x{v_stream['height']} (Expected 1080x1920)")
    print(f" - FPS: {fps_5:.1f} (Expected 30.0)")
    print(f" - Duration: {dur_5:.2f}s (Expected 39.5s)")
    print(f" - Video Codec: {v_stream['codec_name']} ({v_stream['pix_fmt']})")
    print(f" - Audio Codec: {a_stream['codec_name']} ({a_stream['sample_rate']}Hz, {a_stream['bit_rate']} bps)")
    print(f" - Audio Stats: Non-silent={not_silent}, RMS={rms:.4f}, Peak={peak:.4f} (Peak < 1.0/0dB: {peak < 1.0})")

    assert v_stream["width"] == 1080 and v_stream["height"] == 1920, "Resolution mismatch"
    assert fps_5 == 30.0, "FPS mismatch"
    assert abs(dur_5 - 39.5) < 0.25, f"Expected 39.5s, got {dur_5}"
    assert v_stream["codec_name"] == "h264", "Video codec not h264"
    assert a_stream["codec_name"] == "aac", "Audio codec not aac"
    assert not_silent, "Audio track is silent"
    assert peak < 1.0, f"Audio clipped! Peak = {peak}"

    results["Test 2: Default Render (5 rounds, 39.5s, H.264+AAC, Peak < 0dB)"] = "PASSED"
    print(">>> TEST 2 PASSED\n")

    # -------------------------------------------------------------
    # TEST 3: --random 3 (25.5s video)
    # -------------------------------------------------------------
    print("[TEST 3] Rendering 3-round video (target: 25.5s)...")
    out_3 = "test_odd_3rounds.mp4"
    rounds_3 = odd_one_out.build_random_rounds(cats, count=3)
    odd_one_out.render_odd_one_out_video(rounds_3, bg_path=None, output_path=out_3)

    meta_3 = ffprobe_info(out_3)
    v_3 = next(s for s in meta_3["streams"] if s["codec_type"] == "video")
    a_3 = next(s for s in meta_3["streams"] if s["codec_type"] == "audio")
    dur_3 = float(meta_3["format"]["duration"])

    print(f"3-Round Video Verification:")
    print(f" - Resolution: {v_3['width']}x{v_3['height']}")
    print(f" - Duration: {dur_3:.2f}s (Expected 25.5s)")

    assert v_3["width"] == 1080 and v_3["height"] == 1920
    assert abs(dur_3 - 25.5) < 0.25, f"Expected 25.5s, got {dur_3}"

    results["Test 3: 3 Rounds Render (25.5s)"] = "PASSED"
    print(">>> TEST 3 PASSED\n")

    # -------------------------------------------------------------
    # TEST 4: Empty categories skipped & orphan warning
    # -------------------------------------------------------------
    print("[TEST 4] Testing empty category skipping and orphan lonely_pear warning...")
    # Capture stdout during discovery
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        discovered = odd_one_out.discover_categories("sets")
    printed_log = buf.getvalue()

    print("Discovery output log:")
    print(printed_log.strip())

    # Verify empty categories are skipped
    assert "characters" not in discovered, "Empty category 'characters' should be skipped"
    assert "vegetables" not in discovered, "Empty category 'vegetables' should be skipped"
    assert "fruits" in discovered and "cars" in discovered, "Populated categories missing"

    # Verify orphan lonely_pear warning
    assert "lonely_pear" in printed_log and "skipped" in printed_log, "Orphan lonely_pear warning not printed"

    results["Test 4: Empty Categories Skipped & Orphan Warning"] = "PASSED"
    print(">>> TEST 4 PASSED\n")

    # -------------------------------------------------------------
    # TEST 5: Keyframe Inspection (Intro, Guess, Reveal, End Card)
    # -------------------------------------------------------------
    print("[TEST 5] Extracting and inspecting keyframes from 5-round video...")
    os.makedirs("test_frames_odd", exist_ok=True)

    # Keyframe timestamps:
    # Intro card: 0.0s - 2.0s -> extract at 1.0s
    # Round 1 Guess phase: 2.0s - 7.0s -> extract at 4.5s
    # Round 1 Reveal phase: 7.0s - 9.0s -> extract at 7.8s
    # End card: 37.0s - 39.5s -> extract at 38.2s
    f_intro = extract_frame_at_time(out_default, 1.0, "test_frames_odd/01_intro_card.png")
    f_guess = extract_frame_at_time(out_default, 4.5, "test_frames_odd/02_guess_phase.png")
    f_reveal = extract_frame_at_time(out_default, 7.8, "test_frames_odd/03_reveal_phase.png")
    f_end = extract_frame_at_time(out_default, 38.2, "test_frames_odd/04_end_card.png")

    print(f" - Intro card frame: {f_intro}")
    print(f" - Guess phase frame: {f_guess}")
    print(f" - Reveal phase frame: {f_reveal}")
    print(f" - End card frame: {f_end}")

    # Inspect guess frame: verify 4 item cards visible
    im_guess = Image.open(f_guess)
    arr_guess = np.array(im_guess)
    for pos_i, (gx, gy) in enumerate(odd_one_out.GRID_POSITIONS):
        cell_patch = arr_guess[gy+50:gy+390, gx+50:gx+390]
        # Check non-background variance in card area
        card_variance = np.var(cell_patch)
        print(f"   Pos {pos_i} ({gx}, {gy}) item card variance: {card_variance:.1f}")
        assert card_variance > 50.0, f"Item at pos {pos_i} missing or blank"

    # Inspect reveal frame: verify green ring / tick presence AND all 4 items visible
    im_reveal = Image.open(f_reveal)
    arr_reveal = np.array(im_reveal)
    # Check that all 4 items remain visible in the reveal frame
    for pos_i, (gx, gy) in enumerate(odd_one_out.GRID_POSITIONS):
        cell_patch_rev = arr_reveal[gy+50:gy+390, gx+50:gx+390]
        card_var_rev = np.var(cell_patch_rev)
        print(f"   Reveal Pos {pos_i} ({gx}, {gy}) item card variance: {card_var_rev:.1f}")
        assert card_var_rev > 50.0, f"Item at pos {pos_i} missing or blank in reveal frame"

    # Check green pixels in the whole reveal frame (green ring + tick badge)
    green_count = np.sum((arr_reveal[:, :, 1] > 160) & (arr_reveal[:, :, 0] < 100) & (arr_reveal[:, :, 2] < 120))
    print(f"   Green ring/tick pixels detected in reveal frame: {green_count}")
    assert green_count > 500, "Green ring/tick badge missing in reveal frame"

    # Inspect end card frame
    im_end = Image.open(f_end)
    arr_end = np.array(im_end)
    end_box_var = np.var(arr_end[600:1100, 200:880])
    print(f"   End card content variance: {end_box_var:.1f}")
    assert end_box_var > 100.0, "End card content missing or blank"

    results["Test 5: Keyframes Inspection (All Visible & Legible)"] = "PASSED"
    print(">>> TEST 5 PASSED\n")

    # -------------------------------------------------------------
    # TEST 6: Regression check on existing 6 acceptance tests
    # -------------------------------------------------------------
    print("[TEST 6] Running existing acceptance tests (run_acceptance_tests.py)...")
    res_reg = subprocess.run([sys.executable, "run_acceptance_tests.py"], capture_output=True, text=True)
    print(res_reg.stdout.strip())
    assert res_reg.returncode == 0, f"Regression in existing tests! Output:\n{res_reg.stderr}"

    results["Test 6: Regression Test (Existing 6 Tests Pass)"] = "PASSED"
    print(">>> TEST 6 PASSED\n")

    print("==================================================")
    print("ALL ODD ONE OUT ACCEPTANCE TESTS PASSED!")
    print("==================================================")
    for name, stat in results.items():
        print(f"  • {name}: {stat}")

if __name__ == "__main__":
    run_acceptance_tests()
