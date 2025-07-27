import math
import random
import numpy as np

def generate_perlin_noise_2d(shape, res):
    def f(t):
        return 6 * t**5 - 15 * t**4 + 10 * t**3
    
    delta = (res[0] / shape[0], res[1] / shape[1])
    d = (shape[0] // res[0], shape[1] // res[1])
    
    grid = np.mgrid[0:res[0]:delta[0], 0:res[1]:delta[1]].transpose(1, 2, 0) % 1
    
    # Gradients
    angles = 2 * np.pi * np.random.rand(res[0] + 1, res[1] + 1)
    gradients = np.dstack((np.cos(angles), np.sin(angles)))
    g00 = gradients[0:-1, 0:-1].repeat(d[0], 0).repeat(d[1], 1)
    g10 = gradients[1: , 0:-1].repeat(d[0], 0).repeat(d[1], 1)
    g01 = gradients[0:-1, 1: ].repeat(d[0], 0).repeat(d[1], 1)
    g11 = gradients[1: , 1: ].repeat(d[0], 0).repeat(d[1], 1)
    
    # Ramps
    n00 = np.sum(grid * g00, 2)
    n10 = np.sum(np.dstack((grid[:, :, 0] - 1, grid[:, :, 1])) * g10, 2)
    n01 = np.sum(np.dstack((grid[:, :, 0], grid[:, :, 1] - 1)) * g01, 2)
    n11 = np.sum(np.dstack((grid[:, :, 0] - 1, grid[:, :, 1] - 1)) * g11, 2)
    
    # Interpolation
    t = f(grid)
    n0 = n00 * (1 - t[:, :, 0]) + t[:, :, 0] * n10
    n1 = n01 * (1 - t[:, :, 0]) + t[:, :, 0] * n11
    return np.sqrt(2) * ((1 - t[:, :, 1]) * n0 + t[:, :, 1] * n1)

def generate_fractal_noise_2d(shape, res, octaves=1, persistence=0.5):
    noise = np.zeros(shape)
    frequency = 1
    amplitude = 1
    for _ in range(octaves):
        noise += amplitude * generate_perlin_noise_2d(shape, (frequency * res[0], frequency * res[1]))
        frequency *= 2
        amplitude *= persistence
    return noise

def generate_grid_and_terrain():
    hex_radius = 60
    circular_radius = 40
    grid = [(q, r) for q in range(-hex_radius, hex_radius + 1)
            for r in range(max(-hex_radius, -q - hex_radius), min(hex_radius, -q + hex_radius) + 1)]
    grid = [(q, r) for q, r in grid if math.sqrt((q + r/2)**2 + (r * math.sqrt(3)/2)**2) <= circular_radius]

    noise_shape = (128, 128)
    res = (8, 8)
    octaves = 4
    persistence = 0.5
    noise = generate_fractal_noise_2d(noise_shape, res, octaves, persistence)

    noise_offset = noise_shape[0] // 2 - hex_radius
    noise_values = [noise[r + hex_radius + noise_offset, q + hex_radius + noise_offset] for q, r in grid]
    noise_values.sort()
    water_threshold = noise_values[int(0.48 * len(noise_values))]
    mountain_threshold = noise_values[int(0.925 * len(noise_values))]

    terrain = {}
    for q, r in grid:
        val = noise[r + hex_radius + noise_offset, q + hex_radius + noise_offset]
        if val < water_threshold:
            terrain[(q, r)] = 'water'
        elif val > mountain_threshold:
            terrain[(q, r)] = 'mountain'
        else:
            terrain[(q, r)] = 'land'

    # Force circular border with water
    for q, r in grid:
        dist = math.sqrt((q + r/2)**2 + (r * math.sqrt(3)/2)**2)
        if dist >= circular_radius - 2:
            terrain[(q, r)] = 'water'

    return grid, terrain
