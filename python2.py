import pygame, sys, math, numpy as np

pygame.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 14)

camera_x, camera_y = 0.0, 0.0

camera_zoom = 1.0

WORLD_SIZE = 2000
MAP_RES = 2
BASE_SPACING = 50
TARGET_SPACING_PX = 50
MAX_REL_LEVELS = 2
R_MIN, R_MAX = 1, 4


#DRAW GRID
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
				screen_x = (x - camera_x) * camera_zoom + WIDTH / 2
				screen_y = (y - camera_y) * camera_zoom + HEIGHT / 2
				pygame.draw.circle(screen, (200,200,200), (int(screen_x), int(screen_y)), int(radius))
				y += spacing
			x += spacing


#DEBUG FUNCTIONS
def write_camera_pos_zoom_on_screen():
	camera_pos_text = f"Camera Position: ({camera_x:.2f}, {camera_y:.2f})"
	camera_zoom_text = f"Camera Zoom: {camera_zoom:.2f}"
	text_surface = font.render(camera_pos_text, True, (255, 255, 255))
	screen.blit(text_surface, (10, 10))
	text_surface = font.render(camera_zoom_text, True, (255, 255, 255))
	screen.blit(text_surface, (10, 30))

#MAIN LOOP
panning = False
pan_last_mouse = (0, 0)

running = True
while running:
	dt = clock.tick(60)/1000.0

	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			running = False
		elif event.type == pygame.MOUSEWHEEL:
			mx, my = pygame.mouse.get_pos()
			before_wx = (mx - WIDTH/2) / camera_zoom + camera_x
			before_wy = (my - HEIGHT/2) / camera_zoom + camera_y
			factor = 1.1**event.y
			camera_zoom *= factor
			camera_zoom = max(0.001, min(1000.0, camera_zoom))
			camera_x = before_wx - (mx - WIDTH/2)/camera_zoom
			camera_y = before_wy - (my - HEIGHT/2)/camera_zoom
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

	screen.fill((10,10,10))
	draw_grid(camera_x, camera_y, camera_zoom)

	write_camera_pos_zoom_on_screen()

	pygame.display.flip()

pygame.quit()
sys.exit()