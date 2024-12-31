import asyncio
from pywizlight import wizlight, PilotBuilder, discovery

class WizLighting:
    def __init__(self, broadcast_space="192.168.1.255"):
        self.broadcast_space = broadcast_space
        self.bulbs = []

    async def initialize(self):
        self.bulbs = [wizlight("192.168.1.159")]
        #self.bulbs = await discovery.discover_lights(broadcast_space=self.broadcast_space)
        print(f"Discovered {len(self.bulbs)} bulbs.")
        for b in self.bulbs:
            print(f"{await b.get_bulbtype()}")

    async def __aenter__(self):
        # Could do discovery here or externally
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # This will be called automatically when exiting the context
        tasks = [bulb.async_close() for bulb in self.bulbs]
        await asyncio.gather(*tasks)

    async def turn_on_all(self):
        tasks = [bulb.turn_on(PilotBuilder()) for bulb in self.bulbs]
        await asyncio.gather(*tasks)

    async def turn_off_all(self):
        tasks = [bulb.turn_off() for bulb in self.bulbs]
        await asyncio.gather(*tasks)

    async def set_color(self, r: int, g: int, b:int,
                        warm_white: int = 255, cold_white: int = 128,
                        brightness = None):
        for bulb in self.bulbs:
            # Set RGB values, deactivate scene
            if brightness:
                settings = PilotBuilder(rgbww=(r, g, b, warm_white, cold_white),
                                        scene = None,
                                        speed=200)
            else:
                settings = PilotBuilder(rgbww=(r, g, b, warm_white, cold_white),
                                        scene=None,
                                        brightness=brightness,
                                        speed=200)
            await bulb.turn_on(settings)

    async def get_state(self):
        states = {}
        for b in self.bulbs:
            bulbtype = await b.get_bulbtype()
            bulbtype_dict = bulbtype.as_dict()
            # Get the current color temperature, RGB values
            state = await b.updateState()
            status = {
                'warm_white': state.get_warm_white(),
                'cold_white': state.get_cold_white(),
                'rgb': state.get_rgb(),
                'rgbww': state.get_rgbww(),
                'rgbw': state.get_rgbw(),
                'scene_id': state.get_scene_id(),
                'speed': state.get_speed(),
                'ratio': state.get_ratio(),
                'colortemp': state.get_colortemp(),
                'brightness': state.get_brightness(),
            }
            print(f"{bulbtype_dict['name']}: {status}")
            states[bulbtype.as_dict()["name"]] = status
        return states

async def main():
    async with WizLighting("192.168.1.255") as wiz:
        # Bulbs are discovered in __aenter__()
        #await wiz.turn_on_all()
        await wiz.set_color(r=255, g=0, b=0, warm_white=255, cold_white=255, brightness=255)
        await asyncio.sleep(1)
        await wiz.get_state()

    # Once we exit the `with` block, all bulbs get closed in __aexit__()

if __name__ == "__main__":
    asyncio.run(main())
