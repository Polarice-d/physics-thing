import pygame as py
import asyncio

py.init()

screen = py.display.set_mode((640,640))

clock = py.time.Clock()

async def do_physics():
    pass

async def main():
    rot = 0
    rot_speed = 2
    image_orig = py.Surface((100,100))
    image_orig.set_colorkey((0,0,0))
    image_orig.fill((255,0,0))
    
    image = image_orig.copy()
    image.set_colorkey((0,0,0))
    
    rect = image.get_rect( )
    rect.center = (320, 320)
    running = True
    while running:
        screen.fill((0,0,0))
        for event in py.event.get():
            if event.type == py.QUIT:
                running = False
                

        dt = clock.tick(60) / 1000
        dt = min(0.1, dt)
        
        old_center = rect.center
        rot = (rot + rot_speed) % 360 

        new_image = py.transform.rotate(image_orig , rot)  
        rect = new_image.get_rect()

        rect.center = old_center 

        screen.blit(new_image , rect)
    
        
        py.display.flip()
        

    py.quit()

asyncio.run(main())