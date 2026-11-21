"""Module types, rack slots, front-panel ports and knob settings for the IVVI rack.

Other tools can read this catalogue without importing the drivers.
See https://qtwork.tudelft.nl/~schouten/ivvi/doc-mod/index-mod.htm.
"""

from dataclasses import asdict, dataclass
from typing import Literal

PortKind = Literal["drive", "sense", "current", "gate", "signal"]
SLOTS = {"source": ("Sa", "Sb", "Sc", "Sd"), "measure": ("Ma", "Mb")}
_PKG = "qcodes_contrib_drivers.drivers.QuTech"
_DOC = "https://qtwork.tudelft.nl/~schouten/ivvi/doc-mod/"


@dataclass(frozen=True)
class Knob:
    name: str
    label: str
    values: tuple[str | bool, ...]
    initial: str | bool
    unit: str = ""
    doc: str = ""


@dataclass(frozen=True)
class Port:
    id: str
    label: str
    kind: PortKind


@dataclass(frozen=True)
class ModuleSpec:
    type: str
    kind: Literal["source", "measure", "combined", "misc"]
    slot_kind: Literal["source", "measure", "any"]
    label: str
    ports: tuple[Port, ...]
    knobs: tuple[Knob, ...]
    doc_url: str
    driver: str
    extra_manual: tuple[str, ...] = ()  # Manual parameters without discrete settings.


def slots_for(slot_kind: str) -> tuple[str, ...]:
    return (
        SLOTS["source"] + SLOTS["measure"] if slot_kind == "any" else SLOTS[slot_kind]
    )


def catalogue_json() -> dict[str, dict]:
    """Return the catalogue with ports as triples and settings as JSON-safe lists."""
    out = {}
    for module_type, spec in CATALOGUE.items():
        entry = asdict(spec)
        entry["ports"] = [[port.id, port.label, port.kind] for port in spec.ports]
        entry["knobs"] = [
            {**asdict(knob), "values": list(knob.values)} for knob in spec.knobs
        ]
        entry["extra_manual"] = list(spec.extra_manual)
        del entry["type"]
        out[module_type] = entry
    return out


_DIFFERENTIAL_INPUT = (Port("in+", "in +", "sense"), Port("in-", "in -", "sense"))

