from collections import deque
from heapq import heappush, heappop
from settings import movements, max_fuel, capacity, unit_stats, sea_units, max_stack
from hex_utils import hex_distance, get_neighbors

def get_allowed(utype: str) -> set:
    """Return allowed terrain types for a unit type."""
    if utype in ['Infantry', 'Tank']:
        return {'land'}
    elif utype in sea_units:
        return {'water'}
    elif utype in ['Fighter', 'TransportPlane']:
        return {'water', 'land', 'mountain'}
    return set()

def is_loadable_transport_hex(key: tuple, unit: dict, units: list, transport_loads: dict, terrain: dict, cities: list, city_owners: dict, grid: list) -> bool:
    """Check if a hex contains a loadable transport for the unit."""
    utype = unit['type']
    owner = unit['owner']
    # Allow loading onto TransportShip if adjacent to land or owned city
    if utype in ['Infantry', 'Tank']:
        for n in get_neighbors(*key, grid):
            if terrain.get(n) == 'land' or (n in cities and city_owners.get(n) == owner):
                transport = any(u['pos'] == key and u['type'] == 'TransportShip' and utype in capacity[u['type']]['allowed'] and u['owner'] == owner and len(transport_loads.get(id(u), [])) < capacity[u['type']]['max'] for u in units)
                # print(f"Checking loadable hex {key} for {utype}: transport={transport}, adjacent_land={any(terrain.get(n) == 'land' for n in get_neighbors(*key, grid))}, adjacent_owned_city={any(n in cities and city_owners.get(n) == owner for n in get_neighbors(*key, grid))}")
                return transport
    return any(u['pos'] == key and u['type'] in capacity and utype in capacity[u['type']]['allowed'] and u['owner'] == owner and len(transport_loads.get(id(u), [])) < capacity[u['type']]['max'] for u in units)

def get_unit_count_at(pos: tuple, units: list) -> int:
    """Count units at a given position."""
    return sum(1 for u in units if u['pos'] == pos)

def is_hex_occupied(pos: tuple, owner: str, units: list, cities: list, city_owners: dict, max_stack: int) -> bool:
    """Check if a hex is occupied, respecting stacking limits for owned cities."""
    if pos in cities and city_owners[pos] == owner:
        return get_unit_count_at(pos, units) >= max_stack
    return get_unit_count_at(pos, units) > 0

def get_reachable(unit: dict, grid: list, terrain: dict, cities: list, city_owners: dict, units: list, coastal_cities: set, transport_loads: dict) -> set:
    """Calculate reachable hexes for a unit within movement range."""
    pos = unit['pos']
    mov = unit['movement_left']
    utype = unit['type']
    fuel = unit['fuel'] if 'fuel' in unit else None
    if utype in ['Fighter', 'TransportPlane'] and fuel is not None:
        mov = min(mov, fuel)
    allowed = get_allowed(utype)
    visited = set()
    queue = deque([(pos[0], pos[1], 0)])
    reach = set()
    while queue:
        cq, cr, dist = queue.popleft()
        key = (cq, cr)
        if key in visited or dist > mov:
            continue
        visited.add(key)
        if key in cities and city_owners[key] is None or (key not in cities and any(u['pos'] == key and u['type'] == 'AirCarrier' and u['owner'] != unit['owner'] for u in units)):
            continue
        is_sea_unit = utype in sea_units
        allow_city = is_sea_unit and key in coastal_cities and city_owners.get(key) == unit['owner']
        loadable = is_loadable_transport_hex(key, unit, units, transport_loads, terrain, cities, city_owners, grid)
        occupied = is_hex_occupied(key, unit['owner'], units, cities, city_owners, max_stack)
        if dist == 0 or (terrain[key] in allowed or loadable or allow_city) and (not occupied or loadable):
            if utype == 'Fighter' and any(u['pos'] == key and u['type'] == 'AirCarrier' and u['owner'] == unit['owner'] and len(transport_loads.get(id(u), [])) < capacity['AirCarrier']['max'] for u in units):
                if dist > 0:
                    reach.add(key)
            if dist > 0:
                reach.add(key)
            for nq, nr in get_neighbors(cq, cr, grid):
                n_key = (nq, nr)
                if n_key in cities and city_owners[n_key] != unit['owner'] and utype != 'Infantry':
                    continue
                queue.append((nq, nr, dist + 1))
    # print(f"Reachable hexes for {utype} at {pos}: {reach}")
    return reach

