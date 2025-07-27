import math
import random
import time
import pygame
from hex_utils import hex_distance, get_neighbors, pixel_to_axial, axial_to_pixel
from units import get_allowed, is_loadable_transport_hex, get_reachable, get_fuel_range, find_path, is_hex_occupied
from settings import HEX_SIZE, movements, max_fuel, capacity, unit_stats, costs, city_max_hp, min_city_hp, WHITE, RED, GREY, YELLOW, ORANGE, LIGHT_RED, DARK_RED, BLUE, GREEN, BROWN, player_colors, production_text_colors, unit_digits, digit_colors, light_colors, sea_units, city_attack, city_defense, city_range, terrain_bonuses
from rendering import draw_screen, draw_hex_border  # Added draw_hex_border import

def has_enemy_or_neutral_city_near(pos, owner, cities, city_owners, units, grid):
    """Check if an enemy or neutral city/unit is adjacent to the position."""
    for n in get_neighbors(*pos, grid):
        if n in cities and city_owners[n] != owner:
            return True
        for u in units:
            if u['pos'] == n and u['owner'] != owner:
                return True
    return False

def get_next_movable(units, transport_loads, current=None, player=None):
    """Get the next unit with movement left for the player, skipping sentry units."""
    if player is None:
        return None
    movable_units = [u for u in units if u['movement_left'] > 0 and u['owner'] == player and not u.get('sentry', False) and u not in [lu for t in transport_loads.values() for lu in t]]
    if not movable_units:
        return None
    if current is None:
        return movable_units[0]
    try:
        idx = movable_units.index(current)
        return movable_units[(idx + 1) % len(movable_units)]
    except ValueError:
        return movable_units[0]

def center_on_unit(unit, cam_x, cam_y, zoom, screen_width, screen_height):
    """Center the camera on the unit's position."""
    if unit:
        base_x = HEX_SIZE * (3 / 2 * unit['pos'][0]) * zoom
        base_y = HEX_SIZE * (math.sqrt(3) * (unit['pos'][1] + unit['pos'][0] / 2)) * zoom
        cam_x = -base_x + screen_width / 2
        cam_y = -base_y + screen_height / 2
    return cam_x, cam_y

def center_on_unit_if_needed(unit, cam_x, cam_y, zoom, screen_width, screen_height, grid):
    """Recenter camera only if unit is outside a 15x15 hex grid around screen center."""
    if not unit:
        return cam_x, cam_y
    center_hex = pixel_to_axial(screen_width / 2, screen_height / 2, zoom, cam_x, cam_y, screen_width, screen_height, grid)
    if not center_hex:
        return center_on_unit(unit, cam_x, cam_y, zoom, screen_width, screen_height)
    if hex_distance(unit['pos'], center_hex) <= 7:
        return cam_x, cam_y
    return center_on_unit(unit, cam_x, cam_y, zoom, screen_width, screen_height)

