import pygame
import sys
import math

pygame.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Camera state
camera_x, camera_y = 0, 0
camera_zoom = 1.0  # 1 = 100%, >1 = zoom in, <1 = zoom out

# Grid base spacing
BASE_SPACING = 100

R_MIN, R_MAX = 1.0, 3.0
MIN_PX = 20.0                      # min on-screen spacing to draw a level
MAX_PX = float(WIDTH)

def level_to_spacing(L):
    return BASE_SPACING / (2 ** L)

def visible_level_range(zoom):
    a = math.log2((BASE_SPACING * zoom) / MAX_PX)
    b = math.log2((BASE_SPACING * zoom) / MIN_PX)
    L_min = max(0, math.ceil(a))
    L_max = max(L_min, math.floor(b))
    return L_min, L_max

def level_screen_radius(L, zoom):
    r_world = R_MIN + (R_MAX - R_MIN) * (0.5 ** L)
    r_screen = r_world * zoom

    return max(R_MIN, min(R_MAX, r_screen))

def world_to_screen(wx, wy):
    """Convert world coordinates to screen coordinates based on camera."""
    sx = (wx - camera_x) * camera_zoom + WIDTH // 2
    sy = (wy - camera_y) * camera_zoom + HEIGHT // 2
    return sx, sy

def draw_grid():
    L_min, L_max = visible_level_range(camera_zoom)
    # draw coarse → fine (optional order)
    for L in range(L_min, L_max + 1):
        spacing = level_to_spacing(L)
        draw_grid_level(spacing, L)

def draw_grid_level(spacing, L):
    radius = level_screen_radius(L, camera_zoom)

    left = camera_x - (WIDTH  / 2) / camera_zoom
    right = camera_x + (WIDTH  / 2) / camera_zoom
    top =  camera_y - (HEIGHT / 2) / camera_zoom
    bottom= camera_y + (HEIGHT / 2) / camera_zoom

    start_x = math.floor(left / spacing) * spacing
    start_y = math.floor(top  / spacing) * spacing

    x = start_x
    while x <= right:
        y = start_y
        while y <= bottom:
            sx, sy = world_to_screen(x, y)
            pygame.draw.circle(screen, (200, 200, 200), (int(sx), int(sy)), int(radius))
            y += spacing
        x += spacing

# Main loop
running = True
while running:
    dt = clock.tick(60) / 1000

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEWHEEL:
            if event.y > 0:
                camera_zoom += event.y * 0.1
            elif event.y < 0:
                camera_zoom -= abs(event.y * 0.1)

    # Camera movement
    keys = pygame.key.get_pressed()
    speed = 200 / camera_zoom * dt
    if keys[pygame.K_LEFT]:
        camera_x -= speed
    if keys[pygame.K_RIGHT]:
        camera_x += speed
    if keys[pygame.K_UP]:
        camera_y -= speed
    if keys[pygame.K_DOWN]:
        camera_y += speed

    # Draw
    screen.fill((0, 0, 0))
    draw_grid()
    pygame.display.flip()

pygame.quit()
sys.exit()
