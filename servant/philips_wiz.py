import asyncio
import json
import traceback
from pywizlight import wizlight, PilotBuilder, discovery


async def wiz_get_state():
    b = wizlight("192.168.1.159")
    bulbtype = await b.get_bulbtype()
    #bulbtype_dict = bulbtype.as_dict()
    # Get the current color temperature, RGB values
    state = await b.updateState()
    status = {
        'warm_white': state.get_warm_white(),
        'cold_white': state.get_cold_white(),
        'rgb': state.get_rgb(),
        'rgbww': state.get_rgbww(),
        'rgbw': state.get_rgbw(),
        'scene': state.get_scene_id(),
        'speed': state.get_speed(),
        'ratio': state.get_ratio(),
        'colortemp': state.get_colortemp(),
        'brightness': state.get_brightness(),
    }
    #print(f"{bulbtype_dict['name']}: {status}")
    return status

async def wiz_set_state(parsed_cmd):
    b = wizlight("192.168.1.159")
    # apply some needed changes to the parsed_cmd
    if 'action' in parsed_cmd:
        action = parsed_cmd.pop("action")
    else:
        action = 'on'
    if 'scene' in parsed_cmd and int(parsed_cmd['scene']) == 0:
        parsed_cmd['scene'] = None
    parsed_cmd['state'] = True if action == 'on' else False
    settings = PilotBuilder(**parsed_cmd)
    await b.turn_on(settings)


async def main():
    print(await wiz_get_state())
    cmd = '{"action": "on", "rgbww": [0, 0, 255, 0, 0], "scene": 0}'
    #cmd = '{"action": "on", "rgbww": [255, 0, 255, 200, 100], "scene": 0, "speed": null, "colortemp": null, "brightness": 255}'
    cmd_parsed = json.loads(cmd)
    await wiz_set_state(cmd_parsed)
    # Once we exit the `with` block, all bulbs get closed in __aexit__()

if __name__ == "__main__":
    asyncio.run(main())
