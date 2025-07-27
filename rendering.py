import math
import pygame
from collections import Counter
from settings import HEX_SIZE, BLUE, GREEN, BROWN, GREY, BLACK, player_colors, production_text_colors, YELLOW, RED, ORANGE, LIGHT_RED, DARK_RED, WHITE, light_colors, unit_digits, digit_colors, city_max_hp, costs, movements, max_fuel
from hex_utils import axial_to_pixel

def draw_hex(screen, center_x, center_y, color, zoom):
    effective_size = HEX_SIZE * zoom
    points = []
    for i in range(6):
        angle = math.radians(60 * i)
        px = center_x + effective_size * math.cos(angle)
        py = center_y + effective_size * math.sin(angle)
        points.append((px, py))
    pygame.draw.polygon(screen, color, points)
    pygame.draw.polygon(screen, BLACK, points, 1)

def draw_hex_border(screen, center_x, center_y, color, width, zoom):
    effective_size = HEX_SIZE * zoom
    points = []
    for i in range(6):
        angle = math.radians(60 * i)
        px = center_x + effective_size * math.cos(angle)
        py = center_y + effective_size * math.sin(angle)
        points.append((px, py))
    pygame.draw.polygon(screen, color, points, width)

def draw_dashed_line(screen, color, start, end, width=7, dash=10, gap=5, offset=0):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dist = math.hypot(dx, dy)
    if dist == 0:
        return
    ux = dx / dist
    uy = dy / dist
    pos = offset % (dash + gap)
    while pos < dist:
        p1x = start[0] + ux * pos
        p1y = start[1] + uy * pos
        p2x = start[0] + ux * min(pos + dash, dist)
        p2y = start[1] + uy * min(pos + dash, dist)
        pygame.draw.line(screen, color, (p1x, p1y), (p2x, p2y), width)
        pos += dash + gap

def is_within_screen_bounds(x, y, zoom, screen_width, screen_height):
    """Check if coordinates are within screen bounds with zoom-adjusted buffer."""
    return -HEX_SIZE * zoom < x < screen_width + HEX_SIZE * zoom and -HEX_SIZE * zoom < y < screen_height + HEX_SIZE * zoom

