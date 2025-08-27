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
TARGET_SPACING_PX = 50.0  # preferred on-screen spacing for "current level"
MAX_REL_LEVELS = 2     # number of finer levels to draw
R_MIN, R_MAX = 1.0, 5.0
DISPLACEMENT_THRESHOLD = 10000


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
    def __init__(self, x, y, mass, radius=5.0,
                 displacement_threshold=200, rs_visual=None,
                 movable=False, vx=0.0, vy=0.0):
        self.x = float(x)
        self.y = float(y)
        self.mass = mass
        self.radius = radius

        # real schwarzschild radius (for reference)
        self.rs = 2 * 6.67430e-11 * mass / (3e8**2)

        # visual exaggeration
        if rs_visual is not None:
            self.rs_visual = float(rs_visual)
        else:
            self.rs_visual = 1e3 * self.rs

        self.displacement_threshold = displacement_threshold

        # movement properties (if movable True)
        self.movable = bool(movable)
        self.vx = float(vx)
        self.vy = float(vy)
        self.speed = math.hypot(self.vx, self.vy) if (self.vx or self.vy) else 0.0

        # steering parameters (tune for stable orbits)
        self.steering_K = 0.8         # how strongly slope steers direction
        self.max_turn_rate = math.radians(180)  # rad/s cap
        self.damping = 0.0            # optional small damping (0..1) to remove drift

    def draw(self, camera_x, camera_y, camera_zoom):
        sx = (self.x - camera_x) * camera_zoom + WIDTH * 0.5
        sy = (self.y - camera_y) * camera_zoom + HEIGHT * 0.5
        screen_radius = max(1, int(round(self.radius * camera_zoom)))
        if -screen_radius <= sx <= WIDTH + screen_radius and -screen_radius <= sy <= HEIGHT + screen_radius:
            pygame.draw.circle(screen, (0, 200, 0), (int(sx), int(sy)), screen_radius)

    def update(self, dt, all_bodies):
        """If movable, steer according to gradZ from other bodies and integrate."""
        if not self.movable:
            return

        # speed and unit direction
        vmag = math.hypot(self.vx, self.vy)
        if vmag == 0:
            # initialize small random velocity to avoid zero division
            ang = random.random() * 2 * math.pi
            self.vx = math.cos(ang) * 1e-3
            self.vy = math.sin(ang) * 1e-3
            vmag = math.hypot(self.vx, self.vy)
        ux = self.vx / vmag
        uy = self.vy / vmag

        # compute gradient of Z from *other* bodies only
        other_bodies = [b for b in all_bodies if b is not self]
        gx, gy = gradZ_at((self.x, self.y), other_bodies)
        gmag = math.hypot(gx, gy)

        if gmag > 0:
            # downhill direction (toward reducing Z)
            dx = gx / gmag
            dy = gy / gmag

            # steering strength from slope magnitude
            strength = self.steering_K * min(1.0, gmag)  # clamp to [0,1]
            blended_x = ux * (1.0 - strength) + dx * strength
            blended_y = uy * (1.0 - strength) + dy * strength

            # normalize blended
            bmag = math.hypot(blended_x, blended_y)
            if bmag > 0:
                new_ux = blended_x / bmag
                new_uy = blended_y / bmag
            else:
                new_ux, new_uy = ux, uy

            # limit maximum turn rate
            dot = max(-1.0, min(1.0, ux * new_ux + uy * new_uy))
            ang = math.acos(dot)
            max_ang = self.max_turn_rate * dt
            if ang > max_ang and ang > 1e-8:
                sign = 1.0 if (ux * new_uy - uy * new_ux) >= 0 else -1.0
                cosA = math.cos(max_ang)
                sinA = math.sin(max_ang) * sign
                rx = ux * cosA - uy * sinA
                ry = ux * sinA + uy * cosA
                rmag = math.hypot(rx, ry)
                ux, uy = rx / rmag, ry / rmag
            else:
                ux, uy = new_ux, new_uy

        # keep magnitude of velocity (self.speed) if set, otherwise use vmag
        if self.speed == 0:
            self.speed = vmag if vmag > 0 else 1.0

        # optional damping (to avoid runaway)
        if self.damping:
            self.speed *= (1.0 - self.damping * dt)

        # update velocity and integrate position
        self.vx = ux * self.speed
        self.vy = uy * self.speed
        self.x += self.vx * dt
        self.y += self.vy * dt

# helpers used by Body
def gradZ_at(pos, bodies):
    """Gradient of visualization Z at world position pos (dZ/dx, dZ/dy).
       Excludes any contribution from bodies with zero rs_visual or beyond threshold.
    """
    x, y = pos
    gx = 0.0
    gy = 0.0
    for b in bodies:
        # skip if this body is None or if b.rs_visual==0
        dx = x - b.x
        dy = y - b.y
        r = math.hypot(dx, dy) + 1e-9
        if r > getattr(b, "displacement_threshold", 200):
            continue
        # Z contribution used in visualization was Z ~ b.rs_visual / r
        # grad dZ/dx = -b.rs_visual * dx / r^3
        inv_r3 = 1.0 / (r * r * r + 1e-12)
        gx += -b.rs_visual * dx * inv_r3
        gy += -b.rs_visual * dy * inv_r3
    return gx, gy




particles = [
    Particle(0, 0, size=5),
    Particle(50, 50, size=8),
    Particle(-100, 30, size=4)
]

# create bodies list
bodies = []

# central star (immobile)
star = Body(x=0.0, y=0.0, mass=1.989e30, radius=12.0,
            displacement_threshold=2000, rs_visual=1e6, movable=False)
bodies.append(star)

# orbiting body (movable)
r_orbit = 300.0  # world units distance from star
# compute initial tangential speed using v ≈ K * rs_visual / r  (geometry-based guess)
K_guess = 0.2
v_guess = K_guess * star.rs_visual / r_orbit
# if v_guess is tiny, scale it to a visually useful number
if v_guess < 1.0:
    v_guess = 80.0  # fallback base speed for visualization

moon = Body(x=r_orbit, y=0.0, mass=7.3e22, radius=4.0,
            displacement_threshold=1000, rs_visual=star.rs_visual * 0.1,
            movable=True, vx=0.0, vy=v_guess)

# set a desired constant speed for the moon (tweakable)
moon.speed = v_guess
moon.steering_K = K_guess
moon.max_turn_rate = math.radians(120)  # allow some turning

bodies.append(moon)

def displace_point(x, y, bodies):
    x_new, y_new = x, y
    for body in bodies:
        dx = x_new - body.x
        dy = y_new - body.y
        r = math.hypot(dx, dy)
        #if r > DISPLACEMENT_THRESHOLD:
        #    continue  # ignore this body
        if r == 0:
            continue
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

            # Draw the grid point if on screen
            if -10 <= sx <= WIDTH + 10 and -10 <= sy <= HEIGHT + 10:
                pygame.draw.circle(screen, (200,200,200), (int(round(sx)), int(round(sy))), int(radius_px))

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

    for b in bodies:
        b.update(dt, bodies)

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
