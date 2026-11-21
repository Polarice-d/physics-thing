import pygame as py
import threading
import math
import time

from pygame.math import lerp

py.init()
screen = py.display.set_mode((640,640))
clock = py.time.Clock()

stop = threading.Event()

# initializing variables
global point_pos; point_pos = [400,250]
global pivot_pos; pivot_pos = [320, 250]

def do_physics():
    l_0 = 80
    k = 100000000
    m = 10
    g = 100000
    v_p = [0,0]
    a_p = [0,0]
    dt = 0.0001
    while not stop.is_set():
        def get_acceleration(k, m, l_0, point_pos, pivot_pos):
            """
            returns acceleration vector for particle on spring
            """
            x = point_pos[0]
            y = point_pos[1]
            x_0 = pivot_pos[0]
            y_0 = pivot_pos[1]
            a = [0,0]
            distance = math.hypot(x-x_0, y - y_0)
            a[0] = (-k/m)*(distance - l_0)*(math.cos(math.atan2(640-(y - y_0),(x-x_0))))
            a[1] = (-k/m)*(distance - l_0)*(math.sin(math.atan2(640-(y - y_0),(x-x_0)))) + g
            return a
        a_p = get_acceleration(k, m, l_0, point_pos, pivot_pos)
        v_p[0] += a_p[0] * dt
        v_p[1] += a_p[1] * dt
        point_pos[0] += v_p[0] * dt
        point_pos[1] += v_p[1] * dt
        #print(f'pos: {point_pos}')
        time.sleep(dt)

def render_rect(point_a: tuple[int,int], point_b: tuple[int,int], color: tuple[int,int,int]):
    distance = math.floor(math.hypot((point_b[0]-point_a[0]), (point_b[1]-point_a[1])))
    image_orig = py.Surface((distance,3))
    image_orig.set_colorkey((0,0,0))
    image_orig.fill(color)
    image = image_orig.copy()
    image.set_colorkey((0,0,0))
    rect = image.get_rect( )

    center_x = math.floor(lerp(point_a[0], point_b[0], 0.5))
    center_y = math.floor(lerp(point_a[1], point_b[1], 0.5))

    angle = -math.degrees(math.atan2(point_b[1] - point_a[1], point_b[0] - point_a[0]))

    rect.center = (center_x, center_y)
    new_image = py.transform.rotate(image_orig , angle)
    rect = new_image.get_rect(center=(center_x, center_y))

    screen.blit(new_image , rect)

def main():
    running = True
    while running:
    	# rendering logic here
        screen.fill((0,0,0))
        render_rect(pivot_pos, point_pos, (255,0,0))
        for event in py.event.get():
            if event.type == py.QUIT:
                running = False
                stop.set()
        dtt = clock.tick(60) / 1000
        dtt = min(0.1, dtt)
        py.display.flip()

    py.quit()

t1 = threading.Thread(target=do_physics)
t1.start()

main()
