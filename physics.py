import math


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

    def magnitude(self):
        return math.hypot(self.x, self.y)

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
    def __init__(self, attractiveness: float, attractive_particle: Particle, min_radius) -> None:
        self.attractiveness = attractiveness
        self.att_particle = attractive_particle
        self.min_radius = min_radius

    def apply(self, particle_key, positions: dict[Particle, Vector2], velocities: dict[Particle, Vector2]):
        position_self = positions[particle_key]
        attractive_pos = positions[self.att_particle]

        distance = get_distance(position_self, attractive_pos)

        if distance == 0.0:
            return Vector2(0,0)

        force = clamp(0, self.attractiveness / (self.min_radius)**2, self.attractiveness / distance**2)
        direction = position_self - attractive_pos
        direction /= direction.magnitude()

        return direction * force

def clamp(min, max, x) -> float:
    if abs(x) <= abs(min):
        return min
    if abs(x) >= abs(max):
        return max
    return x

# Debug
time_elapsed = 0.0

def get_distance(a: Vector2, b: Vector2) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)

def _get_accelerations(particles:list[Particle], positions: dict[Particle, Vector2], velocities: dict[Particle, Vector2]) -> dict[Particle, Vector2]:
    accelerations = {}
    for particle in particles:
        accelerations[particle] = particle.get_acceleration(positions, velocities) / particle.mass

    return accelerations

def _rk4_advance(values, rates_change, step):
    final = {}
    for v in values:
        final[v] = values[v] + rates_change[v] * step

    return final

def step_sim(particles: list[Particle], timestep: float):

    halfstep = timestep / 2

    positions = {}
    velocities = {}

    for p in particles:
        positions[p] = p.pos
        velocities[p] = p.vel

    d_stage1_pos = velocities
    d_stage1_vel = _get_accelerations(particles, positions, velocities)

    stage2_pos = _rk4_advance(positions, d_stage1_pos, halfstep)
    stage2_vel = _rk4_advance(velocities, d_stage1_vel, halfstep)
    d_stage2_pos = stage2_vel
    d_stage2_vel = _get_accelerations(particles, stage2_pos, stage2_vel)

    stage3_pos = _rk4_advance(positions, d_stage2_pos, halfstep)
    stage3_vel = _rk4_advance(velocities, d_stage2_vel, halfstep)
    d_stage3_pos = stage3_vel
    d_stage3_vel = _get_accelerations(particles, stage3_pos, stage3_vel)

    stage4_pos = _rk4_advance(positions, d_stage3_pos, timestep)
    stage4_vel = _rk4_advance(velocities, d_stage3_vel, timestep)
    d_stage4_pos = stage4_vel
    d_stage4_vel = _get_accelerations(particles, stage4_pos, stage4_vel)

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