def move_unit_along_path(unit, units, transport_loads, terrain, cities, city_owners, grid, capacity, max_stack, players, screen, bold_font, attacked_cities, coastal_cities, zoom, screen_width, screen_height, font, turn, menu_active, menu_city, unit_types, sea_units, productions, city_hp, fuel_range, reachable, attackable_hexes, selected_unit, path_preview, preview_path, target_hex, show_path, path_to_show, cam_x, cam_y, current_player, menu_scroll, hovered_hex=None, good_sound=None):
    """Move a unit along its path, handling fuel, stacking, and city capture."""
    running = True
    if 'path' not in unit or not unit['path']:
        return cam_x, cam_y, running
    if has_enemy_or_neutral_city_near(unit['pos'], unit['owner'], cities, city_owners, units, grid):
        del unit['path']
        return cam_x, cam_y, running
    moved = 0
    allowed = get_allowed(unit['type'])
    is_sea_unit = unit['type'] in sea_units
    while moved < unit['movement_left'] and unit['path']:
        next_hex = unit['path'][0]
        allow_city = is_sea_unit and next_hex in coastal_cities and city_owners.get(next_hex) == unit['owner']
        loadable = is_loadable_transport_hex(next_hex, unit, units, transport_loads, terrain, cities, city_owners, grid)
        occupied = is_hex_occupied(next_hex, unit['owner'], units, cities, city_owners, max_stack)
        if (occupied and not loadable) or (terrain[next_hex] not in allowed and not loadable and not allow_city) or (next_hex in cities and city_owners[next_hex] is None):
            del unit['path']
            break
        unit['pos'] = next_hex
        unit['path'].pop(0)
        moved += 1
        if moved > 0:
            unit['did_move'] = True
        if unit['type'] in ['Fighter', 'TransportPlane'] and unit['fuel'] is not None:
            unit['fuel'] = unit['fuel'] - 1
            if unit['fuel'] <= 0:
                error_sound = pygame.mixer.Sound('error.wav')  # Ensure sound is available
                error_sound.play()
                if id(unit) in transport_loads:
                    for lu in transport_loads[id(unit)]:
                        units.remove(lu)
                    del transport_loads[id(unit)]
                units.remove(unit)
                break
        if id(unit) in transport_loads:
            for loaded_unit in transport_loads[id(unit)]:
                loaded_unit['pos'] = unit['pos']
        if unit['pos'] in cities and city_owners[unit['pos']] != unit['owner']:
            stacked = [u for u in units if u['pos'] == unit['pos'] and u != unit]
            for u in stacked:
                remove_unit_and_loads(u, units, transport_loads)
            city_owners[unit['pos']] = unit['owner']
            running = check_win(cities, city_owners, players, screen, bold_font, running)
        if unit['type'] == 'AirCarrier':
            for loaded_unit in transport_loads.get(id(unit), []):
                if loaded_unit['type'] == 'Fighter':
                    loaded_unit['fuel'] = max_fuel.get('Fighter', loaded_unit['fuel'])
        cam_x, cam_y = center_on_unit_if_needed(unit, cam_x, cam_y, zoom, screen_width, screen_height, grid)
        draw_screen(screen, grid, terrain, cities, city_owners, productions, city_hp, fuel_range, reachable, attackable_hexes, units, transport_loads, selected_unit, zoom, cam_x, cam_y, screen_width, screen_height, path_preview, preview_path, target_hex, show_path, path_to_show, turn, current_player, menu_active, menu_city, unit_types, sea_units, coastal_cities, font, bold_font, menu_scroll, hovered_hex)
        pygame.display.flip()
        time.sleep(0.1)
    unit['movement_left'] -= moved
    if 'path' in unit and not unit['path']:
        del unit['path']
    # Check if final position is loadable transport and load if possible
    if is_loadable_transport_hex(unit['pos'], unit, units, transport_loads, terrain, cities, city_owners, grid):
        transport = next((u for u in units if u['pos'] == unit['pos'] and u['type'] in capacity and unit['type'] in capacity[u['type']]['allowed'] and u['owner'] == unit['owner'] and len(transport_loads.get(id(u), [])) < capacity[u['type']]['max']), None)
        if transport:
            transport_loads.setdefault(id(transport), []).append(unit)
            units.remove(unit)
            unit['movement_left'] = 0
            if good_sound:
                good_sound.play()
    return cam_x, cam_y, running

def remove_unit_and_loads(unit, units, transport_loads):
    """Remove a unit and its loaded units from the game."""
    if unit in units:
        units.remove(unit)
    if id(unit) in transport_loads:
        for lu in transport_loads[id(unit)]:
            units.remove(lu)
        del transport_loads[id(unit)]