def draw_screen(screen, grid, terrain, cities, city_owners, productions, city_hp, fuel_range, reachable, attackable_hexes, units, transport_loads, selected_unit, zoom, cam_x, cam_y, screen_width, screen_height, path_preview, preview_path, target_hex, show_path, path_to_show, turn, current_player, menu_active, menu_city, unit_types, sea_units, coastal_cities, font, bold_font, menu_scroll, hovered_hex=None, last_info_hex=None, last_selected_unit=None, highlighted_hex=None):
    screen.fill(BLACK)
    
    # Draw grid
    for q, r in grid:
        x, y = axial_to_pixel(q, r, zoom, cam_x, cam_y, screen_width, screen_height)
        if is_within_screen_bounds(x, y, zoom, screen_width, screen_height):
            t = terrain[(q, r)]
            color = BLUE if t == 'water' else GREEN if t == 'land' else BROWN
            if (q, r) in cities:
                owner = city_owners[(q, r)]
                color = player_colors[owner] if owner else GREY
            draw_hex(screen, x, y, color, zoom)
            if (q, r) in cities and city_owners[(q, r)] == current_player:
                p = productions[(q, r)]
                text_color = production_text_colors[current_player]
                if p['turns_left'] > 0:
                    digit = unit_digits[p['unit']]
                    text = bold_font.render(digit, True, text_color)
                else:
                    text = bold_font.render('#', True, text_color)
                screen.blit(text, (x - text.get_width() // 2, y - text.get_height() // 2))
            # Draw city HP bar if below 100%
            if (q, r) in cities and city_hp[(q, r)] < city_max_hp:
                percentage = (city_hp[(q, r)] / city_max_hp) * 100
                if percentage == 100:
                    hp_color = GREEN
                elif 75 <= percentage < 100:
                    hp_color = YELLOW
                elif 50 <= percentage < 75:
                    hp_color = ORANGE
                elif 25 <= percentage < 50:
                    hp_color = LIGHT_RED
                else:
                    hp_color = DARK_RED
                bar_width = int(HEX_SIZE * zoom // 2)
                bar_height = 4
                fill_width = int(bar_width * (city_hp[(q, r)] / city_max_hp))
                hp_bar_bg = pygame.Rect(x - bar_width // 2, y + int(HEX_SIZE * zoom // 3), bar_width, bar_height)
                hp_bar_fill = pygame.Rect(x - bar_width // 2, y + int(HEX_SIZE * zoom // 3), fill_width, bar_height)
                pygame.draw.rect(screen, GREY, hp_bar_bg)
                pygame.draw.rect(screen, hp_color, hp_bar_fill)
    
    # Draw fuel range border
    for hex_pos in fuel_range:
        hx, hy = axial_to_pixel(*hex_pos, zoom, cam_x, cam_y, screen_width, screen_height)
        if is_within_screen_bounds(hx, hy, zoom, screen_width, screen_height):
            draw_hex_border(screen, hx, hy, RED, 3, zoom)
    
    # Draw highlights
    for hex_pos in reachable:
        hx, hy = axial_to_pixel(*hex_pos, zoom, cam_x, cam_y, screen_width, screen_height)
        if is_within_screen_bounds(hx, hy, zoom, screen_width, screen_height):
            draw_hex_border(screen, hx, hy, YELLOW, 3, zoom)
    
    # Draw attackable borders
    for h in attackable_hexes:
        hx, hy = axial_to_pixel(*h, zoom, cam_x, cam_y, screen_width, screen_height)
        if is_within_screen_bounds(hx, hy, zoom, screen_width, screen_height):
            draw_hex_border(screen, hx, hy, RED, 3, zoom)
    
    # Draw units
    units_to_draw = [u for u in units if u is not selected_unit] + [selected_unit] if selected_unit else units
    for unit in units_to_draw:
        if unit is None:
            continue
        ux, uy = axial_to_pixel(*unit['pos'], zoom, cam_x, cam_y, screen_width, screen_height)
        if is_within_screen_bounds(ux, uy, zoom, screen_width, screen_height):
            owner = unit['owner']
            if selected_unit is unit:
                ticks = pygame.time.get_ticks()
                ball_color = player_colors[owner] if (ticks // 500) % 2 == 0 else light_colors[owner]
            else:
                ball_color = player_colors[owner]
            pygame.draw.circle(screen, ball_color, (ux, uy), int(HEX_SIZE * zoom // 2))
            digit = unit_digits[unit['type']]
            text = font.render(digit, True, digit_colors[owner])
            screen.blit(text, (ux - text.get_width() // 2, uy - text.get_height() // 2))
            # Draw HP bar
            if unit['hp'] > 0:
                percentage = (unit['hp'] / unit['max_hp']) * 100
                if percentage == 100:
                    hp_color = GREEN
                elif 75 <= percentage < 100:
                    hp_color = YELLOW
                elif 50 <= percentage < 75:
                    hp_color = ORANGE
                elif 25 <= percentage < 50:
                    hp_color = LIGHT_RED
                else:
                    hp_color = DARK_RED
                bar_width = int(HEX_SIZE * zoom // 2)
                bar_height = 4
                fill_width = int(bar_width * (unit['hp'] / unit['max_hp']))
                hp_bar_bg = pygame.Rect(ux - bar_width // 2, uy + int(HEX_SIZE * zoom // 3), bar_width, bar_height)
                hp_bar_fill = pygame.Rect(ux - bar_width // 2, uy + int(HEX_SIZE * zoom // 3), fill_width, bar_height)
                pygame.draw.rect(screen, GREY, hp_bar_bg)
                pygame.draw.rect(screen, hp_color, hp_bar_fill)
            # Draw sentry indicator
            if unit.get('sentry', False):
                pygame.draw.circle(screen, WHITE, (ux + int(HEX_SIZE * zoom // 3), uy - int(HEX_SIZE * zoom // 3)), 5)
    
    # Draw current path if selected
    if selected_unit and 'path' in selected_unit and selected_unit['path']:
        path = selected_unit['path']
        points = [axial_to_pixel(*selected_unit['pos'], zoom, cam_x, cam_y, screen_width, screen_height)]
        for h in path:
            points.append(axial_to_pixel(*h, zoom, cam_x, cam_y, screen_width, screen_height))
        offset = (pygame.time.get_ticks() / 1000.0 * 10) % (10 + 5)
        for i in range(len(points) - 1):
            draw_dashed_line(screen, WHITE, points[i], points[i+1], 7, 10, 5, offset)
    
    # Draw preview path
    if path_preview and preview_path:
        points = [axial_to_pixel(*selected_unit['pos'], zoom, cam_x, cam_y, screen_width, screen_height)]
        for h in preview_path:
            points.append(axial_to_pixel(*h, zoom, cam_x, cam_y, screen_width, screen_height))
        offset = (pygame.time.get_ticks() / 1000.0 * 10) % (10 + 5)
        for i in range(len(points) - 1):
            draw_dashed_line(screen, WHITE, points[i], points[i+1], 7, 10, 5, offset)
        if target_hex:
            hx, hy = axial_to_pixel(*target_hex, zoom, cam_x, cam_y, screen_width, screen_height)
            draw_hex_border(screen, hx, hy, WHITE, 5, zoom)
            # Calculate turns
            path_len = len(preview_path)
            mov = movements[selected_unit['type']]
            if selected_unit['type'] in ['Fighter', 'TransportPlane'] and selected_unit['fuel'] is not None and path_len > selected_unit['fuel']:
                turns_text = 'X'
            else:
                turns = math.ceil(path_len / mov)
                turns_text = str(turns)
            text = bold_font.render(turns_text, True, BLACK)
            screen.blit(text, (hx - text.get_width() // 2, hy - text.get_height() // 2))
    
    # Draw shown path
    if show_path and path_to_show:
        points = [axial_to_pixel(*selected_unit['pos'], zoom, cam_x, cam_y, screen_width, screen_height)]
        for h in path_to_show:
            points.append(axial_to_pixel(*h, zoom, cam_x, cam_y, screen_width, screen_height))
        offset = (pygame.time.get_ticks() / 1000.0 * 10) % (10 + 5)
        for i in range(len(points) - 1):
            draw_dashed_line(screen, WHITE, points[i], points[i+1], 7, 10, 5, offset)
        if path_to_show:
            dest = path_to_show[-1]
            hx, hy = axial_to_pixel(*dest, zoom, cam_x, cam_y, screen_width, screen_height)
            draw_hex_border(screen, hx, hy, WHITE, 5, zoom)
            # Calculate turns for remaining path
            path_len = len(path_to_show)
            mov = movements[selected_unit['type']]
            if selected_unit['type'] in ['Fighter', 'TransportPlane'] and selected_unit['fuel'] is not None and path_len > selected_unit['fuel']:
                turns_text = 'X'
            else:
                turns = math.ceil(path_len / mov)
                turns_text = str(turns)
            text = bold_font.render(turns_text, True, BLACK)
            screen.blit(text, (hx - text.get_width() // 2, hy - text.get_height() // 2))
    
    # Draw highlighted hex border
    if highlighted_hex:
        hx, hy = axial_to_pixel(*highlighted_hex, zoom, cam_x, cam_y, screen_width, screen_height)
        if is_within_screen_bounds(hx, hy, zoom, screen_width, screen_height):
            draw_hex_border(screen, hx, hy, WHITE, 2, zoom)
    
    # Draw UI
    turn_text = font.render(f"Turn: {turn} - Player: {current_player}", True, WHITE)
    screen.blit(turn_text, (10, 10))
    
    if menu_active:
        cx, cy = axial_to_pixel(*menu_city, zoom, cam_x, cam_y, screen_width, screen_height)
        menu_x = min(max(cx + HEX_SIZE * zoom, 50), screen_width - 250)
        menu_y = min(max(cy - 150, 50), screen_height - 300)
        menu_width = 200
        menu_height = 300
        # Draw border and background
        pygame.draw.rect(screen, GREY, (menu_x - 10, menu_y - 10, menu_width + 20, menu_height + 20), border_radius=10)
        pygame.draw.rect(screen, WHITE, (menu_x, menu_y, menu_width, menu_height), border_radius=10)
        p = productions[menu_city]
        y_pos = menu_y + 10
        menu_font = pygame.font.SysFont('Arial', 18, bold=True)
        if p['turns_left'] > 0:
            status = f"{p['unit']} ({p['turns_left']} turns)"
            text = menu_font.render(status, True, BLACK)
            screen.blit(text, (menu_x + 10, y_pos))
            y_pos += 40
        is_coastal = menu_city in coastal_cities
        available_units = [ut for ut in unit_types if is_coastal or ut not in sea_units]
        item_height = 40
        visible_items = (menu_height - (y_pos - menu_y)) // item_height
        max_scroll = max(0, len(available_units) * item_height - visible_items * item_height)
        menu_scroll = max(0, min(menu_scroll, max_scroll))
        # Draw scrollbar
        if len(available_units) > visible_items:
            scrollbar_height = menu_height * (visible_items / len(available_units))
            scrollbar_y = menu_y + (menu_scroll / max_scroll) * (menu_height - scrollbar_height) if max_scroll > 0 else menu_y
            pygame.draw.rect(screen, BLACK, (menu_x + menu_width - 10, menu_y, 10, menu_height))
            pygame.draw.rect(screen, LIGHT_RED, (menu_x + menu_width - 10, scrollbar_y, 10, scrollbar_height))
        # Draw unit list
        for i, ut in enumerate(available_units):
            item_y = y_pos + i * item_height - menu_scroll
            if item_y + item_height < menu_y or item_y > menu_y + menu_height:
                continue
            text = menu_font.render(f"{ut} ({costs[ut]} turns)", True, BLACK)
            screen.blit(text, (menu_x + 10, item_y))

    # Draw information line
    info_font = pygame.font.SysFont(None, 22)  # Reverted to original font size
    if last_info_hex or (selected_unit and last_info_hex is None):
        info_text = ""
        display_hex = last_info_hex
        if display_hex is None and selected_unit:
            display_hex = selected_unit['pos']
        if display_hex:
            unit = next((u for u in units if u['pos'] == display_hex), None)
            if unit:
                if unit['owner'] == current_player:
                    type_ = unit['type']
                    health = f"{unit['hp']}/{unit['max_hp']}"
                    movement = f"{unit['movement_left']}/{movements[type_]}"
                    fuel = f", Fuel: {unit['fuel']}/{max_fuel.get(type_, 'N/A')}" if unit.get('fuel') is not None else ""
                    info_text = f"{type_}: Health: {health}, Movement: {movement}{fuel}"
                    # Add loaded units if transport
                    if id(unit) in transport_loads and transport_loads[id(unit)]:
                        loaded = Counter(lu['type'] for lu in transport_loads[id(unit)])
                        loaded_str = ", Loaded: " + ", ".join(f"{count} {typ}" for typ, count in loaded.items())
                        info_text += loaded_str
                else:
                    info_text = f"Enemy {unit['type']}"
            elif display_hex in cities:
                if city_owners[display_hex] == current_player:
                    p = productions[display_hex]
                    info_text = f"City: Production: {p['unit'] or 'None'} ({p['turns_left']} turns)"
                else:
                    info_text = "City"
            else:
                info_text = terrain.get(display_hex, "Unknown")
        
        # Truncate text if too long for 600 pixels
        text_surface = info_font.render(info_text, True, WHITE)
        if text_surface.get_width() > 590:
            info_text = info_text[:75] + "..."  # Truncate to approx 75 chars, adjust as needed
            text_surface = info_font.render(info_text, True, WHITE)
        
        # Draw info line (600x30 to accommodate single line)
        box_rect = pygame.Rect(screen_width - 610, screen_height - 40, 600, 30)
        pygame.draw.rect(screen, GREY, box_rect)
        screen.blit(text_surface, (screen_width - 600, screen_height - 30))  # Adjusted y-position for original font

    return last_info_hex
