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
from pygame_widgets.toggle import Toggle

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
class GravityForce:
    def __init__(self, particle1: Particle, particle2: Particle, min_radius) -> None:
        self.particle1 = particle1
        self.particle2 = particle2
        self.min_radius = min_radius
        self.mass1 = particle1.mass
        self.mass2 = particle2.mass

    def apply(self, particle_key, positions: dict[Particle, Vector2], velocities: dict[Particle, Vector2]):
        position1 = positions[particle_key]
        position2 = positions[self.particle2]

        distance = get_distance(position1, position2)

        if distance == 0.0:
            return Vector2(0,0)

        force = clamp(
            0,
            (state.gravity * self.mass1 * self.mass2) / (self.min_radius)**2,
            (state.gravity * self.mass1 * self.mass2) / distance**2
            )
        direction = position2 - position1
        direction /= direction.magnitude()

        return direction * force

class WorldState:
    def __init__(self) -> None:
        self.mouse_pos = Vector2(0,0)
        self.triggered_events: set[Particle] = {Particle(Vector2(0,0),Vector2(0,0),0)}
        self.energy = []
        self.gravity = 6
        self.time_elapsed = 0
        self.paused = False

    def set_gravity(self, g):
        self.gravity = g

    def set_energy(self, e):
        self.energy = e

# Simulation settings
SCREEN_HEIGHT = 2000
SCREEN_WIDTH = 2000
PENDULUM_COLOR = (0,255,0)
SPHERE_RADIUS = 15
timestep = 1/5000
grabbing_strength = 1000
pixels_per_meter = 200
size = 1.0 # Meters
speed = 1.5
gravity = 10
state = WorldState()

def convert_pygame(vector, screen_height) -> tuple[int, int]:
    return (round(vector.x * pixels_per_meter), round(screen_height - (vector.y * pixels_per_meter)))

def from_pygame(coordinate: tuple[int, int], screen_height: int):
    return Vector2(coordinate[0]/pixels_per_meter, (screen_height - coordinate[1])/pixels_per_meter)

def get_particles_dist(particle1: Particle, particle2: Particle):
    return math.hypot(particle1.pos.x - particle2.pos.x , particle1.pos.y - particle2.pos.y)

def calc_energy(particles:list[Particle]):
    ke = 0
    pe = 0
    for particle in particles:
        ke += 0.5 * particle.get_mass() * (particle.get_scalar_velocity())**2
    pe -= particles[0].get_mass() * particles[1].get_mass() * state.gravity / get_particles_dist(particles[0], particles[1])
    pe -= particles[0].get_mass() * particles[2].get_mass() * state.gravity / get_particles_dist(particles[0], particles[2])
    pe -= particles[1].get_mass() * particles[2].get_mass() * state.gravity / get_particles_dist(particles[1], particles[2])
    te = pe + ke
    return [ke, pe, te]

# Particles

particle_2 = Particle(
    Vector2(4 + (size) * math.cos(math.radians(120)), 4 + (size) * math.sin(math.radians(120))),
    Vector2(speed * math.cos(math.radians(210)), speed*math.sin(math.radians(210))),
    1,
)

particle_1 = Particle(
    Vector2(4 + (size) * math.cos(math.radians(0)), 4 + (size) * math.sin(math.radians(0))),
    Vector2(0, speed),
    1,
)

particle_3 = Particle(
    Vector2(4 + (size) * math.cos(math.radians(240)), 4 + (size) * math.sin(math.radians(240))),
    Vector2(speed * math.cos(math.radians(330)), speed*math.sin(math.radians(330))),
    1
)

particle_1.set_forces(
    GravityForce(particle_1, particle_2, 0.1),
    GravityForce(particle_1, particle_3, 0.1)
)

particle_2.set_forces(
    GravityForce(particle_2, particle_1, 0.1),
    GravityForce(particle_2, particle_3, 0.1)
)

particle_3.set_forces(
    GravityForce(particle_3, particle_1, 0.1),
    GravityForce(particle_3, particle_2, 0.1)
)

particles = [
    particle_1,
    particle_2,
    particle_3,
]

for p in particles:
    p.add_force(CursorForce(500, 30))

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
        if not state.paused:
            step_sim(particles, timestep)
            state.set_energy(calc_energy(particles))
            state.time_elapsed += timestep

        time.sleep(timestep)

def main():
    running = True
    while running:
        state.mouse_pos = from_pygame(py.mouse.get_pos(), SCREEN_HEIGHT)

    	# rendering logic here
        screen.fill((0,0,0))


        for p in particles:
            py.draw.circle(screen, (255,0,0), convert_pygame(p.pos, SCREEN_HEIGHT), SPHERE_RADIUS)

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
                print(state.mouse_pos)
                for particle in particles:
                    if get_distance(state.mouse_pos, particle.pos) <= SPHERE_RADIUS/pixels_per_meter:
                        state.triggered_events.add(particle)

            if event.type == MOUSEBUTTONUP:
                state.triggered_events.clear()

        state.gravity = round(g_slider.getValue(), 2)
        g_label.setText(f"Gravity constant: {state.gravity}")
        total_energy_label.setText(f"Total Energy: {round(state.energy[2], 2)} J")
        kinetic_energy_label.setText(f"Kinetic Energy: {round(state.energy[0], 2)} J")
        potential_energy_label.setText(f"Potential Energy: {round(state.energy[1], 2)} J")
        time_elapsed_label.setText(f"Time Elapsed: {round(state.time_elapsed, 3)} s")
        on_condition = "running" if on_off_toggle.getValue() else "paused"
        toggle_label.setText(f'Sim: {on_condition}')
        state.paused = not on_off_toggle.getValue()
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
state.triggered_events.clear()
g_slider = Slider(screen, 450, 600, 300, 20, min=-2*gravity, max=2*gravity, step=0.01, initial=state.gravity, handleColour=(255,0,0))
g_label = TextBox(screen, 450, 650, 310, 40, fontSize=24)
g_label.disable()
total_energy_label = TextBox(screen, 450, 700, 310, 40, fontSize=24)
total_energy_label.disable()
kinetic_energy_label = TextBox(screen, 450, 750, 310, 40, fontSize=24)
kinetic_energy_label.disable()
potential_energy_label = TextBox(screen, 450, 800, 310, 40, fontSize=24)
potential_energy_label.disable()
on_off_toggle = Toggle(screen, 870, 600, 40, 20, startOn=True, handleOnColour=(255,0,0),onColour=(0,0,255))
toggle_label = TextBox(screen, 940, 590, 210, 40, fontSize=24)
toggle_label.disable()
time_elapsed_label = TextBox(screen, 850, 650, 310, 40, fontSize=24)
time_elapsed_label.disable()

# Running stuff
t1 = threading.Thread(target=do_physics)
t1.start()
main()
