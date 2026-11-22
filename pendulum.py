import pygame as py
from physics import *
import threading
import math
import time
from pygame.constants import MOUSEBUTTONDOWN, MOUSEBUTTONUP
from pygame.math import lerp
import pygame_widgets
from pygame_widgets.slider import Slider
from pygame_widgets.textbox import TextBox

class GlobalGravityForce:
    def __init__(self) -> None:
        pass

    def apply(self, particle: Particle, positions: dict[Particle, Vector2], velocities: dict[Particle, Vector2]):
        return Vector2(0, -gravity * particle.mass)

class CursorForce:
    def __init__(self, stiffness: float, dampening: float) -> None:
        self.stiffness = stiffness
        self.dampening = dampening

    def apply(self, particle_key, positions: dict[Particle, Vector2], velocities: dict[Particle, Vector2]):
        if particle_key not in state.triggered_events:
            return Vector2(0,0)

        position = positions[particle_key]
        velocity = velocities[particle_key]

        final_force = Vector2(0,0)
        distance = get_distance(position, state.mouse_pos)

        if distance == 0.0:
            return Vector2(0,0)

        force = -self.stiffness * (distance)
        angle = math.atan2(position.y - state.mouse_pos.y, position.x - state.mouse_pos.x)

        final_force.x = force * math.cos(angle)
        final_force.y = force * math.sin(angle)

        final_force -= velocity * self.dampening

        return final_force

class WorldState:
    def __init__(self) -> None:
        self.mouse_pos = Vector2(0,0)
        self.triggered_events: set[Particle] = {Particle(Vector2(0,0),Vector2(0,0),0)}
        self.energy = []
        self.gravity = 0

    def set_gravity(self, g):
        self.gravity = g

    def set_energy(self, e):
        self.energy = e

# Simulation settings
SCREEN_HEIGHT = 2000
SCREEN_WIDTH = 2000
PENDULUM_COLOR = (0,255,0)
LINE_WIDTH = 7
SPHERE_RADIUS = 15
timestep = 1/5000
grabbing_strength = 1000
pixels_per_meter = 200
pendulum_len = 1.0 # Meters
gravity = 9.81 # m/s^2
stiffness = 100000.0
angle_1 = math.pi # this angle is like what you would use in a pendulum problem
angle_2 = math.pi/2
total_energy = 0

def convert_pygame(vector, screen_height) -> tuple[int, int]:
    return (round(vector.x * pixels_per_meter), round(screen_height - (vector.y * pixels_per_meter)))

def from_pygame(coordinate: tuple[int, int], screen_height: int):
    return Vector2(coordinate[0]/pixels_per_meter, (screen_height - coordinate[1])/pixels_per_meter)

def calc_energy(particles:list[Particle]):
    ke = 0
    pe = 0
    pe_g = 0
    pe_s = 0
    for particle in particles:
        ke += 0.5 * particle.get_mass() * (particle.get_scalar_velocity())**2
        pe_g += particle.get_mass() * particle.pos.y * gravity
    pe_s += 0.5 * stiffness * (get_distance(pivot, particle_1.pos) - pendulum_len)**2
    pe_s += 0.5 * stiffness * (get_distance(particle_1.pos, particle_2.pos) - pendulum_len)**2
    pe = pe_s + pe_g
    te = pe + ke
    return [ke, pe, te]