def get_fuel_range(unit: dict, grid: list, terrain: dict) -> set:
    """Calculate fuel range border for Fighter and TransportPlane."""
    if unit['type'] not in ['Fighter', 'TransportPlane'] or unit['fuel'] is None:
        return set()
    pos = unit['pos']
    fuel = unit['fuel']
    allowed = get_allowed(unit['type'])
    visited = set()
    queue = deque([(pos[0], pos[1], 0)])
    range_border = set()
    max_dist = fuel
    while queue:
        cq, cr, dist = queue.popleft()
        key = (cq, cr)
        if key in visited or dist > max_dist:
            continue
        visited.add(key)
        if terrain[key] in allowed:
            if dist == max_dist:
                range_border.add(key)
            for nq, nr in get_neighbors(cq, cr, grid):
                queue.append((nq, nr, dist + 1))
    return range_border

def find_path(start: tuple, goal: tuple, unit: dict, grid: list, terrain: dict, cities: list, city_owners: dict, units: list, transport_loads: dict, capacity: dict, coastal_cities: set) -> list:
    """Find a path from start to goal for the unit using A*."""
    if start == goal:
        return []
    utype = unit['type']
    allowed = get_allowed(utype)
    is_sea_unit = utype in sea_units
    allow_city = is_sea_unit and goal in coastal_cities and city_owners.get(goal) == unit['owner']
    loadable = is_loadable_transport_hex(goal, unit, units, transport_loads, terrain, cities, city_owners, grid)
    occupied = is_hex_occupied(goal, unit['owner'], units, cities, city_owners, max_stack)
    if terrain[goal] not in allowed and not loadable and not allow_city or (occupied and not loadable):
        # print(f"Path to {goal} blocked: terrain={terrain.get(goal)}, loadable={loadable}, allow_city={allow_city}, occupied={occupied}")
        return None
    if goal in cities and city_owners[goal] is None:
        return None
    came_from = {}
    g_score = {start: 0}
    f_score = {start: hex_distance(start, goal)}
    open_set = []
    heappush(open_set, (f_score[start], start))
    while open_set:
        _, current = heappop(open_set)
        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path
        for neighbor in get_neighbors(*current, grid):
            allow_neighbor_city = is_sea_unit and neighbor in coastal_cities and city_owners.get(neighbor) == unit['owner']
            n_loadable = is_loadable_transport_hex(neighbor, unit, units, transport_loads, terrain, cities, city_owners, grid)
            n_occupied = is_hex_occupied(neighbor, unit['owner'], units, cities, city_owners, max_stack)
            if (terrain[neighbor] not in allowed and not n_loadable and not allow_neighbor_city) or (n_occupied and not n_loadable) or \
               (neighbor in cities and city_owners[neighbor] is None) or \
               (neighbor in cities and city_owners[neighbor] != unit['owner'] and utype != 'Infantry') or \
               (any(u['pos'] == neighbor and u['type'] == 'AirCarrier' and u['owner'] != unit['owner'] for u in units)) or \
               (any(u['pos'] == neighbor and u['type'] == 'AirCarrier' and u['owner'] == unit['owner'] and len(transport_loads.get(id(u), [])) >= capacity['AirCarrier']['max'] for u in units)):
                continue
            tentative_g = g_score[current] + 1
            if tentative_g < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + hex_distance(neighbor, goal)
                if neighbor not in [i[1] for i in open_set]:
                    heappush(open_set, (f_score[neighbor], neighbor))
    # print(f"No path found from {start} to {goal} for {utype}")
    return None
