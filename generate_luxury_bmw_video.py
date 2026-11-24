import os
import sys
import time
import math
import numpy as np
import cv2
import av

print("=== BMW M3 Photorealistic Luxury Background Video Generator ===")
t_start = time.time()

# Configuration
WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION = 10.0
TOTAL_FRAMES = int(FPS * DURATION) # 300 frames
OUTPUT_MP4 = r"D:\Django_Final_Project\bmw_luxury_loop.mp4"

# Source paths
IMG_PATH = r"D:\Django_Final_Project\BMW.png"
CUTOUT_PATH = r"D:\Django_Final_Project\bmw_car_isolated.png"

# Load source image & cutout
print("1. Loading source layers...")
base_orig = cv2.imread(IMG_PATH)
cutout_orig = cv2.imread(CUTOUT_PATH, cv2.IMREAD_UNCHANGED)

# Resize to 1920x1080 Full HD
base_1080 = cv2.resize(base_orig, (WIDTH, HEIGHT), interpolation=cv2.INTER_LANCZOS4)
cutout_1080 = cv2.resize(cutout_orig, (WIDTH, HEIGHT), interpolation=cv2.INTER_LANCZOS4)

car_bgr = cutout_1080[:, :, :3]
car_alpha = cutout_1080[:, :, 3].astype(np.float32) / 255.0

# Refined anti-aliased edge
car_alpha_soft = cv2.GaussianBlur(car_alpha, (5, 5), 1.0)

# Precompute clean inpainted background for 2.5D parallax shift
print("2. Inpainting background boundary for parallax...")
kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
dilated_mask = cv2.dilate((car_alpha > 0.05).astype(np.uint8) * 255, kernel_dilate)
bg_inpainted = cv2.inpaint(base_1080, dilated_mask, 7, cv2.INPAINT_TELEA)

# 3. Authentic Headlight Extraction & Bloom Maps
print("3. Extracting real BMW Laserlight optical signatures...")
gray_car = cv2.cvtColor(car_bgr, cv2.COLOR_BGR2GRAY)
y_grid, x_grid = np.ogrid[:HEIGHT, :WIDTH]

# Define headlight zones on 1080p
zone1 = (x_grid >= 930) & (x_grid <= 1130) & (y_grid >= 520) & (y_grid <= 620)
zone2 = (x_grid >= 1410) & (x_grid <= 1580) & (y_grid >= 510) & (y_grid <= 600)
hl_pixels = (gray_car > 185) & (cutout_1080[:, :, 3] > 200)

hl_mask = np.zeros_like(gray_car, dtype=np.float32)
hl_mask[(zone1 | zone2) & hl_pixels] = 1.0

# Headlight multi-scale blooms (local to car layer so they transform with car)
hl_bloom_core = cv2.GaussianBlur(hl_mask, (15, 15), 4.0)
hl_bloom_soft = cv2.GaussianBlur(hl_mask, (45, 45), 14.0)
hl_bloom_wide = cv2.GaussianBlur(hl_mask, (95, 95), 30.0)
hl_streak = cv2.GaussianBlur(hl_mask, (181, 7), 55.0, 1.2) # anamorphic horizontal laser streak

hl_bloom_map = (hl_bloom_core * 0.8 + hl_bloom_soft * 0.45 + hl_bloom_wide * 0.25 + hl_streak * 0.55)
# Headlight color: crisp platinum with subtle warm/ice-blue luxury tint
hl_color = np.array([255, 250, 240], dtype=np.float32) # BGR
hl_bloom_3ch = np.dstack([hl_bloom_map * hl_color[0], hl_bloom_map * hl_color[1], hl_bloom_map * hl_color[2]])

# 4. Authentic Sun Bloom & God-Rays (local to background)
print("4. Computing desert golden hour sun optics...")
gray_base = cv2.cvtColor(base_1080, cv2.COLOR_BGR2GRAY)
sun_zone = (x_grid < 180) & (y_grid < 260) & (gray_base > 220)
sun_mask = np.zeros_like(gray_base, dtype=np.float32)
sun_mask[sun_zone] = 1.0