# Particles
pivot = Vector2(SCREEN_WIDTH//(2 * pixels_per_meter), SCREEN_HEIGHT//(2*pixels_per_meter))

particle_1 = Particle(
    Vector2(pivot.x + (pendulum_len) * math.sin(angle_1), pivot.y - (pendulum_len) * math.cos(angle_1)),
    Vector2(0,0),
    1,
)

particle_2 = Particle(
    Vector2(particle_1.pos.x + (pendulum_len) * math.sin(angle_2), particle_1.pos.y - (pendulum_len) * math.cos(angle_2)),
    Vector2(0,0),
    1,
)

particle_1.set_forces(
    GlobalGravityForce(),
    FixedSpringForce(stiffness, pendulum_len, pivot),
    SpringParticlesForce(stiffness, pendulum_len, particle_2),

)

particle_2.set_forces(
    GlobalGravityForce(),
    SpringParticlesForce(stiffness, pendulum_len, particle_1)
)


particles = [
    particle_1,
    particle_2,
]

for p in particles:
    p.add_force(CursorForce(1000, 30))

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

def do_physics():
    time_elapsed = 0
    while not stop.is_set():
        # Ts was not worth one bit of the effort
        step_sim(particles, timestep)
        state.set_energy(calc_energy(particles))

        time_elapsed += timestep
        time.sleep(timestep)

def main():
    running = True
    while running:
        state.mouse_pos = from_pygame(py.mouse.get_pos(), SCREEN_HEIGHT)

    	# rendering logic here
        screen.fill((0,0,0))


        for p in particles:
            py.draw.circle(screen, (255,0,0), convert_pygame(p.pos, SCREEN_HEIGHT), SPHERE_RADIUS)


        render_pendulum(convert_pygame(particle_1.pos, SCREEN_HEIGHT), convert_pygame(particle_2.pos, SCREEN_HEIGHT), PENDULUM_COLOR, LINE_WIDTH)
        render_pendulum(convert_pygame(particle_1.pos, SCREEN_HEIGHT), convert_pygame(pivot, SCREEN_HEIGHT), PENDULUM_COLOR, LINE_WIDTH)
        #py.draw.circle(screen, (255,0,0), particle1_pos.convert_pygame(SCREEN_HEIGHT), SPHERE_RADIUS)
        #py.draw.circle(screen, (255,0,0), particle2_pos.convert_pygame(SCREEN_HEIGHT), SPHERE_RADIUS)

        for particle in state.triggered_events:
            render_pendulum(convert_pygame(particle.pos, SCREEN_HEIGHT), convert_pygame(state.mouse_pos, SCREEN_HEIGHT), (0,0,255), 5)


        # boilerplate
        events = py.event.get()
        for event in events:
            if event.type == py.QUIT:
                running = False
                stop.set()

            if event.type == MOUSEBUTTONDOWN:
                for particle in particles:
                    if get_distance(state.mouse_pos, particle.pos) <= SPHERE_RADIUS/pixels_per_meter:
                        state.triggered_events.add(particle)

            if event.type == MOUSEBUTTONUP:
                state.triggered_events.clear()

        gravity = round(g_slider.getValue(), 2)
        g_label.setText(f"Gravity: {gravity} m/s²")
        total_energy_label.setText(f"Total Energy: {round(state.energy[2], 2)} J")
        kinetic_energy_label.setText(f"Kinetic Energy: {round(state.energy[0], 2)} J")
        potential_energy_label.setText(f"Potential Energy: {round(state.energy[1], 2)} J")
        pygame_widgets.update(events)
        dt = clock.tick(60) / 1000
        dt = min(0.1, dt)
        py.display.flip()

    py.quit()

# Initialization
stop = threading.Event()
py.init()
screen = py.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = py.time.Clock()
state = WorldState()
state.triggered_events.clear()
g_slider = Slider(screen, 450, 600, 300, 20, min=-2*gravity, max=2*gravity, step=0.01, initial=gravity, handleColour=(255,0,0))
g_label = TextBox(screen, 450, 650, 275, 40, fontSize=24)
g_label.disable()
total_energy_label = TextBox(screen, 450, 700, 275, 40, fontSize=24)
total_energy_label.disable()
kinetic_energy_label = TextBox(screen, 450, 750, 275, 40, fontSize=24)
kinetic_energy_label.disable()
potential_energy_label = TextBox(screen, 450, 800, 275, 40, fontSize=24)
potential_energy_label.disable()

# Running stuff
t1 = threading.Thread(target=do_physics)
t1.start()
main()