CATALOGUE: dict[str, ModuleSpec] = {
    spec.type: spec
    for spec in [
        ModuleSpec(
            type="S4c",
            kind="source",
            slot_kind="source",
            label="Current and voltage source",
            ports=(Port("out+", "out +", "drive"), Port("out-", "out -", "drive")),
            knobs=(
                Knob(
                    "source_mode",
                    "Source Mode",
                    ("V", "I", "V+R"),
                    "V",
                    doc="Selects the source mode.",
                ),
                Knob(
                    "range",
                    "Range",
                    ("1n", "10n", "100n", "1u", "10u", "100u", "1m", "10m", "20m"),
                    "20m",
                    doc="Sets the output range.",
                ),
                Knob(
                    "R_out",
                    "Output Resistance",
                    ("R/1000", "R/100", "R/10", "10R", "100R", "1000R"),
                    "R/10",
                    doc="Sets the output resistance in V+R mode.",
                ),
                Knob(
                    "output_mode",
                    "Output Mode",
                    ("symm", "single"),
                    "symm",
                    doc="Selects symmetric or single-ended output.",
                ),
                Knob(
                    "x001_jumper",
                    "x0.01 jumper",
                    (False, True),
                    False,
                    doc="Records whether the x0.01 jumper is installed.",
                ),
            ),
            doc_url=f"{_DOC}docs4c.htm",
            driver=f"{_PKG}.S4c.S4c",
        ),
        ModuleSpec(
            type="M1b",
            kind="measure",
            slot_kind="measure",
            label="Current preamplifier",
            ports=(Port("in", "in", "current"),),
            knobs=(
                Knob(
                    "gain",
                    "Transimpedance gain",
                    ("1M", "10M", "100M", "1G"),
                    "1G",
                    "V/A",
                    "Sets the current-to-voltage gain.",
                ),
                Knob(
                    "postgain",
                    "Postgain",
                    ("x1", "x100ac", "x100dc"),
                    "x1",
                    doc="Selects unity gain or 100x gain with AC or DC coupling.",
                ),
                Knob(
                    "input_resistance_setting",
                    "Input resistance setting",
                    ("Low Rin", "Low Noise"),
                    "Low Noise",
                    doc="Selects low input resistance or low noise.",
                ),
                Knob(
                    "reference",
                    "Reference",
                    ("ground", "ref-in"),
                    "ground",
                    doc="Selects ground or the external reference input.",
                ),
                Knob(
                    "muted",
                    "Mute status",
                    (False, True),
                    False,
                    doc="Records whether the output is muted.",
                ),
            ),
            doc_url=f"{_DOC}docm1b.htm",
            driver=f"{_PKG}.M1b.M1b",
        ),
        ModuleSpec(
            type="M2b",
            kind="measure",
            slot_kind="measure",
            label="Differential voltage preamplifier",
            ports=_DIFFERENTIAL_INPUT,
            knobs=(
                Knob(
                    "gain",
                    "Gain",
                    ("100", "1k", "10k"),
                    "100",
                    "V/V",
                    "Sets the voltage gain.",
                ),
                Knob(
                    "dc_ac_mode",
                    "DC/AC mode",
                    ("dc", "ac"),
                    "ac",
                    doc="Selects DC or AC coupling.",
                ),
            ),
            doc_url=f"{_DOC}docm2b.htm",
            driver=f"{_PKG}.M2b.M2b",
        ),
        ModuleSpec(
            type="M2m",
            kind="measure",
            slot_kind="measure",
            label="Differential voltage preamplifier",
            ports=_DIFFERENTIAL_INPUT,
            knobs=(
                Knob(
                    "gain",
                    "Gain",
                    ("1", "10", "100", "1k", "10k"),
                    "1",
                    "V/V",
                    "Sets the voltage gain.",
                ),
                Knob(
                    "dc_ac_mode",
                    "DC/AC mode",
                    ("dc", "ac", "hpf"),
                    "ac",
                    doc="Selects DC or AC coupling, or the optional high-pass filter.",
                ),
            ),
            doc_url=f"{_DOC}docm2m.htm",
            driver=f"{_PKG}.M2m.M2m",
        ),
        ModuleSpec(
            type="M2q",
            kind="measure",
            slot_kind="measure",
            label="Differential voltage preamplifier",
            ports=_DIFFERENTIAL_INPUT,
            knobs=(
                Knob(
                    "gain",
                    "Gain",
                    ("100", "1k", "10k"),
                    "100",
                    "V/V",
                    "Sets the voltage gain.",
                ),
                Knob(
                    "dc_ac_mode",
                    "DC/AC mode",
                    ("dc", "ac"),
                    "ac",
                    doc="Selects DC or AC coupling.",
                ),
            ),
            doc_url=f"{_DOC}docm2q.htm",
            driver=f"{_PKG}.M2q.M2q",
        ),
        ModuleSpec(
            type="S1h",
            kind="source",
            slot_kind="source",
            label="High-voltage backgate source",
            ports=(Port("out", "out", "gate"), Port("imon", "I monitor", "signal")),
            knobs=(
                Knob(
                    "output_range",
                    "Output range",
                    ("30", "60", "90"),
                    "30",
                    "V",
                    "The ±30, ±60 and ±90 V ranges use gains of 15, 30 and 45 V/V.",
                ),
                Knob(
                    "output_swing",
                    "Output swing",
                    ("positive", "bipolar", "negative"),
                    "bipolar",
                    doc="Selects positive, bipolar or negative output swing.",
                ),
            ),
            doc_url=f"{_DOC}docs1h.htm",
            driver=f"{_PKG}.S1h.S1h",
        ),
        ModuleSpec(
            type="S3b",
            kind="source",
            slot_kind="source",
            label="Isolated voltage and current source",
            ports=(Port("out", "out", "drive"),),
            knobs=(
                Knob(
                    "output_mode",
                    "Output mode",
                    ("short", "100u", "1m", "10m", "100m", "100uA/V"),
                    "short",
                    doc="Selects the short, voltage-gain or current-output setting. Defaults to the first listed position.",
                ),
            ),
            doc_url=f"{_DOC}docs3b.htm",
            driver=f"{_PKG}.S3b.S3b",
        ),
        ModuleSpec(
            type="S1d",
            kind="source",
            slot_kind="source",
            label="Isolated voltage source",
            ports=(Port("out", "out", "drive"),),
            knobs=(
                Knob(
                    "gain",
                    "Gain",
                    ("1", "4"),
                    "1",
                    "V/V",
                    "Sets the voltage gain. Defaults to the first listed position.",
                ),
            ),
            doc_url=f"{_DOC}docs1d.htm",
            driver=f"{_PKG}.S1d.S1d",
        ),
        ModuleSpec(
            type="S1f",
            kind="source",
            slot_kind="source",
            label="Eight-channel gate amplifier",
            ports=(
                Port("in1", "in1", "signal"),
                Port("out1", "out1", "gate"),
                Port("in2", "in2", "signal"),
                Port("out2", "out2", "gate"),
                Port("in3", "in3", "signal"),
                Port("out3", "out3", "gate"),
                Port("in4", "in4", "signal"),
                Port("out4", "out4", "gate"),
                Port("in5", "in5", "signal"),
                Port("out5", "out5", "gate"),
                Port("in6", "in6", "signal"),
                Port("out6", "out6", "gate"),
                Port("in7", "in7", "signal"),
                Port("out7", "out7", "gate"),
                Port("in8", "in8", "signal"),
                Port("out8", "out8", "gate"),
            ),
            knobs=(
                Knob(
                    "battery_mode",
                    "Battery mode",
                    ("charge", "power"),
                    "charge",
                    doc="Selects charge or power on the first version. Later panels omit the switch. Defaults to the first listed position.",
                ),
            ),
            doc_url=f"{_DOC}docs1f.htm",
            driver=f"{_PKG}.S1f.S1f",
        ),
        ModuleSpec(
            type="S4d",
            kind="source",
            slot_kind="source",
            label="Dual current and voltage source",
            ports=(
                Port("outA", "out A", "drive"),
                Port("outB", "out B", "drive"),
            ),
            knobs=(
                Knob(
                    "range_a",
                    "Range A",
                    ("100n", "1u", "10u", "100u", "1m", "10m"),
                    "100n",
                    "A/V",
                    "Sets the source range. Defaults to the first listed position.",
                ),
                Knob(
                    "source_mode_a",
                    "Source mode A",
                    ("V", "V+R", "I"),
                    "V",
                    doc="Selects voltage, voltage with series resistance or current. Defaults to the first listed position.",
                ),
                Knob(
                    "range_b",
                    "Range B",
                    ("100n", "1u", "10u", "100u", "1m", "10m"),
                    "100n",
                    "A/V",
                    "Sets the source range. Defaults to the first listed position.",
                ),
                Knob(
                    "source_mode_b",
                    "Source mode B",
                    ("V", "V+R", "I"),
                    "V",
                    doc="Selects voltage, voltage with series resistance or current. Defaults to the first listed position.",
                ),
            ),
            doc_url=f"{_DOC}docs4d.htm",
            driver=f"{_PKG}.S4d.S4d",
        ),
        ModuleSpec(
            type="P1a",
            kind="source",
            slot_kind="source",
            label="Potentiometer and backplane adapter",
            ports=(
                Port("potm_v", "Potentiometer voltage", "drive"),
                Port("potm_10u", "Potentiometer x10u", "drive"),
                Port("potm_100n", "Potentiometer x100n", "drive"),
                Port("out_v", "Backplane voltage", "drive"),
                Port("out_10u", "Backplane x10u", "drive"),
                Port("out_100n", "Backplane x100n", "drive"),
                Port("in", "in", "signal"),
            ),
            knobs=(
                Knob(
                    "reference",
                    "Reference",
                    ("9Vbatt", "charge", "1Vref"),
                    "9Vbatt",
                    doc="Selects the labelled potentiometer reference or charge setting. Defaults to the first listed position.",
                ),
                Knob(
                    "output_swing",
                    "Output swing",
                    ("positive", "zero", "negative"),
                    "positive",
                    doc="Selects positive, zero or negative output. Defaults to the first listed position.",
                ),
            ),
            doc_url=f"{_DOC}docp1a.htm",
            driver=f"{_PKG}.P1a.P1a",
        ),
        ModuleSpec(
            type="S4m",
            kind="source",
            slot_kind="source",
            label="Current source",
            ports=(
                Port("out+", "out +", "drive"),
                Port("out-", "out -", "drive"),
            ),
            knobs=(
                Knob(
                    "range",
                    "Range",
                    ("1n", "10n", "100n", "1u", "10u", "100u", "1m", "10m", "20m"),
                    "1n",
                    "A/V",
                    "Sets the source range. Defaults to the first listed position.",
                ),
                Knob(
                    "muted",
                    "Mute",
                    (False, True),
                    False,
                    doc="Records whether the output is muted.",
                ),
                Knob(
                    "output_mode",
                    "Output mode",
                    ("symm", "single"),
                    "symm",
                    doc="Selects symmetric or single-ended output. Defaults to the first listed position.",
                ),
            ),
            doc_url=f"{_DOC}docs4m.htm",
            driver=f"{_PKG}.S4m.S4m",
        ),
        ModuleSpec(
            type="S4f",
            kind="source",
            slot_kind="source",
            label="Dual current source",
            ports=(
                Port("outA", "out A", "drive"),
                Port("outB", "out B", "drive"),
            ),
            knobs=(
                Knob(
                    "range_a",
                    "Range A",
                    ("1u", "10u", "100u", "1m", "10m", "20m"),
                    "1u",
                    "A/V",
                    "Sets the source range. Defaults to the first listed position.",
                ),
                Knob(
                    "output_mode_a",
                    "Output mode A",
                    ("symm", "single"),
                    "symm",
                    doc="Selects symmetric or single-ended output. Defaults to the first listed position.",
                ),
                Knob(
                    "range_b",
                    "Range B",
                    ("1u", "10u", "100u", "1m", "10m", "20m"),
                    "1u",
                    "A/V",
                    "Sets the source range. Defaults to the first listed position.",
                ),
                Knob(
                    "output_mode_b",
                    "Output mode B",
                    ("symm", "single"),
                    "symm",
                    doc="Selects symmetric or single-ended output. Defaults to the first listed position.",
                ),
            ),
            doc_url=f"{_DOC}docs4f.htm",
            driver=f"{_PKG}.S4f.S4f",
        ),
        ModuleSpec(
            type="SM1",
            kind="source",
            slot_kind="source",
            label="Current source and isolated voltage readout",
            ports=(
                Port("out", "out", "drive"),
                Port("gnd", "Source ground", "signal"),
                Port("in+", "in +", "sense"),
                Port("in-", "in -", "sense"),
                Port("iso_out", "ISO out", "signal"),
            ),
            knobs=(
                Knob(
                    "range",
                    "Range",
                    ("1", "10", "100"),
                    "1",
                    "µA/V",
                    "Sets the current source range. Defaults to the first listed position.",
                ),
                Knob(
                    "gain",
                    "Gain",
                    ("10", "100", "1k"),
                    "10",
                    "V/V",
                    "Sets the voltage gain. Defaults to the first listed position.",
                ),
            ),
            doc_url=f"{_DOC}docsm1.htm",
            driver=f"{_PKG}.SM1.SM1",
        ),
        ModuleSpec(
            type="S4e",
            kind="source",
            slot_kind="source",
            label="Ultralow-noise voltage and current source",
            ports=(Port("out", "out", "drive"),),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}docs4e.htm",
            driver=f"{_PKG}.S4e.S4e",
        ),
    ]
}
