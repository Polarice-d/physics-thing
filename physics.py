import pygame as py
import asyncio
import math

from pygame.math import lerp

py.init()
screen = py.display.set_mode((640,640))
clock = py.time.Clock()

class pendulum:
    def __init__(self, pivot_pos, tip_pos, mass) -> None:
        self.pivot_pos = pivot_pos
        self.tip_pos = tip_pos
        self.mass = mass

pendulums = []

async def do_physics():
    pass

def render_rect(point_a: tuple[int,int], point_b: tuple[int,int], color: tuple[int,int,int]):
    distance = math.floor(math.hypot((point_b[0]-point_a[0]), (point_b[1]-point_a[1])))
    image_orig = py.Surface((distance,10))
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

async def main():
    running = True
    while running:
    	# rendering logic here
        screen.fill((0,0,0))
        render_rect((50,100), (550,250), (255,0,0))
        render_rect((100,50), (250, 550), (0,255,0))
        # game rendering
    
        # boilerplate code
        for event in py.event.get():
            if event.type == py.QUIT:
                running = False
        # boilerplate code
     
        dt = clock.tick(60) / 1000
        dt = min(0.1, dt)
        
        py.display.flip()
        

    py.quit()

asyncio.run(main())