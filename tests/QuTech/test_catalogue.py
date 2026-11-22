import importlib
import json
from dataclasses import replace

import pytest
from qcodes.parameters import ManualParameter
from qcodes.validators import Enum

from qcodes_contrib_drivers.drivers.QuTech.catalogue import CATALOGUE, catalogue_json
from qcodes_contrib_drivers.drivers.QuTech.ivvi_module import IVVIModule

KINDS = {"drive", "sense", "current", "gate", "signal"}
# Every module on the qtwork IVVI module index that is not marked obsolete or
# SPI-only, plus M2q, which has its own driver here.
CURRENT_IVVI_MODULES = """S3b S1d S1h S1f S4c S4d S5a S5b S5c S5d S5e S5f S5g S5h S5j P1a S4m S4f SM1 S4e
M2m M2b M2d M2e M2c M2f M2g M2i M2k M2q M1b M1h M1g M1r M1c M3m M3a M3b M3c
VIa VIb VIc VId IVa IVb IVc IVd SM1a U1a U1b P2a P2b P2c P3 F1a F1b F1c F2a A1 A2 A3c A4 A6 R1 R2""".split()


def test_every_current_module_is_in_the_catalogue():
    assert sorted(set(CURRENT_IVVI_MODULES) - set(CATALOGUE)) == []
    assert sorted(set(CATALOGUE) - set(CURRENT_IVVI_MODULES)) == []


def driver_class(spec):
    module, cls = spec.driver.rsplit(".", 1)
    return getattr(importlib.import_module(module), cls)


@pytest.mark.parametrize("type_", sorted(CATALOGUE))
def test_entry_is_well_formed(type_):
    spec = CATALOGUE[type_]
    assert spec.type == type_
    assert spec.kind in {"source", "measure", "combined", "misc"}
    assert spec.slot_kind in {"source", "measure", "any"}
    assert spec.doc_url.startswith("https://qtwork.tudelft.nl/")
    assert len({p.id for p in spec.ports}) == len(spec.ports)
    assert all(p.kind in KINDS for p in spec.ports)
    assert set(spec.backplane) <= {p.id for p in spec.ports}
    for k in spec.knobs:
        assert k.values and k.initial in k.values, k.name


@pytest.mark.parametrize("type_", sorted(CATALOGUE))
def test_driver_builds_and_every_knob_takes_every_value(type_):
    spec = CATALOGUE[type_]
    inst = driver_class(spec)(f"t_{type_.lower()}")
    try:
        assert inst.get_idn()["model"] == type_
        for k in spec.knobs:
            param = inst.parameters[k.name]
            for v in k.values:
                param(v)
                assert param() == v
        snap = inst.snapshot()
        assert {k.name for k in spec.knobs} <= set(snap["parameters"])
    finally:
        inst.close()


@pytest.mark.parametrize(
    "type_",
    [
        type_
        for type_, spec in sorted(CATALOGUE.items())
        if not issubclass(driver_class(spec), IVVIModule)
    ],
)
def test_hand_written_drivers_match_catalogue(type_):
    """Check the catalogue against drivers that define their own settings."""
    spec = CATALOGUE[type_]
    inst = driver_class(spec)(f"m_{type_.lower()}")
    try:
        manual = {
            n: p
            for n, p in inst.parameters.items()
            if isinstance(p, ManualParameter) and n != "slot"
        }
        assert set(manual) == {k.name for k in spec.knobs}
        for k in spec.knobs:
            param = manual[k.name]
            assert param.cache.get() == k.initial, k.name
            assert param.label == k.label, k.name
            assert param.unit == k.unit, k.name
            vals = param.vals
            if isinstance(vals, Enum):
                assert set(vals.valid_values) == set(k.values), k.name
    finally:
        inst.close()


def test_json_round_trips():
    data = catalogue_json()
    assert json.loads(json.dumps(data)) == data
    assert data["S4c"]["ports"][0] == ["out+", "out +", "drive"]
    assert data["S4c"]["backplane"] == ["out+", "out-"]
    assert {name for name, entry in data.items() if not entry["ports_verified"]} == {
        "S5j", "IVb", "P2a", "P3", "F1a", "F1b"
    }


@pytest.mark.parametrize(
    ("type_", "ports"),
    [
        ("M2g", ()),
        ("S5h", ()),
        ("S5j", ()),
        ("S5a", ("out_q", "out_i", "outA", "outB")),
        ("P1a", ("out_v", "out_10u", "out_100n", "in")),
    ],
)
def test_backplane_overrides(type_, ports):
    assert CATALOGUE[type_].backplane == ports


def test_backplane_rejects_an_unknown_port():
    with pytest.raises(ValueError, match="unknown backplane ports"):
        replace(CATALOGUE["S4c"], backplane=("unknown",))


def test_s1h_has_a_driver():
    from qcodes_contrib_drivers.drivers.QuTech.S1h import S1h

    assert S1h.module_type == "S1h"
