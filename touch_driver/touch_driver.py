"""
RPi Touch driver.

Following is referenced from:
https://stackoverflow.com/a/54986161/10909029
"""

import json
import pathlib
from typing import Tuple, Union

import evdev
from evdev.ecodes import EV_ABS, EV_KEY, ABS_X, ABS_Y, BTN_TOUCH


LCD_DATA = pathlib.Path(__file__).parent / "lcd_data.json"
LCD_DATA = json.load(LCD_DATA.open(encoding="utf8"))
DEFAULT_DEVICE = "event0"


def _raw_coord_to_pixel_closure(pixel_dim, hw_origin, hw_end):
    """Creates raw-2-pixel coordinate convertor from HW origin & end coordinates.
    origin & end is found in `xorg.conf.d/99-calibration.conf`'s Calibration.

    Returns:
        Function converting HW coordination to Pixel Coordination
    """

    # This need to be really fast - make all calc done in advance, no ifs.
    x_ori, y_ori = hw_origin
    x_end, y_end = hw_end

    x_d = x_end - x_ori
    y_d = y_end - y_ori
    x_d_abs = abs(x_d)
    y_d_abs = abs(y_d)

    w_divider = x_d_abs / pixel_dim[0]
    h_divider = y_d_abs / pixel_dim[1]

    # could've reduced 2 call overheads if python3.10+ works with pygame on pi...
    if x_d < 0:
        def _x_convert(x):
            return (x_d_abs - x + x_end) / w_divider
    else:
        def _x_convert(x):
            return (x - x_ori) / w_divider

    if y_d < 0:
        def _y_convert(y):
            return (y_d_abs - y + y_end) / h_divider
    else:
        def _y_convert(y):
            return (y - y_ori) / h_divider

    # define inner and return
    def converter(x, y):
        return int(_x_convert(x)), int(_y_convert(y))

    return converter


class TouchDeviceOccupied(Exception):
    pass


class TouchDriver:
    active_device = set()

    def __init__(self, display_type, touch_device: str):
        """Touch driver. Grabs events upon initializing, so make sure to delete
        instance before creating another on same device.

        Args:
            display_type: Display type specified in lcd_data.json
            touch_device: Touch device name - find it via `udevadm`.
        """

        # fail-fast, check if touch_device is already grabbed.
        if touch_device in self.active_device:
            raise TouchDeviceOccupied(f"Device {touch_device} is in use.")

        # If not mark device occupied. We'll lift it in __del__
        self.active_device.add(touch_device)
        self.device_name = touch_device

        self.display = display_type

        # touch area calibration
        self.dim, (origin, end) = LCD_DATA[display_type]
        self.converter = _raw_coord_to_pixel_closure(self.dim, origin, end)

        # start event manager
        self._listener = evdev.InputDevice("/dev/input/" + touch_device)
        self._listener.grab()

    def __del__(self):
        self._listener.ungrab()
        self.active_device.remove(self.device_name)

    def receive_touch(self) -> Union[Tuple[int, int], None]:
        """Get one touch event.
        Temporary measure until I re-implement evdev to support trio.
        Will only return last touch event.

        Returns:
            (x, y) or None if no input.
        """

        # need to read 2 EV_ABS for x & y, 1 EV_KEY for touch
        # EV_ABS = 3 / EV_KEY = 1
        # but for long touch there could be lots of axis flags

        # could make this much simpler with match-case clause..
        try:
            evs = list(self._listener.read())

            abs_xs = [ev for ev in evs if ev.type == EV_ABS and ev.code == ABS_X]
            abs_ys = [ev for ev in evs if ev.type == EV_ABS and ev.code == ABS_Y]
            release_ev = [
                ev for ev in evs
                if ev.type == EV_KEY and ev.code == BTN_TOUCH and ev.value == 0
            ]

            # make sure there's release event - we'll ignore down event might be missing.
            if not all((abs_xs, abs_ys, release_ev)):
                return None

            # if start_pos:
            return self.converter(abs_xs[-1].value, abs_ys[-1].value)

        except BlockingIOError:
            # Nothing to read in touch driver
            return None
