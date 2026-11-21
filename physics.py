import pygame as py
import threading
import math
import time
from pygame.math import lerp

# X and Y are defined as +x is right and +y is up
class Vector2:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __str__(self) -> str:
        return f"x: {self.x}, y: {self.y}"
    def convert_pygame(self, height) -> tuple[int, int]:
        """
        Converts from real physics (tm) position to freaky pygame pixel coordinates
        """
        return (round(self.x), round(height - self.y))

# Simulation settings
SCREEN_HEIGHT = 800
SCREEN_WIDTH = 800
PENDULUM_COLOR = (0,255,0)
LINE_WIDTH = 10
SPHERE_RADIUS = 15
timestep = 0.0001

# Initial parameters
nat_len = 200.0
k = 100000.0
mass = 10.0
grav = 1000.0
angle_rad = math.pi / 1.5 # this angle is like what you would use in a pendulum problem

pivot_pos = Vector2(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)
particle_pos = Vector2(pivot_pos.x + nat_len * math.sin(angle_rad), pivot_pos.y - nat_len * math.cos(angle_rad))
# particle_pos = Vector2(0,0)

particle_vel = Vector2(0,0)
point_acc = Vector2(0,0)


# Debug
time_elapsed = 0.0

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
        particle_acc = force_solver(mass, spring_force(particle_pos, pivot_pos, k, nat_len), gravity_force(mass, grav))
        particle_vel.x += particle_acc.x * timestep
        particle_vel.y += particle_acc.y * timestep
        
        particle_pos.x += particle_vel.x * timestep
        particle_pos.y += particle_vel.y * timestep
        
        print(f'Energy = [{0.5 * mass * math.hypot(particle_vel.x, particle_vel.y) ** 2 + mass * grav * particle_pos.y}]')

        time_elapsed += timestep
        time.sleep(timestep)

def render_pendulum(point_a: tuple[int,int], point_b: tuple[int,int], color: tuple[int,int,int]):
    distance = math.floor(math.hypot((point_b[0]-point_a[0]), (point_b[1]-point_a[1])))
    image_orig = py.Surface((distance, LINE_WIDTH))
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
    	# rendering logic here
        screen.fill((0,0,0))
        render_pendulum(pivot_pos.convert_pygame(SCREEN_HEIGHT), particle_pos.convert_pygame(SCREEN_HEIGHT), PENDULUM_COLOR)
        py.draw.circle(screen, (255,0,0), particle_pos.convert_pygame(SCREEN_HEIGHT), SPHERE_RADIUS)
        py.display.update()

        # boilerplate
        for event in py.event.get():
            if event.type == py.QUIT:
                running = False
                stop.set()
        dt = clock.tick(60) / 1000
        dt = min(0.1, dt)
        py.display.flip()

    py.quit()

# Initialization
stop = threading.Event()
py.init()
screen = py.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = py.time.Clock()

# Running stuff
t1 = threading.Thread(target=do_physics)
t1.start()
main()