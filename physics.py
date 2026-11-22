import pygame as py
import threading
import math
import time
from pygame.constants import MOUSEBUTTONDOWN, MOUSEBUTTONUP
from pygame.math import lerp
import pygame_widgets
from pygame_widgets.slider import Slider
from pygame_widgets.textbox import TextBox

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
gravity = 0.1 # m/s^2
stiffness = 100000.0
angle_1 = math.pi # this angle is like what you would use in a pendulum problem
angle_2 = math.pi/2
total_energy = 0

# X and Y are defined as +x is right and +y is up
class Vector2:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __str__(self) -> str:
        return f"x: {self.x}, y: {self.y}"

    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar):
        return Vector2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar):
        return Vector2(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar):
        return Vector2(self.x/scalar, self.y/scalar)

    def __neg__(self):
        return Vector2(-self.x, -self.y)

    def convert_pygame(self, screen_height) -> tuple[int, int]:
        """
        Converts from real physics (tm) position to freaky pygame pixel coordinates
        """
        return (round(self.x * pixels_per_meter), round(screen_height - (self.y * pixels_per_meter)))


    def set(self, new):
        self.x = new.x
        self.y = new.y

    def setc(self, x, y):
        self.x = x
        self.y = y

    def magnitude(self):
        return math.hypot(self.x, self.y)
    @staticmethod
    def from_pygame(coordinate: tuple[int, int], screen_height: int):
        return Vector2(coordinate[0]/pixels_per_meter, (screen_height - coordinate[1])/pixels_per_meter)

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

class Particle:
    def __init__(self, position_0: Vector2, velocity_0: Vector2, mass: float) -> None:
        self.pos = position_0
        self.vel = velocity_0
        self.mass = mass
        self.forces = []

    def set_forces(self, *forces):
        self.forces = [f for f in forces]

    def add_force(self, force):
        self.forces.append(force)

    def get_acceleration(self, positions, velocities) -> Vector2:
        acceleration = Vector2(0,0)
        for force in self.forces:
            acceleration += force.apply(self, positions, velocities)

        return acceleration

    def get_mass(self):
        return self.mass

    def get_scalar_velocity(self):
        return math.hypot(self.vel.x, self.vel.y)

# Force definitions
class GlobalGravityForce:
    def __init__(self) -> None:
        pass

    def apply(self, particle: Particle, positions: dict[Particle, Vector2], velocities: dict[Particle, Vector2]):
        return Vector2(0, -gravity * particle.mass)

class GravityForce:
    def __init__(self, g) -> None:
        self.g = g

    def apply(self, particle: Particle, positions: dict[Particle, Vector2], velocities: dict[Particle, Vector2]):
        return Vector2(0, -self.g * particle.mass)

class FixedSpringForce:
    def __init__(self, k, natural_len, pivot_pos) -> None:
        self.k = k
        self.natural_len = natural_len
        self.pivot_pos = pivot_pos

    def apply(self, particle_key, positions: dict[Particle, Vector2], velocities: dict[Particle, Vector2]):
        position = positions[particle_key]

        final_force = Vector2(0,0)
        distance = get_distance(position, self.pivot_pos)

        if distance == 0.0:
            return Vector2(0,0)

        force = -self.k * (distance - self.natural_len)
        angle = math.atan2(position.y - self.pivot_pos.y, position.x - self.pivot_pos.x)

        final_force.x = force * math.cos(angle)
        final_force.y = force * math.sin(angle)

        return final_force

class SpringParticlesForce:
    def __init__(self, k, natural_len, other_particle: Particle) -> None:
        self.k = k
        self.natural_len = natural_len
        self.other_particle = other_particle
        self.negative = False

    def apply(self, particle_key, positions: dict[Particle, Vector2], velocities: dict[Particle, Vector2]):
        position_1 = positions[particle_key]
        position_2 = positions[self.other_particle]

        final_force = Vector2(0,0)
        distance = get_distance(position_1, position_2)

        if distance == 0.0:
            return Vector2(0,0)

        force = -self.k * (distance - self.natural_len)
        angle = math.atan2(position_1.y - position_2.y, position_1.x - position_2.x)

        final_force.x = force * math.cos(angle)
        final_force.y = force * math.sin(angle)

        if self.negative:
            return -final_force
        return final_force

