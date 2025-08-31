import pygame, sys, math, numpy as np

pygame.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 14)

camera_x, camera_y = 0.0, 0.0
camera_zoom = 1.0

WORLD_SIZE = 2000
MAP_RES = 4  # increased for performance
BASE_SPACING = 50
TARGET_SPACING_PX = 50
MAX_REL_LEVELS = 3
R_MIN, R_MAX = 1, 4

# METRIC GRID
N = int(WORLD_SIZE / MAP_RES)
x_axis = np.linspace(-WORLD_SIZE / 2, WORLD_SIZE / 2, N)
y_axis = np.linspace(-WORLD_SIZE / 2, WORLD_SIZE / 2, N)
spacetime_map = np.zeros((N, N, 6))


# ----------------- STAR CLASS -----------------
class Star:
	def __init__(self, x_position, y_position, mass, spin=0.0, radius=10, color=(255, 200, 50), epsilon=0.01):
		self.x = x_position
		self.y = y_position
		self.mass = mass
		self.spin = spin
		self.radius = radius
		self.color = color
		self.epsilon = epsilon
		self.max_effect_radius = self.radius / self.epsilon
		self.needs_update = True  # flag to update spacetime map

	def add_metric_to_grid(self, spacetime_map):
		if not self.needs_update:
			return  # skip if already applied

		# Compute bounding box indices
		ix_min = max(0, int((self.x - self.max_effect_radius + WORLD_SIZE / 2) / MAP_RES))
		ix_max = min(N - 1, int((self.x + self.max_effect_radius + WORLD_SIZE / 2) / MAP_RES))
		iy_min = max(0, int((self.y - self.max_effect_radius + WORLD_SIZE / 2) / MAP_RES))
		iy_max = min(N - 1, int((self.y + self.max_effect_radius + WORLD_SIZE / 2) / MAP_RES))

		# Vectorized calculation
		xs = x_axis[ix_min:ix_max + 1][:, None]
		ys = y_axis[iy_min:iy_max + 1][None, :]
		dx = xs - self.x
		dy = ys - self.y
		r2 = dx ** 2 + dy ** 2
		r = np.sqrt(r2) + 1e-6

		mask = r <= self.max_effect_radius
		if not np.any(mask):
			return

		g_tt = -self.mass / r
		g_xx = 1 + self.mass / (r2 + 1)
		g_yy = 1 + self.mass / (r2 + 1)
		g_xy = (dx * dy) / (r2 + 1) * self.mass * 0.01
		frame_strength = self.spin * self.mass / (r2 + 1)
		frame_drag_x = -dy / r * frame_strength
		frame_drag_y = dx / r * frame_strength

		# Apply mask
		g_tt *= mask
		g_xx *= mask
		g_yy *= mask
		g_xy *= mask
		frame_drag_x *= mask
		frame_drag_y *= mask

		spacetime_map[ix_min:ix_max + 1, iy_min:iy_max + 1, 0] += g_tt
		spacetime_map[ix_min:ix_max + 1, iy_min:iy_max + 1, 1] += g_xx
		spacetime_map[ix_min:ix_max + 1, iy_min:iy_max + 1, 2] += g_yy
		spacetime_map[ix_min:ix_max + 1, iy_min:iy_max + 1, 3] += g_xy
		spacetime_map[ix_min:ix_max + 1, iy_min:iy_max + 1, 4] += frame_drag_x
		spacetime_map[ix_min:ix_max + 1, iy_min:iy_max + 1, 5] += frame_drag_y

		self.needs_update = False  # mark as updated

	def draw(self, screen, camera_x, camera_y, camera_zoom):
		screen_x = (self.x - camera_x) * camera_zoom + WIDTH / 2
		screen_y = (self.y - camera_y) * camera_zoom + HEIGHT / 2
		pygame.draw.circle(screen, self.color, (int(screen_x), int(screen_y)), int(self.radius * camera_zoom))


# ----------------- BODY CLASS -----------------
class Body:
    def __init__(self, x_position, y_position, mass=1.0, color=(0, 255, 0)):
        self.x = x_position
        self.y = y_position
        self.mass = mass
        self.vx = 0.0
        self.vy = 0.0
        self.color = color

    def update(self, dt, spacetime_map):
        """
        Update body velocity and position by sampling the local spacetime metric.
        Acceleration is derived from the gradient of g_tt (simplified Newtonian analogy).
        """
        # Map world position to nearest grid index
        ix = int((self.x + WORLD_SIZE / 2) / MAP_RES)
        iy = int((self.y + WORLD_SIZE / 2) / MAP_RES)

        # Clamp indices to allow finite differences
        ix = min(max(ix, 1), N - 2)
        iy = min(max(iy, 1), N - 2)

        # Finite differences to approximate gradient of g_tt
        g_tt_center = spacetime_map[ix, iy, 0]
        g_tt_xplus = spacetime_map[ix + 1, iy, 0]
        g_tt_xminus = spacetime_map[ix - 1, iy, 0]
        g_tt_yplus = spacetime_map[ix, iy + 1, 0]
        g_tt_yminus = spacetime_map[ix, iy - 1, 0]

        grad_x = (g_tt_xplus - g_tt_xminus) / (2 * MAP_RES)
        grad_y = (g_tt_yplus - g_tt_yminus) / (2 * MAP_RES)

        # Convert gradient into acceleration
        force_scale = 20000.0  # tweak for visible effect
        ax = -grad_x * force_scale
        ay = -grad_y * force_scale

        # Update velocity
        self.vx += ax * dt
        self.vy += ay * dt

        # Update position
        self.x += self.vx * dt
        self.y += self.vy * dt

    def add_velocity_towards(self, target_x, target_y, speed):
        """Add velocity towards a given world position (e.g., mouse click)."""
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx**2 + dy**2) + 1e-6
        self.vx += speed * dx / distance
        self.vy += speed * dy / distance

    def draw(self, screen, camera_x, camera_y, camera_zoom):
        screen_x = (self.x - camera_x) * camera_zoom + WIDTH / 2
        screen_y = (self.y - camera_y) * camera_zoom + HEIGHT / 2
        pygame.draw.circle(screen, self.color, (int(screen_x), int(screen_y)), 6)



