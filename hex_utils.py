import math
from settings import HEX_SIZE

def axial_to_pixel(q, r, zoom, cam_x, cam_y, screen_width, screen_height):
    base_x = HEX_SIZE * (3 / 2 * q) * zoom
    base_y = HEX_SIZE * (math.sqrt(3) * (r + q / 2)) * zoom
    x = base_x + cam_x + screen_width / 2
    y = base_y + cam_y + screen_height / 2
    return int(x), int(y)

def pixel_to_axial(mx, my, zoom, cam_x, cam_y, screen_width, screen_height, grid):
    world_x = (mx - screen_width / 2 - cam_x) / zoom
    world_y = (my - screen_height / 2 - cam_y) / zoom
    closest = None
    min_dist = float('inf')
    for q, r in grid:
        cx = HEX_SIZE * (3 / 2 * q)
        cy = HEX_SIZE * (math.sqrt(3) * (r + q / 2))
        dist = math.hypot(cx - world_x, cy - world_y)
        if dist < min_dist:
            min_dist = dist
            closest = (q, r)
    if min_dist < HEX_SIZE:
        return closest
    return None

def hex_distance(a, b):
    qa, ra = a
    qb, rb = b
    sa = -qa - ra
    sb = -qb - rb
    return (abs(qa - qb) + abs(ra - rb) + abs(sa - sb)) // 2

def get_neighbors(q, r, grid):
    directions = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
    return [(q + dq, r + dr) for dq, dr in directions if (q + dq, r + dr) in grid]
