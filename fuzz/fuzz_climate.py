import json
import math
import sys
import types
from pathlib import Path

import atheris

ROOT = Path(__file__).resolve().parents[1]
package = types.ModuleType("inverter_climate")
package.__path__ = [str(ROOT / "src/inverter_climate")]
sys.modules[package.__name__] = package

with atheris.instrument_imports():
    from inverter_climate.models import Climate, InvalidObservation


def test_one_input(data: bytes) -> None:
    try:
        value = json.loads(data)
    except (ValueError, RecursionError):
        return
    if not isinstance(value, dict):
        return
    try:
        climate = Climate.parse(value, "climate.synthetic", "°C")
    except InvalidObservation:
        return
    assert -100 <= climate.min_c < climate.max_c <= 100  # nosec B101 - intentional test oracle
    assert math.isfinite(climate.current_c)  # nosec B101 - intentional test oracle
    assert 0 < climate.step_c <= 5  # nosec B101 - intentional test oracle
    if climate.can_set_temperature:
        try:
            aligned = climate.temperature_command(climate.min_c)
        except InvalidObservation:
            return
        assert math.isfinite(aligned)  # nosec B101 - intentional test oracle


if __name__ == "__main__":
    atheris.Setup(sys.argv, atheris.instrument_func(test_one_input))
    atheris.Fuzz()
