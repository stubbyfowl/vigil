"""Optional C++ tracker. If it is not built, Vigil uses the Python tracker with identical results."""

import ctypes
import os
from pathlib import Path

import numpy as np

from ..config import Config
from ..signals import Signal
from .baseline import window_sizes

LIB_PATH = Path(__file__).parent / "_vigil_fast.so"
METHOD_CODE = {"z": 0, "ewma": 1, "cusum": 2, "vote": 3}
FIRED_NAMES = ((1, "z"), (2, "ewma"), (4, "cusum"))
_DOUBLE = ctypes.POINTER(ctypes.c_double)
_BYTE = ctypes.POINTER(ctypes.c_uint8)
_INT = ctypes.POINTER(ctypes.c_int32)


class _Params(ctypes.Structure):
    _fields_ = [
        *((name, ctypes.c_int32) for name in ("short_window", "reference_window", "needed", "persist", "release", "max_freeze", "method", "votes_needed")),
        *((name, ctypes.c_double) for name in ("sigma_floor", "sign", "z_limit", "ewma_lambda", "cusum_k", "cusum_h", "limit", "dead_zone", "evidence_cap")),
    ]


def _load() -> ctypes.CDLL | None:
    if os.environ.get("VIGIL_NO_NATIVE") or not LIB_PATH.exists():
        return None
    try:
        lib = ctypes.CDLL(str(LIB_PATH))
    except OSError:
        return None
    lib.vigil_track.restype = ctypes.c_int
    return lib


_lib = _load()


def available() -> bool:
    return _lib is not None


def track(sig: Signal, values: np.ndarray, cfg: Config, method: str, limit: float) -> dict[str, list]:
    """Run the C++ tracker over a whole series and return one list per output."""
    assert _lib is not None
    d, b, f = cfg["detector"], cfg["baseline"], cfg["fusion"]
    short, reference, needed = window_sizes(sig, cfg)
    persist, release = (d["persist_readings"], d["release_readings"]) if sig.cadence == 1 else (1, 1)
    params = _Params(
        short, reference, needed, persist, release, b["max_freeze_days"], METHOD_CODE[method], d["votes_needed"],
        b["sigma_floor"] * sig.noise, 1.0 if sig.bad == "up" else -1.0, d["z_limit"], d["ewma_lambda"], d["cusum_k"], d["cusum_h"],
        limit, f["dead_zone"], f["evidence_cap"],
    )
    n = len(values)
    input_values = np.asarray(values, dtype=np.float64)
    doubles = {name: np.empty(n, dtype=np.float64) for name in ("last_value", "median", "sigma", "short_median", "ewma", "evidence")}
    learning, flagged, fired = (np.empty(n, dtype=np.uint8) for _ in range(3))
    drift_days = np.empty(n, dtype=np.int32)
    _lib.vigil_track(
        input_values.ctypes.data_as(_DOUBLE), ctypes.c_int32(n), ctypes.byref(params),
        *(doubles[k].ctypes.data_as(_DOUBLE) for k in ("last_value", "median", "sigma", "short_median", "ewma", "evidence")),
        learning.ctypes.data_as(_BYTE), flagged.ctypes.data_as(_BYTE), fired.ctypes.data_as(_BYTE), drift_days.ctypes.data_as(_INT),
    )
    return {
        **{k: v.tolist() for k, v in doubles.items()}, "value": input_values.tolist(),
        "learning": [bool(x) for x in learning], "flagged": [bool(x) for x in flagged], "drift_days": drift_days.tolist(),
        "fired": [tuple(name for bit, name in FIRED_NAMES if int(x) & bit) for x in fired],
    }
