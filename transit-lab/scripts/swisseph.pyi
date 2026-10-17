"""Type stubs for swisseph (Swiss Ephemeris C extension)."""
from typing import Any, Tuple

GREG_CAL: int
JUL_CAL: int

SIDM_LAHIRI: int
SIDM_FAGAN_BRADLEY: int
SIDM_KRISHNAMURTI: int
SIDM_RAMAN: int

FLG_SWIEPH: int
FLG_MOSEPH: int
FLG_SPEED: int
FLG_SIDEREAL: int
FLG_TROPICAL: int

SUN: int
MOON: int
MERCURY: int
VENUS: int
MARS: int
JUPITER: int
SATURN: int
MEAN_NODE: int
TRUE_NODE: int

class Error(Exception): ...

def julday(year: int, month: int, day: int, hour: float = ..., gregflag: int = ...) -> float: ...
def set_sid_mode(sid_mode: int, t0: float = ..., ayan_t0: float = ...) -> None: ...
def get_ayanamsa_ut(tjd_ut: float) -> float: ...
def calc_ut(tjd_ut: float, ipl: int, iflag: int = ...) -> Tuple[Tuple[float, float, float, float, float, float], int]: ...
def houses_ex(tjd_ut: float, geolat: float, geolon: float, hsys: bytes = ..., iflag: int = ...) -> Tuple[Tuple[float, ...], Tuple[float, ...]]: ...