sun_bloom_s = cv2.GaussianBlur(sun_mask, (41, 41), 12.0)
sun_bloom_m = cv2.GaussianBlur(sun_mask, (101, 101), 32.0)
sun_bloom_l = cv2.GaussianBlur(sun_mask, (181, 181), 60.0)
sun_streak = cv2.GaussianBlur(sun_mask, (221, 9), 70.0, 1.4)

sun_bloom_map = (sun_bloom_s * 0.55 + sun_bloom_m * 0.38 + sun_bloom_l * 0.22 + sun_streak * 0.35)
sun_color = np.array([130, 195, 255], dtype=np.float32) # Warm golden BGR
sun_bloom_3ch = np.dstack([sun_bloom_map * sun_color[0], sun_bloom_map * sun_color[1], sun_bloom_map * sun_color[2]])

# 5. Metallic Paint Specular Mask on Car Body
print("5. Preparing metallic bodywork specular sweep...")
hsv_car = cv2.cvtColor(car_bgr, cv2.COLOR_BGR2HSV)
paint_mask = ((hsv_car[:, :, 0] >= 30) & (hsv_car[:, :, 0] <= 95) & (hsv_car[:, :, 1] > 30)) | (hsv_car[:, :, 2] > 175)
paint_mask = (paint_mask.astype(np.float32) * car_alpha_soft)
paint_mask = cv2.GaussianBlur(paint_mask, (7, 7), 2.0)

# Precalculate 3D golden atmospheric dust particles
print("6. Initializing 3D atmospheric golden particle field...")
np.random.seed(101)
NUM_PARTICLES = 65
particles = []
for p in range(NUM_PARTICLES):
    x0 = np.random.uniform(20, WIDTH - 20)
    y0 = np.random.uniform(150, HEIGHT - 80)
    speed_k = np.random.choice([1, 2]) # Integer wrap for seamless loop
    radius = np.random.uniform(1.2, 3.6)
    alpha_base = np.random.uniform(0.35, 0.85)
    twinkle_freq = np.random.choice([1, 2, 3])
    phase = np.random.uniform(0, 2 * math.pi)
    depth = np.random.uniform(0.5, 1.2)
    warmth = np.random.uniform(0.85, 1.0)
    particles.append({
        'x0': x0, 'y0': y0, 'speed_k': speed_k, 'radius': radius,
        'alpha': alpha_base, 'freq': twinkle_freq, 'phase': phase,
        'depth': depth, 'color': np.array([125 * warmth, 195 * warmth, 255], dtype=np.float32)
    })

# Cinematic Luxury Vignette (softer, elegant)
CENTER_POS = (WIDTH / 2.0, HEIGHT / 2.0)
dist_sq = ((x_grid - CENTER_POS[0]) / (WIDTH * 0.6)) ** 2 + ((y_grid - CENTER_POS[1]) / (HEIGHT * 0.6)) ** 2
vignette = np.clip(1.0 - 0.22 * (dist_sq ** 1.1), 0.72, 1.0).astype(np.float32)
vignette_3ch = np.dstack([vignette]*3)

# Angle for metallic specular sweep
phi = math.radians(-32.0)
cos_phi = math.cos(phi)
sin_phi = math.sin(phi)
proj_grid = x_grid * cos_phi + y_grid * sin_phi

