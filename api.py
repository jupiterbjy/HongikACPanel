"""
Experimental AC control code
Some a bit of improved code to discard need of Selenium and chrome/firefox driver

Python 3.8
jupiterbjy@gmail.com

References:
https://www.python-httpx.org/quickstart/
https://developer.mozilla.org/docs/Learn/Forms/Sending_and_retrieving_form_data
"""

import re
import functools
import argparse
from random import randint
from typing import Dict, Any, Union

import trio
import httpx

from bs4 import BeautifulSoup as bs

from loguru import logger


# AC mode translation list
OPERATION_MODE = ["Heating", "Cooling", "Fan only"]
WIND_SPEED_MODE = ["Auto", "Max", "medium", "low"]
WIND_DIRECTION_MODE = ["Swing", "Horizontal", "Vertical"]


class ACTempOutOfBound(Exception):
    pass


class ACRequestFailed(Exception):
    pass


# TODO: find way to determine if we're still logged in or not
class NotLoggedIn(Exception):
    pass


# TODO: Check if we need target temp here
class ACState:
    """
    Simplified web remote status representation from Parsed HTML.
    """

    """
    <MEMO>
    Guessed from html source & images

    <ip>/images/nn_0.gif = Heating
    <ip>/images/nn_1.gif = Cooling
    <ip>/images/nn_2.gif = Fan only
    Used with ID:
        Image_1 -> Showing current AC mode


    <ip>/images/Tem_xx.gif = Temp. XX being celcius displayed on image
    Used with ID:
        Image_2 -> current indoor temp
        Image_3 -> current target temp


    <ip>/images/mm_0.gif = Wind speed auto
    <ip>/images/mm_1.gif = Wind speed max
    <ip>/images/mm_2.gif = Wind speed medium
    <ip>/images/mm_3.gif = Wind speed low
    Used with ID:
        Image_4 -> current wind speed setting


    <ip>/images/kk_0.gif = Wind direction Swinging
    <ip>/images/kk_1.gif = Wind direction Horizontal
    <ip>/images/kk_2.gif = Wind direction Vertical
    Used with ID:
        Image_5 -> current wind direction setting
    """

    # Not sure if we need regex...but whatever
    # regex to find ID in temp image's name

    pattern = re.compile(r"\d+")

    def __init__(self, resp: httpx.Response):
        self.soup = bs(resp.content.decode(), "html.parser")

    def _pattern_match(self, src: str) -> int:
        return int(self.pattern.search(src)[0])

    @functools.cached_property
    def states(self) -> Dict[str, str]:
        """
        Gets __VIEWSTATE, __VIEWSTATEGENERATOR, __EVENTVALIDATION
        values from soup.
        """

        return {
            id_: self.soup.find("input", {"id": id_}).attrs["value"]
            for id_ in ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION")
        }

    @functools.cached_property
    def operation_mode(self) -> str:
        """Determines operation mode"""

        img_src = self.soup.find("img", {"id": "Image_1"})["src"]
        return OPERATION_MODE[self._pattern_match(img_src)]

    @functools.cached_property
    def current_temp(self) -> int:
        """Gets current temperature."""

        img_src = self.soup.find("img", {"id": "Image_2"})["src"]
        return self._pattern_match(img_src)

    @functools.cached_property
    def target_temp(self) -> int:
        """Gets target temperature."""

        img_src = self.soup.find("img", {"id": "Image_3"})["src"]
        return self._pattern_match(img_src)

    @functools.cached_property
    def wind_speed(self) -> str:
        """Determines wind speed mode"""

        img_src = self.soup.find("img", {"id": "Image_4"})["src"]
        return WIND_SPEED_MODE[self._pattern_match(img_src)]

    @functools.cached_property
    def wind_angle(self) -> str:
        """Determines wind angle mode"""

        img_src = self.soup.find("img", {"id": "Image_5"})["src"]
        return WIND_DIRECTION_MODE[self._pattern_match(img_src)]

    # TODO: add permission checks