def battle(attacker, defender, units, transport_loads, cities, city_owners, city_hp, min_city_hp, screen, zoom, cam_x, cam_y, screen_width, screen_height, running, error_sound, grid, terrain, productions, fuel_range, reachable, attackable_hexes, selected_unit, path_preview, preview_path, target_hex, show_path, path_to_show, turn, current_player, menu_active, menu_city, unit_types, sea_units, coastal_cities, font, bold_font, players, attacked_cities, menu_scroll, hovered_hex=None):
    """Handle combat between an attacker and defender, including city battles."""
    range_attack = hex_distance(attacker['pos'], defender['pos'])
    ax, ay = axial_to_pixel(*attacker['pos'], zoom, cam_x, cam_y, screen_width, screen_height)
    dx, dy = axial_to_pixel(*defender['pos'], zoom, cam_x, cam_y, screen_width, screen_height)
    is_city = 'type' in defender and defender['type'] == 'City'
    if is_city:
        attacked_cities.add(defender['pos'])
    is_infantry = attacker['type'] == 'Infantry'
    if is_city and not is_infantry and defender['hp'] <= min_city_hp:
        error_sound.play()
        return
    # Get terrain bonus for defender
    def_terrain = terrain[defender['pos']]
    def_bonus = terrain_bonuses.get(def_terrain, {'defense': 1.0})['defense']
    while attacker['hp'] > 0 and (defender['hp'] > 0 or (is_city and not is_infantry and defender['hp'] > min_city_hp)):
        att_mod = random.uniform(0.8, 1.2)
        def_mod = random.uniform(0.8, 1.2)
        damage = max(0, int(attacker['attack'] * att_mod * 1.5 - defender['defense'] * def_mod * def_bonus * 0.5))
        if damage == 0 and random.random() < 0.2:
            damage = 2
        if is_city and not is_infantry:
            defender['hp'] = max(min_city_hp, defender['hp'] - damage)
        else:
            defender['hp'] -= damage
        if is_city and not is_infantry and defender['hp'] <= min_city_hp:
            break
        draw_screen(screen, grid, terrain, cities, city_owners, productions, city_hp, fuel_range, reachable, attackable_hexes, units, transport_loads, selected_unit, zoom, cam_x, cam_y, screen_width, screen_height, path_preview, preview_path, target_hex, show_path, path_to_show, turn, current_player, menu_active, menu_city, unit_types, sea_units, coastal_cities, font, bold_font, menu_scroll, hovered_hex)
        draw_hex_border(screen, dx, dy, RED, 5, zoom)
        pygame.draw.line(screen, RED, (ax, ay), (dx, dy), 5)
        pygame.display.flip()
        time.sleep(0.25)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
        draw_screen(screen, grid, terrain, cities, city_owners, productions, city_hp, fuel_range, reachable, attackable_hexes, units, transport_loads, selected_unit, zoom, cam_x, cam_y, screen_width, screen_height, path_preview, preview_path, target_hex, show_path, path_to_show, turn, current_player, menu_active, menu_city, unit_types, sea_units, coastal_cities, font, bold_font, menu_scroll, hovered_hex)
        pygame.display.flip()
        if defender['hp'] <= 0 or (is_city and not is_infantry and defender['hp'] <= min_city_hp):
            break
        att_mod = random.uniform(0.8, 1.2)
        def_mod = random.uniform(0.8, 1.2)
        # Attacker doesn't get terrain bonus for counterattack, assuming it's the defender's turn to counter
        damage = max(0, int(defender['attack'] * att_mod * 1.5 - attacker['defense'] * def_mod * 0.5))
        if damage == 0 and random.random() < 0.2:
            damage = 2
        attacker['hp'] -= damage
        draw_screen(screen, grid, terrain, cities, city_owners, productions, city_hp, fuel_range, reachable, attackable_hexes, units, transport_loads, selected_unit, zoom, cam_x, cam_y, screen_width, screen_height, path_preview, preview_path, target_hex, show_path, path_to_show, turn, current_player, menu_active, menu_city, unit_types, sea_units, coastal_cities, font, bold_font, menu_scroll, hovered_hex)
        draw_hex_border(screen, ax, ay, RED, 5, zoom)
        pygame.draw.line(screen, RED, (dx, dy), (ax, ay), 5)
        pygame.display.flip()
        time.sleep(0.25)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
        draw_screen(screen, grid, terrain, cities, city_owners, productions, city_hp, fuel_range, reachable, attackable_hexes, units, transport_loads, selected_unit, zoom, cam_x, cam_y, screen_width, screen_height, path_preview, preview_path, target_hex, show_path, path_to_show, turn, current_player, menu_active, menu_city, unit_types, sea_units, coastal_cities, font, bold_font, menu_scroll, hovered_hex)
        pygame.display.flip()
    if attacker['hp'] <= 0 and defender['hp'] <= 0:
        attacker['hp'] = 1
        if not is_city:
            remove_unit_and_loads(defender, units, transport_loads)
    elif attacker['hp'] <= 0:
        remove_unit_and_loads(attacker, units, transport_loads)
    elif defender['hp'] <= 0:
        if not is_city:
            remove_unit_and_loads(defender, units, transport_loads)
    if attacker['hp'] > 0 and defender['hp'] <= 0 and range_attack == 1 and terrain[defender['pos']] in get_allowed(attacker['type']) and not is_city:
        if defender['pos'] not in cities or attacker['type'] == 'Infantry':
            attacker['pos'] = defender['pos']
            if attacker['pos'] in cities and city_owners[attacker['pos']] != attacker['owner']:
                stacked = [u for u in units if u['pos'] == attacker['pos'] and u != attacker]
                for u in stacked:
                    remove_unit_and_loads(u, units, transport_loads)
                city_owners[attacker['pos']] = attacker['owner']
                city_hp[attacker['pos']] = city_max_hp
                remove_unit_and_loads(attacker, units, transport_loads)
    attacker['movement_left'] = max(0, attacker['movement_left'] - 1)
    check_win(cities, city_owners, players, screen, bold_font, running)
    if is_city:
        city_hp[defender['pos']] = defender['hp']
        if defender['hp'] <= 0 and attacker in units and attacker['type'] == 'Infantry':
            stacked = [u for u in units if u['pos'] == defender['pos'] and u != attacker]
            for u in stacked:
                remove_unit_and_loads(u, units, transport_loads)
            city_owners[defender['pos']] = attacker['owner']
            city_hp[defender['pos']] = city_max_hp
            if attacker in units:
                remove_unit_and_loads(attacker, units, transport_loads)

def check_win(cities, city_owners, players, screen, bold_font, running):
    """Check if a player has won by owning all cities."""
    for player in players:
        owned_cities = [c for c in cities if city_owners[c] == player]
        if len(owned_cities) == len(cities):
            win_text = bold_font.render(f"Player {player} wins!", True, WHITE)
            screen.blit(win_text, (SCREEN_WIDTH // 2 - win_text.get_width() // 2, SCREEN_HEIGHT // 2 - win_text.get_height() // 2))
            pygame.display.flip()
            time.sleep(3)
            running = False
            return running
    return running