def render_frame(frame_idx):
    # Normalized time & phase angle
    t_norm = frame_idx / TOTAL_FRAMES
    tau = 2.0 * math.pi * t_norm
    
    # 1. 2.5D Parallax Camera Motion
    # Seamless breathing zoom (1.00 at t=0 and t=10, peak 1.045 at t=5s)
    cam_zoom_bg = 1.0 + 0.022 * (0.5 * (1.0 - math.cos(tau)))
    cam_pan_x_bg = 6.0 * math.sin(tau)
    cam_pan_y_bg = 2.5 * math.sin(2.0 * tau)
    
    # Hero Car parallax: higher amplitude + road suspension micro-dynamics
    cam_zoom_car = 1.0 + 0.052 * (0.5 * (1.0 - math.cos(tau)))
    cam_pan_x_car = 16.0 * math.sin(tau)
    cam_pan_y_car = 6.0 * math.sin(2.0 * tau) + 1.2 * math.cos(4.0 * tau) + 0.5 * math.sin(6.0 * tau)
    car_tilt = 0.16 * math.sin(tau)
    
    # --- Background Layer ---
    M_bg = cv2.getRotationMatrix2D(CENTER_POS, 0.0, cam_zoom_bg)
    M_bg[0, 2] += cam_pan_x_bg
    M_bg[1, 2] += cam_pan_y_bg
    frame_bg = cv2.warpAffine(bg_inpainted, M_bg, (WIDTH, HEIGHT), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    
    # Heat Shimmer on Lower Road Asphalt (y > 800)
    # 3 exact cycles in 10s -> seamless loop
    heat_phase = 3.0 * tau
    for ry in range(800, HEIGHT, 8):
        weight = (ry - 800) / (HEIGHT - 800)
        shift = int(1.4 * weight * math.sin(ry * 0.07 + heat_phase))
        if shift != 0:
            frame_bg[ry:ry+8, :] = np.roll(frame_bg[ry:ry+8, :], shift, axis=1)

    # Dynamic Sun Bloom on Background (breathing pulse)
    sun_pulse = 1.0 + 0.20 * math.sin(tau)
    warped_sun_bloom = cv2.warpAffine(sun_bloom_3ch * sun_pulse, M_bg, (WIDTH, HEIGHT), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    frame_bg = frame_bg.astype(np.float32) + warped_sun_bloom

    # --- Hero Car Layer ---
    # Specular sweep across car metallic paint
    # Two smooth commercial glints:
    # Glint 1: t in [0.8s, 4.8s]
    # Glint 2: t in [5.4s, 9.4s]
    t_sec = DURATION * t_norm
    specular_car = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
    
    if 0.8 <= t_sec <= 4.8:
        p1 = (t_sec - 0.8) / (4.8 - 0.8)
        env1 = math.sin(math.pi * p1)
        c1 = 450.0 + p1 * 1250.0
        beam1 = np.exp(-((proj_grid - c1) / 70.0) ** 2) * env1 * 0.42
        specular_car += beam1.astype(np.float32)
        
    if 5.4 <= t_sec <= 9.4:
        p2 = (t_sec - 5.4) / (9.4 - 5.4)
        env2 = math.sin(math.pi * p2)
        c2 = 350.0 + p2 * 1350.0
        beam2 = np.exp(-((proj_grid - c2) / 85.0) ** 2) * env2 * 0.36
        specular_car += beam2.astype(np.float32)
        
    # Specular light on car paintwork
    specular_highlight = (specular_car * paint_mask)[:, :, np.newaxis]
    specular_color = np.array([210, 245, 255], dtype=np.float32)
    car_lit = car_bgr.astype(np.float32) + specular_highlight * specular_color
    
    # Headlight breathing bloom (local to car)
    hl_pulse = 1.0 + 0.32 * (0.5 * (1.0 - math.cos(tau)))
    car_lit += hl_bloom_3ch * hl_pulse
    car_lit = np.clip(car_lit, 0, 255)
    
    # Transform Car & Mask
    M_car = cv2.getRotationMatrix2D(CENTER_POS, car_tilt, cam_zoom_car)
    M_car[0, 2] += cam_pan_x_car
    M_car[1, 2] += cam_pan_y_car
    
    warped_car = cv2.warpAffine(car_lit, M_car, (WIDTH, HEIGHT), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    warped_alpha = cv2.warpAffine(car_alpha_soft, M_car, (WIDTH, HEIGHT), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    warped_alpha_3ch = np.dstack([warped_alpha]*3)
    
    # Composite Car over Background
    composite = frame_bg * (1.0 - warped_alpha_3ch) + warped_car * warped_alpha_3ch
    
    # --- Atmospheric Golden Dust Particles ---
    particle_layer = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float32)
    for pt in particles:
        # Perfectly seamless horizontal wrap
        px = (pt['x0'] - pt['speed_k'] * WIDTH * t_norm) % WIDTH
        # Floating gentle vertical wave
        py = pt['y0'] + 10.0 * math.sin(tau + pt['phase'])
        # Twinkle
        twinkle = 0.70 + 0.30 * math.sin(pt['freq'] * tau + pt['phase'])
        alpha_p = pt['alpha'] * twinkle
        
        ipx, ipy = int(px), int(py)
        if 0 <= ipx < WIDTH and 0 <= ipy < HEIGHT:
            col = (pt['color'] * alpha_p).tolist()
            r = int(pt['radius'])
            cv2.circle(particle_layer, (ipx, ipy), r, col, -1, lineType=cv2.LINE_AA)
            if r > 1:
                cv2.circle(particle_layer, (ipx, ipy), r * 3, [c * 0.35 for c in col], -1, lineType=cv2.LINE_AA)
                
    particle_layer = cv2.GaussianBlur(particle_layer, (3, 3), 0.8)
    composite += particle_layer
    
    # --- Vignette & Color Grading ---
    composite = np.clip(composite, 0, 255) * vignette_3ch
    
    # Gentle luxury cinematic film tone curve
    norm = composite / 255.0
    graded = (1.0 / (1.0 + np.exp(-4.8 * (norm - 0.49)))) * 255.0
    final = np.clip(0.40 * graded + 0.60 * composite, 0, 255).astype(np.uint8)
    
    return final

# Test key frames
print("7. Verifying keyframes...")
f0 = render_frame(0)
f75 = render_frame(75)
f150 = render_frame(150)
f225 = render_frame(225)
f299 = render_frame(299)

cv2.imwrite(r"D:\Django_Final_Project\frame_000.jpg", f0)
cv2.imwrite(r"D:\Django_Final_Project\frame_075.jpg", f75)
cv2.imwrite(r"D:\Django_Final_Project\frame_150.jpg", f150)
cv2.imwrite(r"D:\Django_Final_Project\frame_225.jpg", f225)
cv2.imwrite(r"D:\Django_Final_Project\frame_299.jpg", f299)

diff = np.mean(np.abs(f0.astype(np.float32) - f299.astype(np.float32)))
print(f"Loop seam average pixel delta (frame 0 vs 299): {diff:.2f}/255")

# 8. Encode Complete 10s MP4 Loop
print("8. Encoding full 10-second seamless video loop (300 frames) with PyAV H.264...")
container = av.open(OUTPUT_MP4, mode='w', format='mp4')
stream = container.add_stream('libx264', rate=FPS)
stream.width = WIDTH
stream.height = HEIGHT
stream.pix_fmt = 'yuv420p'
stream.options = {
    'crf': '18',          # visually lossless high quality
    'preset': 'fast',      # fast encoding
    'movflags': '+faststart' # fast web streaming
}

t_enc = time.time()
for f_idx in range(TOTAL_FRAMES):
    frame_bgr = render_frame(f_idx)
    av_frame = av.VideoFrame.from_ndarray(frame_bgr, format='bgr24')
    for packet in stream.encode(av_frame):
        container.mux(packet)
    if (f_idx + 1) % 30 == 0:
        sec = (f_idx + 1) / FPS
        fps_calc = (f_idx + 1) / (time.time() - t_enc)
        print(f"Rendered {f_idx + 1}/{TOTAL_FRAMES} frames ({sec:.1f}s / 10.0s) @ {fps_calc:.1f} fps")

# Flush
for packet in stream.encode():
    container.mux(packet)
container.close()

file_size_mb = os.path.getsize(OUTPUT_MP4) / (1024 * 1024)
print("=== COMPLETE SUCCESS! ===")
print(f"Video file: {OUTPUT_MP4}")
print(f"File size: {file_size_mb:.2f} MB")
print(f"Total time elapsed: {time.time() - t_start:.2f}s")