class ACManager:
    """
    AC controller class.
    """

    # TODO: validate effect of hdrNo12 & 13 and update temp_up & temp_down.
    """
    <MEMO>
    Guessed from html source & images

    hdnNo list:
    1 = 0: off, 1: on
    2 = 25 | Minimum?
    3 = 1 0: Unknown, 1: Cooling mode, 2: Unknown
    4 = Target temp
    5 = 0
    6 = 0: On/Off perm, 2: Off perm, else: No perm -> to hdnNo_1
    7 = 0
    8 = 1 | 0: Mode change perm, else: No perm (No UI control avail.) -> to hdnNo_8

    10 = 2 | 0: Wind Speed Auto, 1: High, 2: Mid, 3: Low
    11 = 1 | 0: Wind Angle Swing, 1: Horizontal, 2: Vertical
    12 = 29 AC upper temp lim, must be < 29
    13 = 25 AC lower temp lim, must be >= 25
    14 = 1
    15 = 1
    16 = 1
    17 = 1
    18 = 1

    whichbtn = 0 Unused?

                  AC On | AC Off | T down | T up | None |
    btnSubmit.x = 94    | 108    | 95     | 41   | 55
    btnSubmit.y = 40    | 40     | 35     | 37   | 16
    """

    btn_action = {
        "on": (94, 40),
        "off": (108, 40),
        "temp_down": (95, 35),
        "temp_up": (41, 37),
        "other": (55, 16),
    }

    # TODO: move base_state and associated to ACState
    base_state = {
        "hdnNo_1": 0,
        "hdnNo_2": 25,
        "hdnNo_3": 1,
        "hdnNo_4": 26,
        "hdnNo_5": 0,
        "hdnNo_6": 0,
        "hdnNo_7": 0,
        "hdnNo_8": 1,
        "hdnNo_10": 2,
        "hdnNo_11": 1,
        "hdnNo_12": 29,
        "hdnNo_13": 25,
        "hdnNo_14": 1,
        "hdnNo_15": 1,
        "hdnNo_16": 1,
        "hdnNo_17": 1,
        "hdnNo_18": 1,

        "whichbtn": 0,
        "btnSubmit.x": 55,
        "btnSubmit.y": 16,
    }

    def __init__(self, ip: str, id_: str, password: str, temp=26, angle=0, speed=0):
        self.client = httpx.AsyncClient()

        self._url = f"http://{ip}/"
        self._url_remote = self._url + "webremo"

        self._id = id_
        self._pw = password

        self.angle = angle
        self.speed = speed
        self.target_temp = temp

        # overrides class's
        self.base_state = {k: v for k, v in self.base_state.items()}
        self.base_state["hdnNo_4"] = temp
        self.base_state["hdnNo_10"] = speed
        self.base_state["hdnNo_11"] = angle

        # AC states to keep track of
        self.state: Union[ACState, None] = None

        self.is_powered = False
        self.action = "other"

    @functools.cached_property
    def upper_bound(self) -> int:
        """Upper temp boundary"""

        return self.base_state["hdnNo_12"]

    @functools.cached_property
    def lower_bound(self) -> int:
        """Lower temp boundary"""

        return self.base_state["hdnNo_13"]

    @property
    def payload(self) -> Dict[str, Any]:
        """Creates payload."""

        payload = {k: v for k, v in self.base_state.items()}
        payload["hdnNo_4"] = self.target_temp
        payload["hdnNo_1"] = 1 if self.is_powered else 0

        payload["btnSubmit.x"], payload["btnSubmit.y"] = self.btn_action[self.action]
        payload.update(self.state.states)

        return payload

    async def login(self):
        """
        Performs login and follow into web remote controller site.

        Note:
            There's no login failure tolerance. I'm lazy.
        """

        # initial update
        if self.state is None:
            resp = await self.client.get(self._url, follow_redirects=True)
            self.state = ACState(resp)

        payloads = self.state.states

        # adding login data
        payloads["txtId"] = self._id
        payloads["txtPwd"] = self._pw

        # proceed login & update state
        resp = await self.client.post(self._url, data=payloads, follow_redirects=True)

        resp.raise_for_status()
        logger.info(f"Login successful")

        await self.update(resp)

    async def update(self, resp: httpx.Response = None) -> ACState:
        """Manually trigger update & returns state."""

        if resp is None:
            resp = await self.client.get(self._url, follow_redirects=True)

        self.state = ACState(resp)
        self.target_temp = self.state.target_temp

        logger.info(f"Cur. Temp      : {self.state.current_temp}")
        logger.info(f"Cur. Operation : {self.state.operation_mode}")
        logger.info(f"Cur. Wind speed: {self.state.wind_speed}")
        logger.info(f"Cur. Wind angle: {self.state.wind_angle}")

        return self.state

    async def keep_alive_state(self, interval_sec=60, deviation_max_sec=30):
        """Keep state up-to-date"""

        logger.debug("Keepalive State started")

        while True:
            await trio.sleep(interval_sec + randint(0, deviation_max_sec))
            await self.update()

    async def keep_alive_power(self, interval_sec=1200, deviation_max_sec=60):
        """
        Re-login and send commands again with given interval.
        Randomly adds up to deviation_max_sec to total waiting time.

        Expects keep_alive_state to be run alongside.
        """

        logger.debug("Keepalive Power started")

        while True:
            sleep_duration = interval_sec + randint(0, deviation_max_sec)
            logger.debug(f"Sleeping for {sleep_duration}")

            await trio.sleep(sleep_duration)

            await self.login()
            await trio.sleep(5)
            await self._send()

    async def get_temp(self):
        """Run update and get new current temp."""

        await self.update()
        return self.state.current_temp

    async def power_on(self):
        """Power On AC.

        Raises:
            ACRequestFailed: If request was failed
        """

        self.action = "on"
        self.is_powered = True
        await self._send()

    async def power_off(self):
        """Power Off AC.

        Raises:
            ACRequestFailed: If request was failed
        """

        self.action = "off"
        self.is_powered = False
        await self._send()

    async def set_temp(self, temp: int):
        """Set specific temp.

        Args:
            temp: Target Temperature

        Raises:
            ACTempOutOfBound: If set temperature is out of bound
            ACRequestFailed: If request was failed
        """

        if not(self.lower_bound <= temp < self.upper_bound):
            raise ACTempOutOfBound()

        self.target_temp = temp
        await self._send()

    async def temp_down(self):
        """Lower temp by 1.

        Raises:
            ACTempOutOfBound: If set temperature is out of bound
            ACRequestFailed: If request was failed
        """

        if (self.target_temp - 1) <= self.lower_bound:
            raise ACTempOutOfBound()

        self.target_temp -= 1
        await self._send()

    async def temp_up(self):
        """Higher temp by 1.

        Raises:
            ACTempOutOfBound: If set temperature is out of bound
            ACRequestFailed: If request was failed
        """

        if self.target_temp >= self.upper_bound:
            raise ACTempOutOfBound()

        self.target_temp += 1
        await self._send()

    async def _send(self):
        """Sends request.

        Raises:
            ACRequestFailed: If request operation fails
        """

        # TODO: add & raise custom errors (i.e. permission, out of temp range, etc)
        # TODO: Check all possible exceptions from Univ's AC web remote server

        logger.info("Sending request!")
        logger.debug(f"Power {self.is_powered} / TGT Temp {self.target_temp}")

        resp = await self.client.post(self._url_remote, data=self.payload, follow_redirects=True)

        try:
            resp.raise_for_status()

        except Exception as err:
            logger.warning(f"{type(err).__name__} - {err}")
            logger.debug(f"Received response:\n{resp.content.decode()}\n")
            raise ACRequestFailed() from err

        finally:
            # reset action
            self.action = "other"


