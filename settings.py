import numpy as np

# Screen settings
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 800

# Colors
WHITE = (255, 255, 255)
LIGHT_RED = (255, 100, 100)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
BROWN = (139, 69, 19)
GREY = (128, 128, 128)
RED = (255, 0, 0)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
LIGHT_BLACK = (100, 100, 100)
LIGHT_WHITE = (200, 200, 200)
ORANGE = (255, 165, 0)
DARK_RED = (139, 0, 0)

# Hex settings
HEX_SIZE = 20

# Unit stats
unit_stats = {
    'Infantry': {'max_hp': 10, 'attack': 2, 'defense': 2, 'range': 1},
    'Tank': {'max_hp': 20, 'attack': 4, 'defense': 4, 'range': 1},
    'Fighter': {'max_hp': 20, 'attack': 4, 'defense': 3, 'range': 1},
    'TransportPlane': {'max_hp': 30, 'attack': 0, 'defense': 4, 'range': 1},
    'TransportShip': {'max_hp': 30, 'attack': 0, 'defense': 4, 'range': 1},
    'Destroyer': {'max_hp': 30, 'attack': 5, 'defense': 5, 'range': 1},
    'Cruiser': {'max_hp': 50, 'attack': 6, 'defense': 6, 'range': 2},
    'AirCarrier': {'max_hp': 100, 'attack': 2, 'defense': 6, 'range': 1},
}

# Units
unit_types = ['Infantry', 'Tank', 'Fighter', 'TransportPlane', 'TransportShip', 'Destroyer', 'Cruiser', 'AirCarrier']
sea_units = ['TransportShip', 'Destroyer', 'Cruiser', 'AirCarrier']
unit_digits = {'Infantry': '1', 'Tank': '2', 'Fighter': '3', 'TransportPlane': '4', 'TransportShip': '5', 'Destroyer': '6', 'Cruiser': '7', 'AirCarrier': '8'}
costs = {'Infantry': 1, 'Tank': 1, 'Fighter': 1, 'TransportPlane': 1, 'TransportShip': 1, 'Destroyer': 1, 'Cruiser': 1, 'AirCarrier': 1}
movements = {'Infantry': 1, 'Tank': 2, 'Fighter': 3, 'TransportPlane': 4, 'TransportShip': 2, 'Destroyer': 2, 'Cruiser': 1, 'AirCarrier': 1}
max_fuel = {'Fighter': 30, 'TransportPlane': 30, 'AirCarrier': 30}
capacity = {
    'TransportShip': {'max': 3, 'allowed': ['Infantry', 'Tank']},
    'TransportPlane': {'max': 2, 'allowed': ['Infantry', 'Tank']},
    'AirCarrier': {'max': 5, 'allowed': ['Fighter']}
}

# Players
players = ['red', 'black', 'white']
player_colors = {'red': RED, 'black': BLACK, 'white': WHITE}
light_colors = {'red': LIGHT_RED, 'black': LIGHT_BLACK, 'white': LIGHT_WHITE}
digit_colors = {'red': WHITE, 'black': WHITE, 'white': BLACK}
production_text_colors = {'red': BLACK, 'black': WHITE, 'white': BLACK}

# City settings
city_max_hp = 15
city_attack = 2
city_defense = 3
city_range = 1
min_city_hp = max(1, int(0.1 * city_max_hp))
max_stack = 5

# Terrain bonuses (e.g., defense multiplier)
terrain_bonuses = {
    'mountain': {'defense': 1.2},
    'land': {'defense': 1.0},
    'water': {'defense': 1.0}
}
