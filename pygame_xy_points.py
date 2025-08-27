import pygame, math
pygame.init()

# Screen setup
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Grid setup
BASE_RES = 40
zoom = 1.0

# Camera position in world space
cam_x, cam_y = 0.0, 0.0

# Screen-space cutoff values
MIN_SPACING = 25     # don't draw dots smaller than this in pixels
MAX_SPACING = 100   # don't draw dots bigger than this in pixels


def wrap(pos, max_val):
    return ((pos % max_val) + max_val) % max_val


running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEWHEEL:
            # Smooth zoom
            zoom *= 1.0 + event.y * 0.05
            zoom = max(0.05, min(zoom, 50))

    # Camera movement with arrow keys (in world units)
    keys = pygame.key.get_pressed()
    cam_speed = 10 / zoom  # move consistently regardless of zoom
    if keys[pygame.K_LEFT]:
        cam_x -= cam_speed
    if keys[pygame.K_RIGHT]:
        cam_x += cam_speed
    if keys[pygame.K_UP]:
        cam_y -= cam_speed
    if keys[pygame.K_DOWN]:
        cam_y += cam_speed

    screen.fill((20, 20, 20))

    # Determine visible world bounds
    world_x_min = cam_x
    world_x_max = cam_x + WIDTH / zoom
    world_y_min = cam_y
    world_y_max = cam_y + HEIGHT / zoom

    # Draw multiple grid levels
    max_levels = 6

    current_level = zoom

    levels_to_draw = [current_level - 1, current_level, current_level + 1]

    for level in levels_to_draw:
        # World-space spacing
        spacing_world = BASE_RES * (2 ** level)
        print(spacing_world)
        # Screen-space spacing
        spacing_screen = spacing_world * zoom

        print(spacing_screen)

        spacing_screen_wrapped = wrap(spacing_screen, MAX_SPACING)

        # Skip levels that are too dense or too sparse
        if spacing_screen_wrapped < MIN_SPACING or spacing_screen_wrapped > MAX_SPACING:
            continue
    

        # Compute integer world coords for visible dots
        start_i = math.floor(world_x_min / spacing_screen)
        end_i   = math.ceil(world_x_max / spacing_screen)
        start_j = math.floor(world_y_min / spacing_screen)
        end_j   = math.ceil(world_y_max / spacing_screen)

        for i in range(start_i, end_i):
            for j in range(start_j, end_j):
                pygame.draw.circle(screen, (200, 200, 200, 1), (i * spacing_screen_wrapped - cam_x, j * spacing_screen_wrapped - cam_y), 2)

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
