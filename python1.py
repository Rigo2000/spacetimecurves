import pygame, sys, math

pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 12)

# Camera state
camera_x, camera_y = 0.0, 0.0
camera_zoom = 1.0

# Grid constants
BASE_SPACING = 1.0    # world spacing at absolute Level 0
TARGET_SPACING_PX = 100.0  # preferred on-screen spacing for "current level"
MAX_REL_LEVELS = 2     # number of finer levels to draw
R_MIN, R_MAX = 1.0, 5.0

class Particle:
    def __init__(self, world_x, world_y, size=5, color=(0, 100, 255)):
        self.world_x = world_x
        self.world_y = world_y
        self.size = size  # in world units
        self.color = color

    def draw(self, camera_x, camera_y, camera_zoom):
        # Convert world -> screen
        sx = (self.world_x - camera_x) * camera_zoom + WIDTH * 0.5
        sy = (self.world_y - camera_y) * camera_zoom + HEIGHT * 0.5
        screen_radius = max(1, int(round(self.size * camera_zoom)))

        # Only draw if within screen bounds (simple culling)
        if -screen_radius <= sx <= WIDTH + screen_radius and -screen_radius <= sy <= HEIGHT + screen_radius:
            pygame.draw.circle(screen, self.color, (int(sx), int(sy)), screen_radius)
class Body:
    def __init__(self, x, y, mass, radius=5.0):
        self.x = x        # world x
        self.y = y        # world y
        self.mass = mass  # kg
        self.radius = radius  # visual radius for rendering
        self.rs = 2 * 6.67430e-11 * mass / (3e8**2)  # Schwarzschild radius

    def draw(self, camera_x, camera_y, camera_zoom):
        sx = (self.x - camera_x) * camera_zoom + WIDTH * 0.5
        sy = (self.y - camera_y) * camera_zoom + HEIGHT * 0.5
        screen_radius = max(1, int(round(self.radius * camera_zoom)))
        # Simple culling
        if -screen_radius <= sx <= WIDTH + screen_radius and -screen_radius <= sy <= HEIGHT + screen_radius:
            pygame.draw.circle(screen, (0, 200, 0), (int(sx), int(sy)), screen_radius)



particles = [
    Particle(0, 0, size=5),
    Particle(50, 50, size=8),
    Particle(-100, 30, size=4)
]

bodies = [
    Body(0, 0, 5e24),          # like Earth
    Body(0, 0, 1.989e29, 10)   # like Sun
]

def displace_point(x, y, bodies):
    x_new, y_new = x, y
    for body in bodies:
        dx = x_new - body.x
        dy = y_new - body.y
        r = math.hypot(dx, dy)
        if r == 0:
            continue  # avoid division by zero
        # apply weak-field radial displacement
        r_proper = r * (1 + body.rs / (2*r))
        x_new = body.x + r_proper * dx / r
        y_new = body.y + r_proper * dy / r
    return x_new, y_new


# Utilities
def world_to_screen(wx, wy):
    sx = (wx - camera_x) * camera_zoom + WIDTH * 0.5
    sy = (wy - camera_y) * camera_zoom + HEIGHT * 0.5
    return sx, sy

def screen_to_world(sx, sy):
    wx = (sx - WIDTH * 0.5) / camera_zoom + camera_x
    wy = (sy - HEIGHT * 0.5) / camera_zoom + camera_y
    return wx, wy

def level_to_spacing(L):
    return BASE_SPACING / (2 ** L)

def compute_current_level(zoom):
    # Solve spacing * zoom ≈ target
    val = (BASE_SPACING * zoom) / TARGET_SPACING_PX
    if val <= 0:
        return 0
    return round(math.log2(val))   # allow negative results too

def relative_radius(rel_level):
    # Relative 0 = biggest (≈ R_MAX), then halves each finer level
    radius = R_MAX * (0.7 ** rel_level)  # 0.7 factor makes smoother decay
    return max(R_MIN, min(R_MAX, radius))

def draw_grid_level(spacing, radius_px, bodies=[]):
    left = camera_x - (WIDTH * 0.5) / camera_zoom
    right = camera_x + (WIDTH * 0.5) / camera_zoom
    top = camera_y - (HEIGHT * 0.5) / camera_zoom
    bottom = camera_y + (HEIGHT * 0.5) / camera_zoom

    start_x = math.floor(left / spacing) * spacing
    start_y = math.floor(top / spacing) * spacing

    x = start_x
    while x <= right:
        y = start_y
        while y <= bottom:
            # Apply displacement due to all bodies
            x_disp, y_disp = displace_point(x, y, bodies)
            sx, sy = world_to_screen(x_disp, y_disp)
            if -10 <= sx <= WIDTH + 10 and -10 <= sy <= HEIGHT + 10:
                pygame.draw.circle(screen, (200,200,200), (int(round(sx)), int(round(sy))), int(radius_px))

                # Draw the coordinates next to the point
                #coord_text = f"({x:.1f}, {y:.1f})"
                #text_surf = font.render(coord_text, True, (255, 255, 255))
                #screen.blit(text_surf, (sx, sy + 10))  # offset slightly from point
            y += spacing
        x += spacing

def draw_grid():
    L_current = compute_current_level(camera_zoom)
    for rel in range(MAX_REL_LEVELS):
        L = L_current + rel
        spacing = level_to_spacing(L)   # works for negative too
        radius = relative_radius(rel)
        draw_grid_level(spacing, radius, bodies=bodies)

def debug_overlay():
    L_current = compute_current_level(camera_zoom)
    lines = [
        f"camera: ({camera_x:.2f}, {camera_y:.2f})  zoom: {camera_zoom:.4f}",
        f"current base level = {L_current}"
    ]
    y = 8
    for line in lines:
        surf = font.render(line, True, (200, 0, 0))
        screen.blit(surf, (8, y))
        y += 18

# Panning
panning = False
pan_last_mouse = (0, 0)
show_debug = True

# Main loop
running = True
while running:
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            before_wx, before_wy = screen_to_world(mx, my)
            factor = 1.1 ** event.y
            camera_zoom *= factor
            camera_zoom = max(0.001, min(1000.0, camera_zoom))
            # Adjust camera so the world point under the cursor stays fixed
            camera_x, camera_y = before_wx - (mx - WIDTH * 0.5) / camera_zoom, before_wy - (my - HEIGHT * 0.5) / camera_zoom

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 3:
                panning = True
                pan_last_mouse = pygame.mouse.get_pos()

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 3:
                panning = False

        elif event.type == pygame.MOUSEMOTION:
            if panning:
                mx, my = pygame.mouse.get_pos()
                dx, dy = mx - pan_last_mouse[0], my - pan_last_mouse[1]
                camera_x -= dx / camera_zoom
                camera_y -= dy / camera_zoom
                pan_last_mouse = (mx, my)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_d:
                show_debug = not show_debug

    # Keyboard movement
    keys = pygame.key.get_pressed()
    move_speed = 400 / camera_zoom * dt
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        camera_x -= move_speed
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        camera_x += move_speed
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        camera_y -= move_speed
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        camera_y += move_speed

    # Draw
    screen.fill((10, 10, 10))
    draw_grid()

    # Draw bodies
    for body in bodies:
        body.draw(camera_x, camera_y, camera_zoom)

    for p in particles:
        p.draw(camera_x, camera_y, camera_zoom)

    if show_debug:
        debug_overlay()
    pygame.display.flip()

pygame.quit()
sys.exit()