class AttractiveForce:
    def __init__(self, attractiveness: float, attractive_particle: Particle) -> None:
        self.attractiveness = attractiveness
        self.att_particle = attractive_particle

    def apply(self, particle_key, positions: dict[Particle, Vector2], velocities: dict[Particle, Vector2]):
        position_self = positions[particle_key]
        attractive_pos = positions[self.att_particle]

        distance = get_distance(position_self, attractive_pos)

        if distance == 0.0:
            return Vector2(0,0)
            
        force = clamp(0, self.attractiveness / (SPHERE_RADIUS/pixels_per_meter)**2, self.attractiveness / distance**2)
        direction = position_self - attractive_pos
        direction /= direction.magnitude()

        return direction * force

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

def clamp(min, max, x) -> float:
    if abs(x) <= abs(min):
        return min
    if abs(x) >= abs(max):
        return max
    return x

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

particle_3 = Particle(
    Vector2(1,1),
    Vector2(0,0),
    1
)

particle_4 = Particle (
    Vector2(2,2),
    Vector2(0,0),
    1
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

particle_3.set_forces(
    AttractiveForce(10, particle_4)
)

particles = [
    particle_1,
    particle_2,
    particle_3,
    particle_4,
]

for p in particles:
    p.add_force(CursorForce(1000, 30))
# Debug
time_elapsed = 0.0

def get_distance(a: Vector2, b: Vector2) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)

def get_accelerations(particles:list[Particle], positions: dict[Particle, Vector2], velocities: dict[Particle, Vector2]) -> dict[Particle, Vector2]:
    accelerations = {}
    for particle in particles:
        accelerations[particle] = particle.get_acceleration(positions, velocities) / particle.mass

    return accelerations

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

def rk4_advance(values, rates_change, step):
    final = {}
    for v in values:
        final[v] = values[v] + rates_change[v] * step

    return final

def solve(particles: list[Particle], timestep: float):
    halfstep = timestep / 2

    positions = {}
    velocities = {}

    for p in particles:
        positions[p] = p.pos
        velocities[p] = p.vel

    d_stage1_pos = velocities
    d_stage1_vel = get_accelerations(particles, positions, velocities)

    stage2_pos = rk4_advance(positions, d_stage1_pos, halfstep)
    stage2_vel = rk4_advance(velocities, d_stage1_vel, halfstep)
    d_stage2_pos = stage2_vel
    d_stage2_vel = get_accelerations(particles, stage2_pos, stage2_vel)

    stage3_pos = rk4_advance(positions, d_stage2_pos, halfstep)
    stage3_vel = rk4_advance(velocities, d_stage2_vel, halfstep)
    d_stage3_pos = stage3_vel
    d_stage3_vel = get_accelerations(particles, stage3_pos, stage3_vel)

    stage4_pos = rk4_advance(positions, d_stage3_pos, timestep)
    stage4_vel = rk4_advance(velocities, d_stage3_vel, timestep)
    d_stage4_pos = stage4_vel
    d_stage4_vel = get_accelerations(particles, stage4_pos, stage4_vel)

    for p in particles:
        average_position_d = (
            d_stage1_pos[p]
            + 2 * d_stage2_pos[p]
            + 2 * d_stage3_pos[p]
            + d_stage4_pos[p]
        ) * (1/6)

        average_velocity_d = (
            d_stage1_vel[p]
            + 2 * d_stage2_vel[p]
            + 2 * d_stage3_vel[p]
            + d_stage4_vel[p]
        ) * (1/6)

        p.pos = positions[p] + average_position_d * timestep
        p.vel = velocities[p] + average_velocity_d * timestep

def do_physics():
    time_elapsed = 0
    while not stop.is_set():
        # Ts was not worth one bit of the effort
        solve(particles, timestep)
        state.set_energy(calc_energy(particles))

        time_elapsed += timestep
        time.sleep(timestep*10)

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


        for p in particles:
            py.draw.circle(screen, (255,0,0), p.pos.convert_pygame(SCREEN_HEIGHT), SPHERE_RADIUS)


        render_pendulum(particle_1.pos.convert_pygame(SCREEN_HEIGHT), particle_2.pos.convert_pygame(SCREEN_HEIGHT), PENDULUM_COLOR, LINE_WIDTH)
        render_pendulum(particle_1.pos.convert_pygame(SCREEN_HEIGHT), pivot.convert_pygame(SCREEN_HEIGHT), PENDULUM_COLOR, LINE_WIDTH)
        #py.draw.circle(screen, (255,0,0), particle1_pos.convert_pygame(SCREEN_HEIGHT), SPHERE_RADIUS)
        #py.draw.circle(screen, (255,0,0), particle2_pos.convert_pygame(SCREEN_HEIGHT), SPHERE_RADIUS)

        for particle in state.triggered_events:
            render_pendulum(particle.pos.convert_pygame(SCREEN_HEIGHT), state.mouse_pos.convert_pygame(SCREEN_HEIGHT), (0,0,255), 5)


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
