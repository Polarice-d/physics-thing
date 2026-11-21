from tokenize import Double

import pygame as py
import threading
import math
import time
from pygame.constants import MOUSEBUTTONDOWN, MOUSEBUTTONUP
from pygame.math import lerp

# X and Y are defined as +x is right and +y is up
class Vector2:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __str__(self) -> str:
        return f"x: {self.x}, y: {self.y}"
        
    def convert_pygame(self, screen_height) -> tuple[int, int]:
        """
        Converts from real physics (tm) position to freaky pygame pixel coordinates
        """
        return (round(self.x * pixels_per_meter), round(screen_height - (self.y * pixels_per_meter)))

    def negate(self):
        return Vector2(-self.x, -self.y)

    @staticmethod
    def from_pygame(coordinate: tuple[int, int], screen_height: int):
        return Vector2(coordinate[0]/pixels_per_meter, (screen_height - coordinate[1])/pixels_per_meter)

class GameState:
    def __init__(self) -> None:
        self.mouse_pos = Vector2(0,0)
        self.triggered_events: set[int] = {0}

# Simulation settings
SCREEN_HEIGHT = 2000
SCREEN_WIDTH = 2000
PENDULUM_COLOR = (0,255,0)
LINE_WIDTH = 7
SPHERE_RADIUS = 15
timestep = 0.000001
grabbing_strength = 1000
pixels_per_meter = 200


# Initial parameters
nat_len = 1.0 # Meters
k = 100000.0 
mass = 5 # Kg
grav = 9.81 # m/s^2
angle_1 = math.pi # this angle is like what you would use in a pendulum problem
angle_2 = math.pi/2

