import pygame
import math
import time
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, players, unit_types, sea_units, costs, unit_digits, capacity, movements, max_fuel, city_max_hp, max_stack, min_city_hp, city_attack, city_defense, city_range, unit_stats, HEX_SIZE
from sounds import init_sounds
from terrain_generator import generate_grid_and_terrain
from players import generate_cities_and_coastal, assign_starting_cities_and_units
from hex_utils import pixel_to_axial, get_neighbors, hex_distance, axial_to_pixel
from units import get_reachable, get_fuel_range, find_path, is_loadable_transport_hex, is_hex_occupied, get_allowed
from rendering import draw_screen
from game_logic import has_enemy_or_neutral_city_near, get_next_movable, center_on_unit, move_unit_along_path, battle, check_win, remove_unit_and_loads, center_on_unit_if_needed

class GameState:
    def __init__(self):
        self.turn = 1
        self.current_player = players[0]
        self.selected_unit = None
        self.reachable = set()
        self.fuel_range = set()
        self.menu_active = False
        self.menu_city = None
        self.menu_scroll = 0
        self.dragging = False
        self.last_mouse_pos = None
        self.path_preview = False
        self.preview_path = None
        self.target_hex = None
        self.hold_start = None
        self.hold_hex = None
        self.show_path = False
        self.path_to_show = None
        self.attackable_hexes = []
        self.attacked_cities = set()
        self.zoom = 1.0
        self.cam_x = 0
        self.cam_y = 0
        self.grid, self.terrain = generate_grid_and_terrain()
        self.cities, self.coastal_cities = generate_cities_and_coastal(self.grid, self.terrain)
        self.city_owners, self.units, self.transport_loads, self.productions, self.city_hp, self.start_cities = assign_starting_cities_and_units(self.cities, self.coastal_cities, players, self.grid, unit_stats, movements)
        self.last_info_hex = None
        self.last_selected_unit = None
        self.drag_hold_start = None
        self.highlighted_hex = None
        self.drag_start_pos = None

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("G-Warz")
error_sound, good_sound = init_sounds()

font = pygame.font.SysFont(None, 30)
bold_font = pygame.font.SysFont(None, 35, bold=True)

state = GameState()

def update_selected_unit(state, center=False):
    """Update reachable, fuel_range, and attackable hexes for the selected unit."""
    if state.selected_unit:
        state.reachable = get_reachable(state.selected_unit, state.grid, state.terrain, state.cities, state.city_owners, state.units, state.coastal_cities, state.transport_loads)
        state.fuel_range = get_fuel_range(state.selected_unit, state.grid, state.terrain)
        if center:
            state.cam_x, state.cam_y = center_on_unit_if_needed(state.selected_unit, state.cam_x, state.cam_y, state.zoom, SCREEN_WIDTH, SCREEN_HEIGHT, state.grid)
        state.attackable_hexes = [u['pos'] for u in state.units if u['owner'] != state.current_player and hex_distance(state.selected_unit['pos'], u['pos']) <= state.selected_unit['range'] and state.selected_unit['movement_left'] > 0]
        for c in state.cities:
            if state.city_owners[c] != state.current_player and state.selected_unit['movement_left'] > 0 and hex_distance(state.selected_unit['pos'], c) <= state.selected_unit['range']:
                if state.city_owners[c] is None and state.selected_unit['type'] == 'Infantry':
                    state.attackable_hexes.append(c)
                elif state.city_owners[c] is not None:
                    state.attackable_hexes.append(c)
        state.last_selected_unit = state.selected_unit
        state.last_info_hex = state.selected_unit['pos']
        # Always show path if it exists for the selected unit
        if 'path' in state.selected_unit:
            state.show_path = True
            state.path_to_show = state.selected_unit['path'][:]
            if state.selected_unit['path']:
                state.highlighted_hex = state.selected_unit['path'][-1]
        else:
            state.show_path = False
            state.path_to_show = None
            state.highlighted_hex = None
    else:
        state.reachable = set()
        state.fuel_range = set()
        state.attackable_hexes = []
        state.last_selected_unit = None
        state.last_info_hex = None
        state.show_path = False
        state.path_to_show = None
        state.highlighted_hex = None