# ----------------- GRID DRAWING -----------------
def compute_current_level(zoom):
	val = (BASE_SPACING * zoom) / TARGET_SPACING_PX
	return round(math.log2(val)) if val > 0 else 0


def level_to_spacing(level):
	return BASE_SPACING / (2 ** level)


def relative_radius(rel_level):
	radius = R_MAX * (0.7 ** rel_level)
	return max(R_MIN, radius)


def draw_grid(camera_x, camera_y, camera_zoom):
	L_current = compute_current_level(camera_zoom)
	for rel in range(MAX_REL_LEVELS):
		L = L_current + rel
		spacing = level_to_spacing(L)
		radius = relative_radius(rel)

		left = camera_x - WIDTH / 2 / camera_zoom
		right = camera_x + WIDTH / 2 / camera_zoom
		top = camera_y - HEIGHT / 2 / camera_zoom
		bottom = camera_y + HEIGHT / 2 / camera_zoom

		x = left - left % spacing
		while x <= right:
			y = top - top % spacing
			while y <= bottom:
				ix = int((x + WORLD_SIZE / 2) / MAP_RES)
				iy = int((y + WORLD_SIZE / 2) / MAP_RES)

				ix = min(max(ix, 1), N - 2)
				iy = min(max(iy, 1), N - 2)

				g_tt, g_xx, g_yy, g_xy, frame_drag_x, frame_drag_y = spacetime_map[ix, iy]

				dx = x
				dy = y
				r = math.sqrt(dx * dx + dy * dy) + 1e-6

				displacement_x = -g_tt * (dx / r) * g_xx + g_xy * dy + frame_drag_x
				displacement_y = -g_tt * (dy / r) * g_yy + g_xy * dx + frame_drag_y

				warped_x = x + displacement_x
				warped_y = y + displacement_y

				screen_x = (warped_x - camera_x) * camera_zoom + WIDTH / 2
				screen_y = (warped_y - camera_y) * camera_zoom + HEIGHT / 2

				pygame.draw.circle(screen, (200, 200, 200), (int(screen_x), int(screen_y)), int(radius))

				y += spacing
			x += spacing


# ----------------- DEBUG -----------------
def write_camera_pos_zoom_on_screen():
	camera_pos_text = f"Camera Position: ({camera_x:.2f}, {camera_y:.2f})"
	camera_zoom_text = f"Camera Zoom: {camera_zoom:.2f}"
	text_surface = font.render(camera_pos_text, True, (255, 255, 255))
	screen.blit(text_surface, (10, 10))
	text_surface = font.render(camera_zoom_text, True, (255, 255, 255))
	screen.blit(text_surface, (10, 30))


# ----------------- MAIN LOOP -----------------
panning = False
pan_last_mouse = (0, 0)

# Create a star instance
star1 = Star(x_position=100, y_position=-50, mass=10.0, spin=2.0)

body1 = Body(x_position=-200, y_position=0)


running = True
while running:
	dt = clock.tick(60) / 1000.0

	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			running = False
		elif event.type == pygame.MOUSEWHEEL:
			mx, my = pygame.mouse.get_pos()
			before_wx = (mx - WIDTH / 2) / camera_zoom + camera_x
			before_wy = (my - HEIGHT / 2) / camera_zoom + camera_y
			factor = 1.1 ** event.y
			camera_zoom *= factor
			camera_zoom = max(0.001, min(1000.0, camera_zoom))
			camera_x = before_wx - (mx - WIDTH / 2) / camera_zoom
			camera_y = before_wy - (my - HEIGHT / 2) / camera_zoom
		elif event.type == pygame.MOUSEMOTION:
			if panning:
				mx, my = pygame.mouse.get_pos()
				dx, dy = mx - pan_last_mouse[0], my - pan_last_mouse[1]
				camera_x -= dx / camera_zoom
				camera_y -= dy / camera_zoom
				pan_last_mouse = (mx, my)      
		elif event.type == pygame.MOUSEBUTTONDOWN:
			if event.button == 1:  # Left mouse button
				mx, my = pygame.mouse.get_pos()
				world_x = (mx - WIDTH/2) / camera_zoom + camera_x
				world_y = (my - HEIGHT/2) / camera_zoom + camera_y
				body1.add_velocity_towards(world_x, world_y, speed=100.0)


	keys = pygame.key.get_pressed()
	move_speed = 400 / camera_zoom * dt
	if keys[pygame.K_LEFT]:
		camera_x -= move_speed
	if keys[pygame.K_RIGHT]:
		camera_x += move_speed
	if keys[pygame.K_UP]:
		camera_y -= move_speed
	if keys[pygame.K_DOWN]:
		camera_y += move_speed

	# Clear screen
	screen.fill((10, 10, 10))

	# Apply star metric once
	star1.add_metric_to_grid(spacetime_map)
	star1.draw(screen, camera_x, camera_y, camera_zoom)

	body1.update(dt, spacetime_map)
	body1.draw(screen, camera_x, camera_y, camera_zoom)


	# Draw grid warped by spacetime
	draw_grid(camera_x, camera_y, camera_zoom)

	write_camera_pos_zoom_on_screen()
	pygame.display.flip()

pygame.quit()
sys.exit()