pivot_pos = Vector2(SCREEN_WIDTH//(2 * pixels_per_meter), SCREEN_HEIGHT//(2*pixels_per_meter))
particle1_pos = Vector2(pivot_pos.x + (nat_len) * math.sin(angle_1), pivot_pos.y - (nat_len) * math.cos(angle_1))
particle2_pos = Vector2(particle1_pos.x + (nat_len) * math.sin(angle_2), particle1_pos.y - (nat_len) * math.cos(angle_2))

# particle_pos = Vector2(0,0)

particle1_vel = Vector2(0,0)
particle1_acc = Vector2(0,0)

particle2_vel = Vector2(0,0)
particle2_acc = Vector2(0,0)

# Debug
time_elapsed = 0.0

def cursor_spring_force(active: bool, particle: Vector2, particle_vel: Vector2, cursor: Vector2, k: float, c: float):
    if not active:
        return Vector2(0,0)

    final_force = Vector2(0,0)
    distance = get_distance(particle, cursor)

    force = -k * (distance)
    angle = math.atan2(particle.y - cursor.y, particle.x - cursor.x)
    
    final_force.x = force * math.cos(angle)
    final_force.y = force * math.sin(angle)

    final_force.x += -(particle_vel.x) * c
    final_force.y += -(particle_vel.y) * c
    
    return final_force

def spring_force(particle: Vector2, pivot: Vector2, k: float, nat_len: float) -> Vector2:
    final_force = Vector2(0,0)
    distance = get_distance(particle, pivot)

    force = -k * (distance - nat_len)
    angle = math.atan2(particle.y - pivot.y, particle.x - pivot.x)
    
    final_force.x = force * math.cos(angle)
    final_force.y = force * math.sin(angle)

    return final_force

def gravity_force(g: float, mass: float) -> Vector2:
    return Vector2(0, -mass * g)

def dampening_force(velocity: Vector2, c: float):
    return Vector2(-(velocity.x) * c, -(velocity.y) * c)

def get_distance(a: Vector2, b: Vector2) -> float:
    return math.hypot(b.x - a.x, b.y - a.y)

def force_solver(mass: float, *forces: Vector2) -> Vector2:
    final_accel = Vector2(0,0)
    for force in forces:
        final_accel.x += force.x / mass
        final_accel.y += force.y / mass
    return final_accel

def do_physics():
    time_elapsed = 0
    while not stop.is_set():
        particle1_acc = force_solver(mass,
            spring_force(particle1_pos, pivot_pos, k, nat_len),
            spring_force(particle2_pos, particle1_pos, k, nat_len).negate(),
            dampening_force(particle1_vel, 1),
            gravity_force(mass, grav))
        particle1_vel.x += particle1_acc.x * timestep
        particle1_vel.y += particle1_acc.y * timestep
        
        particle1_pos.x += particle1_vel.x * timestep
        particle1_pos.y += particle1_vel.y * timestep

        particle2_acc = force_solver(mass,
            spring_force(particle2_pos, particle1_pos, k, nat_len),
            dampening_force(particle2_vel, 1),
            gravity_force(mass, grav))
        particle2_vel.x += particle2_acc.x * timestep
        particle2_vel.y += particle2_acc.y * timestep
        
        particle2_pos.x += particle2_vel.x * timestep
        particle2_pos.y += particle2_vel.y * timestep

        energy1 = 0.5 * mass * math.hypot(particle1_vel.x, particle1_vel.y) ** 2 + mass * grav * particle1_pos.y
        energy2 = 0.5 * mass * math.hypot(particle2_vel.x, particle2_vel.y) ** 2 + mass * grav * particle2_pos.y
        
        #print(f'Energy = [{energy1 + energy2}]')
        time_elapsed += timestep
        time.sleep(0)

def render_pendulum(point_a: tuple[int,int], point_b: tuple[int,int], color: tuple[int,int,int], thickness: int):
    distance = math.floor(math.hypot((point_b[0]-point_a[0]), (point_b[1]-point_a[1])))
    image_orig = py.Surface((distance, thickness))
    image_orig.set_colorkey((0,0,0))
    image_orig.fill(color)
    image = image_orig.copy()
    image.set_colorkey((0,0,0))
    rect = image.get_rect()

    center_x = math.floor(lerp(point_a[0], point_b[0], 0.5))
    center_y = math.floor(lerp(point_a[1], point_b[1], 0.5))

    angle = -math.degrees(math.atan2(point_b[1] - point_a[1], point_b[0] - point_a[0]))

    rect.center = (center_x, center_y)
    new_image = py.transform.rotate(image_orig , angle)
    rect = new_image.get_rect(center=(center_x, center_y))

    screen.blit(new_image, rect)

def main():
    running = True
    while running:
        state.mouse_pos = Vector2.from_pygame(py.mouse.get_pos(), SCREEN_HEIGHT)
        
    	# rendering logic here
        screen.fill((0,0,0))
        render_pendulum(pivot_pos.convert_pygame(SCREEN_HEIGHT), particle1_pos.convert_pygame(SCREEN_HEIGHT), PENDULUM_COLOR, LINE_WIDTH)
        render_pendulum(particle1_pos.convert_pygame(SCREEN_HEIGHT), particle2_pos.convert_pygame(SCREEN_HEIGHT), PENDULUM_COLOR, LINE_WIDTH)
        py.draw.circle(screen, (255,0,0), particle1_pos.convert_pygame(SCREEN_HEIGHT), SPHERE_RADIUS)
        py.draw.circle(screen, (255,0,0), particle2_pos.convert_pygame(SCREEN_HEIGHT), SPHERE_RADIUS)
        
        if 1 in state.triggered_events:
            render_pendulum(particle1_pos.convert_pygame(SCREEN_HEIGHT), state.mouse_pos.convert_pygame(SCREEN_HEIGHT), (0,0,255), 5)
        py.display.update()


        # boilerplate
        for event in py.event.get():
            if event.type == py.QUIT:
                running = False
                stop.set()
            
            print(state.mouse_pos)
            if event.type == MOUSEBUTTONDOWN:
                if get_distance(state.mouse_pos, particle1_pos) <= SPHERE_RADIUS:
                    state.triggered_events.add(1)

            if event.type == MOUSEBUTTONUP:
                state.triggered_events.clear()

        dt = clock.tick(60) / 1000
        dt = min(0.1, dt)
        py.display.flip()

    py.quit()

# Initialization
stop = threading.Event()
py.init()
screen = py.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = py.time.Clock()
state = GameState()

# Running stuff
t1 = threading.Thread(target=do_physics)
t1.start()
main()