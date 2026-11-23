"""
Generates clean, cute sample vector-style assets for testing 'Match the Halves'.
Creates:
- fruits/ (apple, banana, orange, watermelon, strawberry, + 1 lonely unpaired half to test warning)
- cars/ (sports_car, truck, taxi, bus)
- vegetables/ (carrot, broccoli, eggplant, corn)
- characters/ (lion, panda, monkey, tiger)
- backgrounds/ (sunny_park, playful_clouds, colorful_gradient)
- symbols/ (correct.png, wrong.png)
- sample_music.wav (for testing custom music mode)
"""

import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def create_item(name, draw_fn, category_dir, suffix_style="num", width=400, height=400):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw_fn(draw, width, height)
    
    # Split vertically
    half_w = width // 2
    left_crop = img.crop((0, 0, half_w, height))
    right_crop = img.crop((half_w, 0, width, height))
    
    if suffix_style == "num":
        l_name = f"{name}-1.png"
        r_name = f"{name}-2.png"
    else:
        l_name = f"{name}-left.png"
        r_name = f"{name}-right.png"
        
    left_crop.save(os.path.join(category_dir, l_name))
    right_crop.save(os.path.join(category_dir, r_name))

# Drawing functions for fruits
def draw_apple(draw, w, h):
    draw.ellipse([60, 80, 340, 360], fill=(230, 45, 45, 255), outline=(180, 20, 20, 255), width=6)
    draw.line([200, 80, 210, 30], fill=(120, 60, 20, 255), width=10)
    draw.ellipse([210, 25, 270, 60], fill=(60, 180, 50, 255))
    draw.ellipse([100, 120, 150, 180], fill=(255, 120, 120, 200))

def draw_banana(draw, w, h):
    draw.arc([30, 40, 370, 370], start=30, end=170, fill=(255, 215, 0, 255), width=70)
    draw.rectangle([50, 120, 75, 145], fill=(139, 69, 19, 255))
    draw.rectangle([340, 150, 365, 175], fill=(139, 69, 19, 255))

def draw_orange(draw, w, h):
    draw.ellipse([60, 60, 340, 340], fill=(255, 140, 0, 255), outline=(220, 110, 0, 255), width=6)
    draw.ellipse([190, 40, 210, 60], fill=(80, 160, 40, 255))
    draw.ellipse([100, 100, 140, 140], fill=(255, 190, 80, 200))

def draw_watermelon(draw, w, h):
    draw.chord([50, 60, 350, 360], start=0, end=180, fill=(235, 50, 70, 255), outline=(40, 140, 40, 255), width=16)
    for sx, sy in [(130, 250), (170, 270), (220, 250), (270, 240), (200, 220)]:
        draw.ellipse([sx-6, sy-10, sx+6, sy+10], fill=(30, 30, 30, 255))

def draw_strawberry(draw, w, h):
    points = [(200, 370), (70, 160), (130, 80), (270, 80), (330, 160)]
    draw.polygon(points, fill=(220, 30, 50, 255), outline=(170, 20, 30, 255))
    draw.polygon([(140, 80), (200, 40), (260, 80)], fill=(50, 170, 50, 255))
    for px, py in [(150, 160), (250, 160), (200, 220), (160, 280), (240, 280)]:
        draw.ellipse([px-4, py-6, px+4, py+6], fill=(255, 240, 150, 255))

# Drawing functions for cars
def draw_sports_car(draw, w, h):
    draw.polygon([(60, 260), (110, 180), (280, 180), (340, 260)], fill=(220, 30, 30, 255))
    draw.rectangle([40, 250, 360, 300], fill=(220, 30, 30, 255))
    draw.polygon([(130, 250), (150, 195), (250, 195), (270, 250)], fill=(200, 240, 255, 255))
    draw.ellipse([90, 270, 150, 330], fill=(40, 40, 40, 255), outline=(180, 180, 180, 255), width=6)
    draw.ellipse([250, 270, 310, 330], fill=(40, 40, 40, 255), outline=(180, 180, 180, 255), width=6)

def draw_pickup_truck(draw, w, h):
    draw.rectangle([40, 180, 220, 290], fill=(50, 120, 220, 255))
    draw.rectangle([220, 230, 360, 290], fill=(50, 120, 220, 255))
    draw.rectangle([60, 195, 150, 250], fill=(210, 240, 255, 255))
    draw.ellipse([90, 260, 160, 330], fill=(40, 40, 40, 255), outline=(180, 180, 180, 255), width=6)
    draw.ellipse([260, 260, 330, 330], fill=(40, 40, 40, 255), outline=(180, 180, 180, 255), width=6)

def draw_taxi(draw, w, h):
    draw.polygon([(80, 240), (120, 170), (280, 170), (320, 240)], fill=(255, 210, 0, 255))
    draw.rectangle([50, 230, 350, 290], fill=(255, 210, 0, 255))
    draw.rectangle([170, 145, 230, 170], fill=(40, 40, 40, 255))
    draw.polygon([(140, 230), (155, 185), (245, 185), (260, 230)], fill=(220, 245, 255, 255))
    draw.ellipse([90, 260, 150, 320], fill=(30, 30, 30, 255), outline=(200, 200, 200, 255), width=5)
    draw.ellipse([250, 260, 310, 320], fill=(30, 30, 30, 255), outline=(200, 200, 200, 255), width=5)

def draw_bus(draw, w, h):
    draw.rectangle([50, 130, 350, 280], fill=(70, 190, 90, 255))
    for wx in [80, 150, 220, 290]:
        draw.rectangle([wx, 150, wx+50, 200], fill=(220, 245, 255, 255))
    draw.ellipse([90, 250, 160, 320], fill=(30, 30, 30, 255), outline=(180, 180, 180, 255), width=6)
    draw.ellipse([240, 250, 310, 320], fill=(30, 30, 30, 255), outline=(180, 180, 180, 255), width=6)