async def main(args_):
    logger.info("Note: This script will automatically stop AC when shutting down by SIGINT")

    ac = ACManager(args_.ip, args_.id, args_.pwd, args_.temp, args_.wind_angle, args_.wind_speed)

    await ac.login()
    await ac.power_on()
    await ac.set_temp(args_.temp)

    async with trio.open_nursery() as nursery:
        nursery.start_soon(ac.keep_alive_power)
        nursery.start_soon(ac.keep_alive_state)

    await ac.power_off()
    logger.info("Shutting down!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser("CLI AC keepalive")
    parser.add_argument(
        "ip",
        type=str,
        help="Web remote IP"
    )
    parser.add_argument(
        "-t",
        "--temp",
        type=int,
        default=26,
        help="Target temp (25 ~ 28)"
    )

    # WIND_DIRECTION_MODE = ["Swing", "Horizontal", "Vertical"]
    parser.add_argument(
        "-a",
        "--wind-angle",
        type=int,
        default=0,
        help="Target Wind Angle (0 Swing / 1 Horizontal / 2 Vertical)"
    )

    # WIND_SPEED_MODE = ["Auto", "Max", "medium", "low"]
    parser.add_argument(
        "-s",
        "--wind-speed",
        type=int,
        default=0,
        help="Target Wind Speed (0 Auto / 1 High / 2 Mid / 3 Low)"
    )

    parser.add_argument(
        "-i",
        "--id",
        type=str,
        required=True,
        help="Login ID"
    )
    parser.add_argument(
        "-p",
        "--pwd",
        type=str,
        required=True,
        help="Login PW"
    )

    args = parser.parse_args()

    trio.run(main, args)
