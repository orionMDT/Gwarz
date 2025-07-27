import random
from hex_utils import hex_distance, get_neighbors
from units import get_allowed
from settings import players, unit_stats, movements, city_max_hp, capacity

def select_spaced_cities(hexes, min_dist, num):
    selected = []
    candidates = hexes[:]
    random.shuffle(candidates)
    for cand in candidates:
        if len(selected) >= num:
            break
        if all(hex_distance(cand, s) >= min_dist for s in selected):
            selected.append(cand)
    return selected

def generate_cities_and_coastal(grid, terrain):
    land_hexes = [h for h in grid if terrain[h] == 'land']
    coastal_land = [h for h in land_hexes if any(terrain.get(n, '') == 'water' for n in get_neighbors(*h, grid))]
    non_coastal = list(set(land_hexes) - set(coastal_land))

    num_cities = 30
    num_coastal = max(5, min(len(coastal_land), num_cities // 2 + num_cities % 2))
    coastal_selected = select_spaced_cities(coastal_land, 10, num_coastal)
    remaining = num_cities - len(coastal_selected)
    non_coastal_selected = select_spaced_cities(non_coastal, 10, remaining)
    cities = coastal_selected + non_coastal_selected
    random.shuffle(cities)

    coastal_cities = set()
    for c in cities:
        q, r = c
        for nq, nr in get_neighbors(q, r, grid):
            if terrain[(nq, nr)] == 'water':
                coastal_cities.add(c)
                break

    return cities, coastal_cities

def assign_starting_cities_and_units(cities, coastal_cities, players, grid, unit_stats, movements):
    coastal_list = list(coastal_cities)
    start_cities = []
    start_cities.append(random.choice(coastal_list))
    min_d = 5
    max_d = 10
    candidates2 = [c for c in coastal_list if c != start_cities[0] and min_d <= hex_distance(c, start_cities[0]) <= max_d]
    if not candidates2:
        candidates2 = [c for c in coastal_list if c != start_cities[0]]
    start_cities.append(random.choice(candidates2))
    candidates3 = [c for c in coastal_list if c not in start_cities and all(min_d <= hex_distance(c, s) <= max_d for s in start_cities)]
    if not candidates3:
        candidates3 = [c for c in coastal_list if c not in start_cities]
    start_cities.append(random.choice(candidates3))

    city_owners = {c: None for c in cities}
    units = []
    for i, player in enumerate(players):
        city = start_cities[i]
        city_owners[city] = player
        utype = 'Infantry'
        stats = unit_stats[utype]
        units.append({
            'pos': city,
            'type': utype,
            'movement_left': movements[utype],
            'owner': player,
            'fuel': None,
            'hp': stats['max_hp'],
            'max_hp': stats['max_hp'],
            'attack': stats['attack'],
            'defense': stats['defense'],
            'range': stats['range'],
            'did_move': False,
            'sentry': False
        })

    transport_loads = {id(u): [] for u in units if u['type'] in capacity}
    productions = {c: {'unit': None, 'turns_left': 0} for c in cities}
    city_hp = {c: city_max_hp for c in cities}

    return city_owners, units, transport_loads, productions, city_hp, start_cities