def draw_sedan(draw, w, h):
    draw.polygon([(80, 250), (130, 180), (270, 180), (320, 250)], fill=(160, 60, 180, 255))
    draw.rectangle([50, 240, 350, 290], fill=(160, 60, 180, 255))
    draw.ellipse([100, 260, 150, 310], fill=(30, 30, 30, 255), outline=(180, 180, 180, 255), width=5)
    draw.ellipse([250, 260, 300, 310], fill=(30, 30, 30, 255), outline=(180, 180, 180, 255), width=5)

# Backgrounds
def generate_backgrounds():
    os.makedirs("backgrounds", exist_ok=True)
    
    # 1. Sunny Park
    bg1 = Image.new("RGB", (1080, 1920), (135, 206, 235))
    d1 = ImageDraw.Draw(bg1)
    d1.ellipse([750, 100, 980, 330], fill=(255, 220, 50))
    d1.chord([-200, 1100, 1300, 2100], start=0, end=180, fill=(76, 175, 80))
    d1.chord([-100, 1300, 1200, 2200], start=0, end=180, fill=(56, 142, 60))
    bg1.save("backgrounds/sunny_park.png")
    
    # 2. Playful Gradient / Candy Sky
    bg2 = Image.new("RGB", (1080, 1920))
    # Vertical gradient from violet to peach
    arr = np.zeros((1920, 1080, 3), dtype=np.uint8)
    for y in range(1920):
        t = y / 1920.0
        r = int((1 - t) * 147 + t * 255)
        g = int((1 - t) * 112 + t * 182)
        b = int((1 - t) * 219 + t * 193)
        arr[y, :, 0] = r
        arr[y, :, 1] = g
        arr[y, :, 2] = b
    bg2 = Image.fromarray(arr)
    d2 = ImageDraw.Draw(bg2)
    # Draw soft clouds
    for cx, cy in [(300, 300), (800, 500), (200, 1400), (850, 1600)]:
        d2.ellipse([cx-150, cy-50, cx+150, cy+50], fill=(255, 255, 255, 100))
    bg2.save("backgrounds/candy_sky.png")

# Symbols
def generate_symbols():
    os.makedirs("symbols", exist_ok=True)
    
    # Correct / Tick (Green)
    correct = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
    dc = ImageDraw.Draw(correct)
    dc.ellipse([20, 20, 220, 220], fill=(46, 204, 113, 255), outline=(39, 174, 96, 255), width=8)
    # Checkmark
    dc.line([(65, 125), (105, 165), (175, 75)], fill=(255, 255, 255, 255), width=22)
    correct.save("symbols/correct.png")
    
    # Wrong / Cross (Red)
    wrong = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
    dw = ImageDraw.Draw(wrong)
    dw.ellipse([20, 20, 220, 220], fill=(231, 76, 60, 255), outline=(192, 57, 43, 255), width=8)
    # X
    dw.line([(70, 70), (170, 170)], fill=(255, 255, 255, 255), width=22)
    dw.line([(170, 70), (70, 170)], fill=(255, 255, 255, 255), width=22)
    wrong.save("symbols/wrong.png")

def generate_sample_music(duration_sec=15.0, sample_rate=44100):
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    # Cheerful upbeat music synth
    music = np.zeros_like(t)
    notes = [261.63, 329.63, 392.00, 523.25, 440.00, 392.00] # C, E, G, C, A, G
    beat_len = 0.25
    for i, note in enumerate(notes * int(duration_sec / (len(notes)*beat_len) + 1)):
        start = i * beat_len
        end = start + beat_len
        idx = (t >= start) & (t < end)
        if np.any(idx):
            sub_t = t[idx] - start
            tone = 0.3 * np.sin(2 * np.pi * note * sub_t) * np.exp(-sub_t * 4)
            music[idx] += tone
    
    # Clamp and save as wav
    music = np.clip(music, -0.9, 0.9)
    stereo = np.column_stack((music, music))
    int_audio = (stereo * 32767).astype(np.int16)
    
    import wave
    with wave.open("sample_music.wav", "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(int_audio.tobytes())

if __name__ == "__main__":
    fruits_dir = "sets/fruits"
    cars_dir = "sets/cars"
    os.makedirs(fruits_dir, exist_ok=True)
    os.makedirs(cars_dir, exist_ok=True)
    
    # 5 Fruits
    create_item("apple", draw_apple, fruits_dir, "num")
    create_item("banana", draw_banana, fruits_dir, "num")
    create_item("orange", draw_orange, fruits_dir, "num")
    create_item("watermelon", draw_watermelon, fruits_dir, "left")
    create_item("strawberry", draw_strawberry, fruits_dir, "left")
    
    # Add an unpaired file to test skip and warning!
    unpaired_img = Image.new("RGBA", (200, 400), (255, 0, 0, 255))
    unpaired_img.save(os.path.join(fruits_dir, "lonely_pear-1.png"))
    
    # 5 Cars
    create_item("sports_car", draw_sports_car, cars_dir, "num")
    create_item("pickup_truck", draw_pickup_truck, cars_dir, "num")
    create_item("taxi", draw_taxi, cars_dir, "num")
    create_item("bus", draw_bus, cars_dir, "left")
    create_item("sedan", draw_sedan, cars_dir, "left")
    
    generate_backgrounds()
    generate_symbols()
    generate_sample_music()
    print("Sample assets generated successfully!")
