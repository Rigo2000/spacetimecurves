import pygame, sys, math, numpy as np

pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 14)

# Camera
camera_x, camera_y = 0.0, 0.0
camera_zoom = 1.0

# Grid & displacement settings
WORLD_SIZE = 2000
MAP_RES = 2
DISPLACEMENT_SCALE = 1e5
BASE_SPACING = 50
TARGET_SPACING_PX = 50
MAX_REL_LEVELS = 2
R_MIN, R_MAX = 1, 4

# Star
class Body:
    def __init__(self, x, y, mass, radius=10.0, rs_visual=1e6):
        self.x = x
        self.y = y
        self.mass = mass
        self.radius = radius
        self.rs = 2 * 6.67430e-11 * mass / (3e8**2)
        self.rs_visual = rs_visual

star = Body(0.0, 0.0, 1.989e30, radius=12.0, rs_visual=1e6)

# Particle
class Particle:
    def __init__(self, x, y, color=(0,100,255), size=5):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.color = color
        self.size = size

    def update(self, dt, displacement_map, map_x, map_y):
        ix = np.clip(int((self.x - map_x[0])/MAP_RES), 0, displacement_map.shape[0]-2)
        iy = np.clip(int((self.y - map_y[0])/MAP_RES), 0, displacement_map.shape[1]-2)
        dzdx = (displacement_map[ix+1, iy] - displacement_map[ix, iy]) / MAP_RES
        dzdy = (displacement_map[ix, iy+1] - displacement_map[ix, iy]) / MAP_RES
        speed = 50.0
        self.vx += dzdx * speed * dt
        self.vy += dzdy * speed * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

    def draw(self, camera_x, camera_y, camera_zoom):
        sx = (self.x - camera_x) * camera_zoom + WIDTH*0.5
        sy = (self.y - camera_y) * camera_zoom + HEIGHT*0.5
        r = max(1, int(self.size * camera_zoom))
        if -r <= sx <= WIDTH+r and -r <= sy <= HEIGHT+r:
            pygame.draw.circle(screen, self.color, (int(sx), int(sy)), r)

# Precompute displacement map
def generate_displacement_map(body):
    N = int(WORLD_SIZE/MAP_RES)
    displacement_map = np.zeros((N,N))
    map_x = np.linspace(-WORLD_SIZE/2, WORLD_SIZE/2, N)
    map_y = np.linspace(-WORLD_SIZE/2, WORLD_SIZE/2, N)
    for i, x in enumerate(map_x):
        for j, y in enumerate(map_y):
            dx = x - body.x
            dy = y - body.y
            r = math.hypot(dx, dy) + 1e-9
            displacement_map[i,j] = body.rs_visual / r
    return displacement_map, map_x, map_y

displacement_map, map_x, map_y = generate_displacement_map(star)

# Adaptive level helpers
def compute_current_level(zoom):
    val = (BASE_SPACING * zoom) / TARGET_SPACING_PX
    return round(math.log2(val)) if val > 0 else 0

def level_to_spacing(level):
    return BASE_SPACING / (2 ** level)

def relative_radius(rel_level):
    radius = R_MAX * (0.7 ** rel_level)
    return max(R_MIN, radius)

# Grid rendering
def draw_grid(camera_x, camera_y, camera_zoom, displacement_map, map_x, map_y):
    L_current = compute_current_level(camera_zoom)
    for rel in range(MAX_REL_LEVELS):
        L = L_current + rel
        spacing = level_to_spacing(L)
        radius = relative_radius(rel)

        left = camera_x - WIDTH/2 / camera_zoom
        right = camera_x + WIDTH/2 / camera_zoom
        top = camera_y - HEIGHT/2 / camera_zoom
        bottom = camera_y + HEIGHT/2 / camera_zoom

        x = left - left % spacing
        while x <= right:
            y = top - top % spacing
            while y <= bottom:
                ix = np.clip(int((x - map_x[0])/MAP_RES), 0, displacement_map.shape[0]-2)
                iy = np.clip(int((y - map_y[0])/MAP_RES), 0, displacement_map.shape[1]-2)
                z = displacement_map[ix, iy]
                f = 1 / (1 + z / DISPLACEMENT_SCALE)
                dx = star.x + (x - star.x) * f
                dy = star.y + (y - star.y) * f
                sx = (dx - camera_x) * camera_zoom + WIDTH/2 
                ##Comment about what is happening here
                ## The screen coordinates (sx, sy) are calculated by transforming the world coordinates (dx, dy) using the camera position and zoom level.
                sy = (dy - camera_y) * camera_zoom + HEIGHT/2
                pygame.draw.circle(screen, (200,200,200), (int(sx), int(sy)), int(radius))
                y += spacing
            x += spacing

# Example particles
particles = [Particle(100,0), Particle(-100,50), Particle(0,-150), Particle(200,-100), Particle(300,200), Particle(400,300)]

# Panning
panning = False
pan_last_mouse = (0,0)

# Main loop
running = True
while running:
    dt = clock.tick(60)/1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            before_wx = (mx - WIDTH/2)/camera_zoom + camera_x
            before_wy = (my - HEIGHT/2)/camera_zoom + camera_y
            factor = 1.1**event.y
            camera_zoom *= factor
            camera_zoom = max(0.001, min(1000.0, camera_zoom))
            camera_x = before_wx - (mx - WIDTH/2)/camera_zoom
            camera_y = before_wy - (my - HEIGHT/2)/camera_zoom
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

    keys = pygame.key.get_pressed()
    move_speed = 400 / camera_zoom * dt
    if keys[pygame.K_LEFT]: camera_x -= move_speed
    if keys[pygame.K_RIGHT]: camera_x += move_speed
    if keys[pygame.K_UP]: camera_y -= move_speed
    if keys[pygame.K_DOWN]: camera_y += move_speed

    # Update particles
    for p in particles:
        p.update(dt, displacement_map, map_x, map_y)

    # Draw
    screen.fill((10,10,10))
    draw_grid(camera_x, camera_y, camera_zoom, displacement_map, map_x, map_y)

    # Draw star
    sx = (star.x - camera_x) * camera_zoom + WIDTH/2
    sy = (star.y - camera_y) * camera_zoom + HEIGHT/2
    pygame.draw.circle(screen, (0,200,0), (int(sx), int(sy)), max(2,int(star.radius*camera_zoom)))

    # Draw particles
    for p in particles:
        p.draw(camera_x, camera_y, camera_zoom)

    pygame.display.flip()

pygame.quit()
sys.exit()