def wake_sentry_units(state):
    """Wake sentry units if an enemy is within 1 hex at turn start."""
    for unit in state.units:
        if unit.get('sentry', False) and unit['owner'] == state.current_player:
            for n in get_neighbors(*unit['pos'], state.grid):
                for u in state.units:
                    if u['pos'] == n and u['owner'] != unit['owner']:
                        unit['sentry'] = False
                        unit['movement_left'] = movements[unit['type']]
                        good_sound.play()
                        break

# Initial setup
state.selected_unit = get_next_movable(state.units, state.transport_loads, player=state.current_player)
update_selected_unit(state, center=True)

# Main game loop
running = True
clock = pygame.time.Clock()
while running:
    mx, my = pygame.mouse.get_pos()
    hovered_hex = pixel_to_axial(mx, my, state.zoom, state.cam_x, state.cam_y, SCREEN_WIDTH, SCREEN_HEIGHT, state.grid)
    if pygame.mouse.get_pressed()[0] and state.hold_start:
        hold_time = pygame.time.get_ticks() - state.hold_start
        if hold_time > 500 and not state.path_preview and state.selected_unit is not None:
            state.path_preview = True
            current_hex = pixel_to_axial(mx, my, state.zoom, state.cam_x, state.cam_y, SCREEN_WIDTH, SCREEN_HEIGHT, state.grid)
            if current_hex:
                state.target_hex = current_hex
                path = find_path(state.selected_unit['pos'], state.target_hex, state.selected_unit, state.grid, state.terrain, state.cities, state.city_owners, state.units, state.transport_loads, capacity, state.coastal_cities)
                if path:
                    state.preview_path = path
                else:
                    state.preview_path = None
    if state.path_preview:
        mx, my = pygame.mouse.get_pos()
        scroll_speed = 5
        if mx < 50:
            state.cam_x += scroll_speed
        elif mx > SCREEN_WIDTH - 50:
            state.cam_x -= scroll_speed
        if my < 50:
            state.cam_y += scroll_speed
        elif my > SCREEN_HEIGHT - 50:
            state.cam_y -= scroll_speed

    state.last_info_hex = draw_screen(screen, state.grid, state.terrain, state.cities, state.city_owners, state.productions, state.city_hp, state.fuel_range, state.reachable, state.attackable_hexes, state.units, state.transport_loads, state.selected_unit, state.zoom, state.cam_x, state.cam_y, SCREEN_WIDTH, SCREEN_HEIGHT, state.path_preview, state.preview_path, state.target_hex, state.show_path, state.path_to_show, state.turn, state.current_player, state.menu_active, state.menu_city, unit_types, sea_units, state.coastal_cities, font, bold_font, state.menu_scroll, hovered_hex, state.last_info_hex, state.last_selected_unit, state.highlighted_hex)
    pygame.display.flip()
    clock.tick(60)

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE:
                next_index = (players.index(state.current_player) + 1) % len(players)
                state.current_player = players[next_index]
                for unit in state.units:
                    if unit['owner'] == state.current_player:
                        unit['movement_left'] = movements[unit['type']]
                wake_sentry_units(state)
                for unit in [u for u in state.units if u['owner'] == state.current_player and not u.get('sentry', False)]:
                    state.cam_x, state.cam_y = center_on_unit_if_needed(unit, state.cam_x, state.cam_y, state.zoom, SCREEN_WIDTH, SCREEN_HEIGHT, state.grid)
                    state.cam_x, state.cam_y, running = move_unit_along_path(unit, state.units, state.transport_loads, state.terrain, state.cities, state.city_owners, state.grid, capacity, max_stack, players, screen, bold_font, state.attacked_cities, state.coastal_cities, state.zoom, SCREEN_WIDTH, SCREEN_HEIGHT, font, state.turn, state.menu_active, state.menu_city, unit_types, sea_units, state.productions, state.city_hp, state.fuel_range, state.reachable, state.attackable_hexes, state.selected_unit, state.path_preview, state.preview_path, state.target_hex, state.show_path, state.path_to_show, state.cam_x, state.cam_y, state.current_player, state.menu_scroll, hovered_hex, good_sound)
                    if not running:
                        break
                if not running:
                    break
                if state.current_player == players[0]:
                    fighters = [u for u in state.units if u['type'] == 'Fighter']
                    for fighter in fighters:
                        if fighter['fuel'] is not None:
                            if fighter['pos'] in state.cities and state.city_owners[fighter['pos']] == fighter['owner']:
                                fighter['fuel'] = max_fuel['Fighter']
                            else:
                                fighter['fuel'] -= 1
                                if fighter['fuel'] <= 0:
                                    error_sound.play()
                                    remove_unit_and_loads(fighter, state.units, state.transport_loads)
                                    if state.selected_unit == fighter:
                                        state.selected_unit = None
                                        update_selected_unit(state)
                    carriers_planes = [u for u in state.units if u['type'] in ['AirCarrier', 'TransportPlane']]
                    for cp in carriers_planes:
                        if cp['fuel'] is not None:
                            if cp['pos'] in state.cities and state.city_owners[cp['pos']] == cp['owner']:
                                cp['fuel'] = max_fuel[cp['type']]
                            else:
                                cp['fuel'] -= 1
                                if cp['fuel'] <= 0:
                                    error_sound.play()
                                    remove_unit_and_loads(cp, state.units, state.transport_loads)
                                    if state.selected_unit == cp:
                                        state.selected_unit = None
                                        update_selected_unit(state)
                    for unit in state.units:
                        if not unit.get('did_move', False) and unit not in [lu for t in state.transport_loads.values() for lu in t]:
                            heal = max(1, int(0.1 * unit['max_hp']))
                            if unit['pos'] in state.cities and state.city_owners[unit['pos']] == unit['owner']:
                                heal = max(1, int(0.2 * unit['max_hp']))
                            unit['hp'] = min(unit['max_hp'], unit['hp'] + heal)
                        unit['did_move'] = False
                    for c in state.cities:
                        if state.city_owners[c] is None:
                            continue
                        p = state.productions[c]
                        if p['turns_left'] > 0:
                            p['turns_left'] -= 1
                            if p['turns_left'] == 0:
                                utype = p['unit']
                                stats = unit_stats[utype]
                                new_unit = {
                                    'pos': c,
                                    'type': utype,
                                    'movement_left': 0,
                                    'owner': state.city_owners[c],
                                    'fuel': max_fuel.get(utype, None),
                                    'hp': stats['max_hp'],
                                    'max_hp': stats['max_hp'],
                                    'attack': stats['attack'],
                                    'defense': stats['defense'],
                                    'range': stats['range'],
                                    'did_move': False,
                                    'sentry': False
                                }
                                state.units.append(new_unit)
                                if new_unit['type'] in capacity:
                                    state.transport_loads[id(new_unit)] = []
                                p['unit'] = None
                                p['turns_left'] = 0
                    state.turn += 1
                    running = check_win(state.cities, state.city_owners, players, screen, bold_font, running)
                state.selected_unit = get_next_movable(state.units, state.transport_loads, player=state.current_player)
                update_selected_unit(state, center=True)
            elif event.key == pygame.K_UP:
                state.cam_y += 50 * state.zoom
            elif event.key == pygame.K_DOWN:
                state.cam_y -= 50 * state.zoom
            elif event.key == pygame.K_LEFT:
                state.cam_x += 50 * state.zoom
            elif event.key == pygame.K_RIGHT:
                state.cam_x -= 50 * state.zoom
            elif event.key == pygame.K_c:
                if state.show_path:
                    if 'path' in state.selected_unit:
                        del state.selected_unit['path']
                        state.show_path = False
                        state.path_to_show = None
                        state.highlighted_hex = None
                else:
                    if state.selected_unit:
                        state.cam_x, state.cam_y = center_on_unit_if_needed(state.selected_unit, state.cam_x, state.cam_y, state.zoom, SCREEN_WIDTH, SCREEN_HEIGHT, state.grid)
                    else:
                        state.cam_x, state.cam_y = center_on_unit_if_needed({'pos': state.start_cities[players.index(state.current_player)]}, state.cam_x, state.cam_y, state.zoom, SCREEN_WIDTH, SCREEN_HEIGHT, state.grid)
            elif event.key == pygame.K_w:
                if state.selected_unit:
                    state.selected_unit = get_next_movable(state.units, state.transport_loads, state.selected_unit, state.current_player)
                    update_selected_unit(state, center=True)
            elif event.key == pygame.K_s:
                if state.selected_unit:
                    if event.mod & pygame.KMOD_SHIFT:  # Shift+S for sentry
                        if state.selected_unit['type'] not in ['Fighter', 'TransportPlane', 'AirCarrier'] and state.selected_unit['movement_left'] > 0:
                            state.selected_unit['sentry'] = True
                            state.selected_unit['movement_left'] = 0
                            good_sound.play()
                    else:  # S for skip
                        state.selected_unit['movement_left'] = 0
                    state.selected_unit = get_next_movable(state.units, state.transport_loads, state.selected_unit, state.current_player)
                    update_selected_unit(state, center=True)
            elif event.key == pygame.K_i:
                if state.selected_unit and state.selected_unit['type'] == 'TransportPlane' and state.selected_unit['pos'] in state.cities and len(state.transport_loads.get(id(state.selected_unit), [])) < capacity['TransportPlane']['max']:
                    infantry = next((u for u in state.units if u['pos'] == state.selected_unit['pos'] and u['type'] == 'Infantry' and u['owner'] == state.current_player), None)
                    if infantry:
                        state.transport_loads.setdefault(id(state.selected_unit), []).append(infantry)
                        state.units.remove(infantry)
                        good_sound.play()
                    else:
                        error_sound.play()
                elif state.selected_unit and state.selected_unit['type'] == 'TransportShip' and len(state.transport_loads.get(id(state.selected_unit), [])) < capacity['TransportShip']['max']:
                    load_pos = state.selected_unit['pos'] if state.selected_unit['pos'] in state.cities and state.city_owners[state.selected_unit['pos']] == state.current_player else next((n for n in get_neighbors(*state.selected_unit['pos'], state.grid) if n in state.cities and state.city_owners[n] == state.current_player), None)
                    if load_pos:
                        infantry = next((u for u in state.units if u['pos'] == load_pos and u['type'] == 'Infantry' and u['owner'] == state.current_player), None)
                        if infantry:
                            state.transport_loads.setdefault(id(state.selected_unit), []).append(infantry)
                            state.units.remove(infantry)
                            good_sound.play()
                        else:
                            error_sound.play()
                    else:
                        error_sound.play()
            elif event.key == pygame.K_t:
                if state.selected_unit and state.selected_unit['type'] == 'TransportPlane' and state.selected_unit['pos'] in state.cities and len(state.transport_loads.get(id(state.selected_unit), [])) < capacity['TransportPlane']['max']:
                    tank = next((u for u in state.units if u['pos'] == state.selected_unit['pos'] and u['type'] == 'Tank' and u['owner'] == state.current_player), None)
                    if tank:
                        state.transport_loads.setdefault(id(state.selected_unit), []).append(tank)
                        state.units.remove(tank)
                        good_sound.play()
                    else:
                        error_sound.play()
                elif state.selected_unit and state.selected_unit['type'] == 'TransportShip' and len(state.transport_loads.get(id(state.selected_unit), [])) < capacity['TransportShip']['max']:
                    load_pos = state.selected_unit['pos'] if state.selected_unit['pos'] in state.cities and state.city_owners[state.selected_unit['pos']] == state.current_player else next((n for n in get_neighbors(*state.selected_unit['pos'], state.grid) if n in state.cities and state.city_owners[n] == state.current_player), None)
                    if load_pos:
                        tank = next((u for u in state.units if u['pos'] == load_pos and u['type'] == 'Tank' and u['owner'] == state.current_player), None)
                        if tank:
                            state.transport_loads.setdefault(id(state.selected_unit), []).append(tank)
                            state.units.remove(tank)
                            good_sound.play()
                        else:
                            error_sound.play()
                    else:
                        error_sound.play()
            elif event.key == pygame.K_u:
                if state.selected_unit and state.selected_unit['type'] in ['TransportShip', 'TransportPlane'] and state.selected_unit['movement_left'] > 0:
                    if state.selected_unit['type'] == 'TransportShip' and not (state.selected_unit['pos'] in state.cities and state.city_owners[state.selected_unit['pos']] == state.selected_unit['owner'] or any(state.terrain[n] == 'land' for n in get_neighbors(*state.selected_unit['pos'], state.grid))):
                        error_sound.play()
                        continue
                    if state.selected_unit['type'] == 'TransportPlane' and state.selected_unit['pos'] not in state.cities:
                        error_sound.play()
                        continue
                    unloaded = False
                    for u in state.transport_loads.get(id(state.selected_unit), []):
                        if is_hex_occupied(state.selected_unit['pos'], u['owner'], state.units, state.cities, state.city_owners, max_stack):
                            error_sound.play()
                            break
                        if state.terrain[state.selected_unit['pos']] in get_allowed(u['type']) or (state.selected_unit['pos'] in state.cities and state.city_owners[state.selected_unit['pos']] == u['owner']):
                            u['pos'] = state.selected_unit['pos']
                            u['movement_left'] = movements[u['type']]
                            u['sentry'] = False
                            state.units.append(u)
                            good_sound.play()
                            unloaded = True
                    state.transport_loads[id(state.selected_unit)] = []
                    if unloaded:
                        state.selected_unit['movement_left'] = max(0, state.selected_unit['movement_left'] - 1)
                        state.selected_unit = u if u['owner'] == state.current_player and u['movement_left'] > 0 else get_next_movable(state.units, state.transport_loads, None, state.current_player)
                        update_selected_unit(state, center=True)
                    else:
                        state.selected_unit = get_next_movable(state.units, state.transport_loads, None, state.current_player)
                        update_selected_unit(state, center=True)
        elif event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if state.menu_active:
                cx, cy = axial_to_pixel(*state.menu_city, state.zoom, state.cam_x, state.cam_y, SCREEN_WIDTH, SCREEN_HEIGHT)
                menu_x = min(max(cx + HEX_SIZE * state.zoom, 50), SCREEN_WIDTH - 250)
                menu_y = min(max(cy - 150, 50), SCREEN_HEIGHT - 300)
                menu_rect = pygame.Rect(menu_x, menu_y, 200, 300)
                if menu_rect.collidepoint(mx, my):
                    state.menu_scroll -= event.y * 20
                    state.menu_scroll = max(0, state.menu_scroll)
                    is_coastal = state.menu_city in state.coastal_cities
                    available_units = [ut for ut in unit_types if is_coastal or ut not in sea_units]
                    max_scroll = max(0, len(available_units) * 40 - 260)
                    state.menu_scroll = min(state.menu_scroll, max_scroll)
            else:
                old_zoom = state.zoom
                state.zoom += event.y * 0.1
                state.zoom = max(0.5, min(3.0, state.zoom))
                world_x = (mx - SCREEN_WIDTH / 2 - state.cam_x) / old_zoom
                world_y = (my - SCREEN_HEIGHT / 2 - state.cam_y) / old_zoom
                state.cam_x = mx - SCREEN_WIDTH / 2 - world_x * state.zoom
                state.cam_y = my - SCREEN_HEIGHT / 2 - world_y * state.zoom
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            clicked_hex = pixel_to_axial(mx, my, state.zoom, state.cam_x, state.cam_y, SCREEN_WIDTH, SCREEN_HEIGHT, state.grid)
            if event.button == 1:
                if state.menu_active:
                    cx, cy = axial_to_pixel(*state.menu_city, state.zoom, state.cam_x, state.cam_y, SCREEN_WIDTH, SCREEN_HEIGHT)
                    menu_x = min(max(cx + HEX_SIZE * state.zoom, 50), SCREEN_WIDTH - 250)
                    menu_y = min(max(cy - 150, 50), SCREEN_HEIGHT - 300)
                    p = state.productions[state.menu_city]
                    y_pos = menu_y + 10
                    if p['turns_left'] > 0:
                        rect = pygame.Rect(menu_x + 10, y_pos, 180, 40)
                        if rect.collidepoint(mx, my):
                            state.menu_active = False
                            state.menu_scroll = 0
                            continue
                        y_pos += 40
                    is_coastal = state.menu_city in state.coastal_cities
                    available_units = [ut for ut in unit_types if is_coastal or ut not in sea_units]
                    for i, ut in enumerate(available_units):
                        item_y = y_pos + i * 40 - state.menu_scroll
                        rect = pygame.Rect(menu_x + 10, item_y, 180, 40)
                        if rect.collidepoint(mx, my):
                            state.productions[state.menu_city]['unit'] = ut
                            state.productions[state.menu_city']['turns_left'] = costs[ut]
                            state.menu_active = False
                            state.menu_scroll = 0
                            good_sound.play()
                            break
                    state.menu_active = False
                    state.menu_scroll = 0
                else:
                    state.hold_hex = clicked_hex
                    state.hold_start = pygame.time.get_ticks()
            elif event.button == 3:
                state.drag_hold_start = pygame.time.get_ticks()
                state.last_mouse_pos = (mx, my)
                state.drag_start_pos = (mx, my)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if state.hold_start:
                    hold_time = pygame.time.get_ticks() - state.hold_start
                    if hold_time < 500:
                        if state.hold_hex:
                            if state.selected_unit and state.hold_hex in state.reachable:
                                path = find_path(state.selected_unit['pos'], state.hold_hex, state.selected_unit, state.grid, state.terrain, state.cities, state.city_owners, state.units, state.transport_loads, capacity, state.coastal_cities)
                                if path:
                                    dist = len(path)
                                    if dist <= state.selected_unit['movement_left']:
                                        if state.selected_unit['type'] in ['Fighter', 'TransportPlane'] and state.selected_unit['fuel'] is not None and dist > state.selected_unit['fuel']:
                                            error_sound.play()
                                            continue
                                        transport = next((u for u in state.units if u['pos'] == state.hold_hex and u['type'] in capacity and u['owner'] == state.selected_unit['owner']), None)
                                        if transport and state.selected_unit['type'] in capacity[transport['type']]['allowed'] and len(state.transport_loads.get(id(transport), [])) < capacity[transport['type']]['max']:
                                            state.transport_loads.setdefault(id(transport), []).append(state.selected_unit)
                                            state.units.remove(state.selected_unit)
                                            state.selected_unit['movement_left'] = 0
                                            good_sound.play()
                                            state.selected_unit = get_next_movable(state.units, state.transport_loads, None, state.current_player)
                                            state.last_selected_unit = state.selected_unit
                                            update_selected_unit(state, center=True)
                                            continue
                                        elif transport:
                                            error_sound.play()
                                            continue
                                        for step in path:
                                            state.selected_unit['pos'] = step
                                        state.selected_unit['movement_left'] -= dist
                                        state.selected_unit['did_move'] = True
                                        if state.selected_unit['type'] in ['Fighter', 'TransportPlane'] and state.selected_unit['fuel'] is not None:
                                            state.selected_unit['fuel'] -= dist
                                            if state.selected_unit['fuel'] <= 0:
                                                error_sound.play()
                                                remove_unit_and_loads(state.selected_unit, state.units, state.transport_loads)
                                                state.selected_unit = None
                                                state.last_selected_unit = None
                                                update_selected_unit(state)
                                                state.hold_start = None
                                                state.hold_hex = None
                                                state.path_preview = False
                                                state.preview_path = None
                                                state.target_hex = None
                                                continue
                                        if state.hold_hex in state.cities and state.city_owners[state.hold_hex] != state.selected_unit['owner']:
                                            stacked = [u for u in state.units if u['pos'] == state.hold_hex and u != state.selected_unit]
                                            for u in stacked:
                                                remove_unit_and_loads(u, state.units, state.transport_loads)
                                            state.city_owners[state.hold_hex] = state.selected_unit['owner']
                                            running = check_win(state.cities, state.city_owners, players, screen, bold_font, running)
                                        if state.selected_unit['movement_left'] <= 0:
                                            state.selected_unit = get_next_movable(state.units, state.transport_loads, state.selected_unit, state.current_player)
                                            state.last_selected_unit = state.selected_unit
                                            update_selected_unit(state, center=True)
                                        else:
                                            update_selected_unit(state)
                            elif state.selected_unit and state.hold_hex in state.attackable_hexes:
                                if state.hold_hex in state.cities:
                                    if state.city_owners[state.hold_hex] is None:
                                        if state.selected_unit['type'] == 'Infantry':
                                            stacked = [u for u in state.units if u['pos'] == state.hold_hex]
                                            for u in stacked:
                                                remove_unit_and_loads(u, state.units, state.transport_loads)
                                            state.city_owners[state.hold_hex] = state.current_player
                                            if state.selected_unit in state.units:
                                                remove_unit_and_loads(state.selected_unit, state.units, state.transport_loads)
                                            state.selected_unit = get_next_movable(state.units, state.transport_loads, None, state.current_player)
                                            state.last_selected_unit = state.selected_unit
                                            update_selected_unit(state, center=True)
                                            running = check_win(state.cities, state.city_owners, players, screen, bold_font, running)
                                            continue
                                        else:
                                            error_sound.play()
                                    else:
                                        virtual_defender = {'pos': state.hold_hex, 'hp': state.city_hp[state.hold_hex], 'max_hp': city_max_hp, 'attack': city_attack, 'defense': city_defense, 'range': city_range, 'owner': state.city_owners[state.hold_hex], 'type': 'City'}
                                        battle(state.selected_unit, virtual_defender, state.units, state.transport_loads, state.cities, state.city_owners, state.city_hp, min_city_hp, screen, state.zoom, state.cam_x, state.cam_y, SCREEN_WIDTH, SCREEN_HEIGHT, running, error_sound, state.grid, state.terrain, state.productions, state.fuel_range, state.reachable, state.attackable_hexes, state.selected_unit, state.path_preview, state.preview_path, state.target_hex, state.show_path, state.path_to_show, state.turn, state.current_player, state.menu_active, state.menu_city, unit_types, sea_units, state.coastal_cities, font, bold_font, players, state.attacked_cities, state.menu_scroll, hovered_hex)
                                        state.city_hp[state.hold_hex] = virtual_defender['hp']
                                        if virtual_defender['hp'] <= 0 and state.selected_unit in state.units and state.selected_unit['type'] == 'Infantry':
                                            stacked = [u for u in state.units if u['pos'] == state.hold_hex and u != state.selected_unit]
                                            for u in stacked:
                                                remove_unit_and_loads(u, state.units, state.transport_loads)
                                            state.city_owners[state.hold_hex] = state.selected_unit['owner']
                                            state.city_hp[state.hold_hex] = city_max_hp
                                            if state.selected_unit in state.units:
                                                remove_unit_and_loads(state.selected_unit, state.units, state.transport_loads)
                                        if state.selected_unit not in state.units or state.selected_unit['movement_left'] <= 0:
                                            state.selected_unit = get_next_movable(state.units, state.transport_loads, state.selected_unit, state.current_player)
                                            state.last_selected_unit = state.selected_unit
                                            update_selected_unit(state, center=True)
                                        else:
                                            update_selected_unit(state)
                                        continue
                                enemy = next((u for u in state.units if u['pos'] == state.hold_hex and u['owner'] != state.current_player and hex_distance(state.selected_unit['pos'], u['pos']) <= state.selected_unit['range'] and state.selected_unit['movement_left'] > 0), None)
                                if enemy:
                                    battle(state.selected_unit, enemy, state.units, state.transport_loads, state.cities, state.city_owners, state.city_hp, min_city_hp, screen, state.zoom, state.cam_x, state.cam_y, SCREEN_WIDTH, SCREEN_HEIGHT, running, error_sound, state.grid, state.terrain, state.productions, state.fuel_range, state.reachable, state.attackable_hexes, state.selected_unit, state.path_preview, state.preview_path, state.target_hex, state.show_path, state.path_to_show, state.turn, state.current_player, state.menu_active, state.menu_city, unit_types, sea_units, state.coastal_cities, font, bold_font, players, state.attacked_cities, state.menu_scroll, hovered_hex)
                                    if state.selected_unit['movement_left'] <= 0 or state.selected_unit not in state.units:
                                        state.selected_unit = get_next_movable(state.units, state.transport_loads, state.selected_unit, state.current_player)
                                        state.last_selected_unit = state.selected_unit
                                        update_selected_unit(state, center=True)
                                    else:
                                        update_selected_unit(state)
                                        continue
                    else:
                        if state.path_preview and state.preview_path:
                            if state.target_hex == state.selected_unit['pos']:
                                pass
                            else:
                                path_len = len(state.preview_path)
                                if state.selected_unit['type'] in ['Fighter', 'TransportPlane'] and state.selected_unit['fuel'] is not None and path_len > state.selected_unit['fuel']:
                                    error_sound.play()
                                else:
                                    state.selected_unit['path'] = state.preview_path
                                    state.cam_x, state.cam_y = center_on_unit_if_needed(state.selected_unit, state.cam_x, state.cam_y, state.zoom, SCREEN_WIDTH, SCREEN_HEIGHT, state.grid)
                                    state.cam_x, state.cam_y, running = move_unit_along_path(state.selected_unit, state.units, state.transport_loads, state.terrain, state.cities, state.city_owners, state.grid, capacity, max_stack, players, screen, bold_font, state.attacked_cities, state.coastal_cities, state.zoom, SCREEN_WIDTH, SCREEN_HEIGHT, font, state.turn, state.menu_active, state.menu_city, unit_types, sea_units, state.productions, state.city_hp, state.fuel_range, state.reachable, state.attackable_hexes, state.selected_unit, state.path_preview, state.preview_path, state.target_hex, state.show_path, state.path_to_show, state.cam_x, state.cam_y, state.current_player, state.menu_scroll, hovered_hex, good_sound)
                                    if state.selected_unit and 'path' in state.selected_unit and state.selected_unit['path']:
                                        state.show_path = True
                                        state.path_to_show = state.selected_unit['path'][:]
                                        if state.selected_unit['path']:
                                            state.highlighted_hex = state.selected_unit['path'][-1]
                                    if state.selected_unit and state.selected_unit['movement_left'] <= 0:
                                        state.selected_unit = get_next_movable(state.units, state.transport_loads, state.selected_unit, state.current_player)
                                        state.last_selected_unit = state.selected_unit
                                        update_selected_unit(state, center=True)
                                    elif state.selected_unit:
                                        update_selected_unit(state)
                    # Cleanup after short or long hold
                    state.hold_start = None
                    state.hold_hex = None
                    state.path_preview = False
                    state.preview_path = None
                    state.target_hex = None
            elif event.button == 3:
                if state.drag_hold_start:
                    mx, my = pygame.mouse.get_pos()
                    clicked_hex = pixel_to_axial(mx, my, state.zoom, state.cam_x, state.cam_y, SCREEN_WIDTH, SCREEN_HEIGHT, state.grid)
                    # Only process RMB actions if not dragging
                    if not state.dragging and clicked_hex:
                        state.highlighted_hex = clicked_hex
                        state.last_info_hex = clicked_hex
                        unit_at = next((u for u in state.units if u['pos'] == clicked_hex and u['owner'] == state.current_player and (u['movement_left'] > 0 or u.get('sentry', False))), None)
                        if unit_at:
                            if unit_at.get('sentry', False):
                                unit_at['sentry'] = False
                                unit_at['movement_left'] = movements[unit_at['type']]
                                good_sound.play()
                            state.selected_unit = unit_at
                            state.last_selected_unit = unit_at
                            update_selected_unit(state)
                            state.path_preview = False
                            state.preview_path = None
                            state.target_hex = None
                        if clicked_hex in state.cities and state.city_owners[clicked_hex] == state.current_player:
                            state.menu_active = True
                            state.menu_city = clicked_hex
                            state.menu_scroll = 0
                        # Removed attack logic from right-click (moved to left-click)
                    state.dragging = False
                    state.drag_hold_start = None
                    state.last_mouse_pos = None
                    state.drag_start_pos = None
        elif event.type == pygame.MOUSEMOTION:
            if pygame.mouse.get_pressed()[0]:
                if state.path_preview:
                    mx, my = event.pos
                    current_hex = pixel_to_axial(mx, my, state.zoom, state.cam_x, state.cam_y, SCREEN_WIDTH, SCREEN_HEIGHT, state.grid)
                    if current_hex and current_hex != state.target_hex and (not is_hex_occupied(current_hex, state.selected_unit['owner'] if state.selected_unit else None, state.units, state.cities, state.city_owners, max_stack) or is_loadable_transport_hex(current_hex, state.selected_unit, state.units, state.transport_loads, state.terrain, state.cities, state.city_owners, state.grid)):
                        state.target_hex = current_hex
                        path = find_path(state.selected_unit['pos'], state.target_hex, state.selected_unit, state.grid, state.terrain, state.cities, state.city_owners, state.units, state.transport_loads, capacity, state.coastal_cities)
                        if path:
                            state.preview_path = path
                        else:
                            state.preview_path = None
            elif pygame.mouse.get_pressed()[2] and state.drag_start_pos:
                mx, my = event.pos
                # Check if mouse has moved enough to start dragging (threshold: 5 pixels)
                dx_start = mx - state.drag_start_pos[0]
                dy_start = my - state.drag_start_pos[1]
                if math.hypot(dx_start, dy_start) > 5:
                    state.dragging = True
                if state.dragging and state.last_mouse_pos:
                    dx = mx - state.last_mouse_pos[0]
                    dy = my - state.last_mouse_pos[1]
                    state.cam_x += dx
                    state.cam_y += dy
                state.last_mouse_pos = (mx, my)

pygame.quit()
