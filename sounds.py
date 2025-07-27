import pygame
import numpy as np

def init_sounds():
    pygame.mixer.init()
    # Simple error beep (440Hz sine wave for 0.2 seconds)
    sample_rate = 44100
    duration = 0.2
    freq = 440
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    beep_wave = np.sin(2 * np.pi * freq * t) * 0.5
    beep_wave = (beep_wave * 32767).astype(np.int16)
    error_sound = pygame.mixer.Sound(beep_wave)
    # Good sound (higher pitch, 880Hz sine wave for 0.2 seconds)
    freq_good = 880
    good_wave = np.sin(2 * np.pi * freq_good * t) * 0.5
    good_wave = (good_wave * 32767).astype(np.int16)
    good_sound = pygame.mixer.Sound(good_wave)
    return error_sound, good_sound

