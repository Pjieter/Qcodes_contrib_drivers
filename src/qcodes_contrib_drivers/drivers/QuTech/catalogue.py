"""Module types, rack slots, front-panel ports and knob settings for the IVVI rack.

Other tools can read this catalogue without importing the drivers.
Entries with missing module pages infer their ports from the module index,
as marked in the comments.
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
    """A discrete front-panel setting and its allowed values."""

    name: str
    label: str
    values: tuple[str | bool, ...]
    initial: str | bool
    unit: str = ""
    doc: str = ""


@dataclass(frozen=True)
class Port:
    """A front-panel connector and its wiring role."""

    id: str
    label: str
    kind: PortKind


@dataclass(frozen=True)
class ModuleSpec:
    """Catalogue metadata for a virtual IVVI module."""

    type: str
    kind: Literal["source", "measure", "combined", "misc"]
    slot_kind: Literal["source", "measure", "any"]
    label: str
    ports: tuple[Port, ...]
    knobs: tuple[Knob, ...]
    doc_url: str
    driver: str


def slots_for(slot_kind: str) -> tuple[str, ...]:
    """Return the rack slots that accept this slot kind."""
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
        del entry["type"]
        out[module_type] = entry
    return out


_DIFFERENTIAL_INPUT = (Port("in+", "in +", "sense"), Port("in-", "in -", "sense"))

# Front-panel connectors shared by the VI modules.
_VI_PORTS = (
    Port("out+", "out +", "drive"),
    Port("out-", "out -", "drive"),
    Port("in", "in", "current"),
    Port("ref", "Ground/reference in", "signal"),
    Port("iso_out", "ISO out", "signal"),
)

# Front-panel connectors shared by the IV modules.
_IV_PORTS = (
    Port("out+", "out +", "drive"),
    Port("out-", "out -", "drive"),
    Port("in+", "in +", "sense"),
    Port("in-", "in -", "sense"),
    Port("iso_out", "ISO out", "signal"),
)

# Gain and mode settings shared by the VI modules.
_VI_INPUT_MODE = Knob(
    "input_mode",
    "Current input mode",
    ("x100ac Low Noise", "x1 Low Rin", "x1 Low Noise"),
    "x100ac Low Noise",
    doc="Selects the combined postgain and input resistance setting. Defaults to the first listed position.",
)
_VI_KNOBS = (
    Knob(
        "source_gain",
        "Source gain",
        ("1m", "10m", "100m"),
        "1m",
        "V/V",
        "Sets the voltage source gain. Defaults to the first listed position.",
    ),
    Knob(
        "gain",
        "Transimpedance gain",
        ("1M", "10M", "100M", "1G"),
        "1M",
        "V/A",
        "Sets the current-to-voltage gain. Defaults to the first listed position.",
    ),
    _VI_INPUT_MODE,
)

# Event selection for the M3 critical-current detectors.
_M3_MODE = Knob(
    "mode",
    "Mode",
    ("switch+", "retrap+", "switch-", "retrap-"),
    "switch+",
    doc="Selects positive or negative switching or retrapping events. Defaults to the first listed position.",
)

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
                    doc="Records whether the output is muted. Defaults to not muted.",
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
            ports=(Port("out+", "out +", "drive"), Port("out-", "out −", "drive")),
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
            ports=(Port("out+", "out +", "drive"), Port("out-", "out −", "drive")),
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
                    doc="First version only. Newer units have no such switch.",
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
            # Follows the prototype photo. The page also names an R-out switch
            # and a 1 nA range that the photo does not show.
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
                    doc="Records whether the output is muted. Defaults to not muted.",
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
                    ("1u", "10u", "100u"),
                    "1u",
                    "A/V",
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
            knobs=(),  # page names decade switches but shows no positions (photo 404)
            doc_url=f"{_DOC}docs4e.htm",
            driver=f"{_PKG}.S4e.S4e",
        ),
        ModuleSpec(
            type="S5a",
            kind="source",
            slot_kind="source",
            label="Six-level pulse generator",
            ports=(
                Port("out_q", "Q out", "drive"),
                Port("out_i", "I out", "drive"),
                Port("outA", "Amplitude out A", "drive"),
                Port("outB", "Amplitude out B", "drive"),
                Port("trigger_in", "Electrical trigger in", "signal"),
                Port("fibre_in", "Fibre trigger in", "signal"),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}docs5a.htm",
            driver=f"{_PKG}.S5a.S5a",
        ),
        ModuleSpec(
            type="S5b",
            kind="source",
            slot_kind="source",
            label="Dual fibre pulse receiver",
            ports=(
                Port("outA", "out A", "drive"),
                Port("outB", "out B", "drive"),
                Port("fibre_in_a", "Ch 1 fibre in", "signal"),
                Port("fibre_in_b", "Ch 2 fibre in", "signal"),
                Port("offset_in_a", "Ch 1 offset in", "signal"),
                Port("offset_in_b", "Ch 2 offset in", "signal"),
            ),
            knobs=(
                Knob(
                    "offset_control",
                    "Offset control",
                    ("ch1", "ch1+ch2", "off"),
                    "ch1",
                    doc="Selects the channels that use front-panel offset control. Defaults to the first listed position.",
                ),
            ),
            doc_url=f"{_DOC}docs5b.htm",
            driver=f"{_PKG}.S5b.S5b",
        ),
        ModuleSpec(
            type="S5c",
            kind="source",
            slot_kind="source",
            label="Four-level write-read pulser",
            ports=(
                Port("out", "out", "drive"),
                Port("fibre_in", "Fibre in", "signal"),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}docs5c.htm",
            driver=f"{_PKG}.S5c.S5c",
        ),
        ModuleSpec(
            type="S5d",
            kind="source",
            slot_kind="source",
            label="Fast two-level pulser",
            ports=(
                Port("out", "out", "drive"),
                Port("fibre_in", "Fibre in", "signal"),
                Port("l0", "L0 control", "signal"),
                Port("l1", "L1 control", "signal"),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}docs5d.htm",
            driver=f"{_PKG}.S5d.S5d",
        ),
        ModuleSpec(
            type="S5e",
            kind="source",
            slot_kind="source",
            label="Precision eight-level pulser",
            ports=(
                Port("out+", "out +", "drive"),
                Port("out-", "out -", "drive"),
                Port("fibre_in", "Fibre clock/reset", "signal"),
                Port("l0", "L0 DAC in", "signal"),
                Port("l1", "L1 DAC in", "signal"),
                Port("l2", "L2 DAC in", "signal"),
                Port("l3", "L3 DAC in", "signal"),
                Port("l4", "L4 DAC in", "signal"),
                Port("l5", "L5 DAC in", "signal"),
                Port("l6", "L6 DAC in", "signal"),
                Port("l7", "L7 DAC in", "signal"),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}docs5e.htm",
            driver=f"{_PKG}.S5e.S5e",
        ),
        ModuleSpec(
            type="S5f",
            kind="source",
            slot_kind="source",
            label="Trigger splitter and isolator",
            ports=(
                Port("trigger_in", "Electrical trigger in", "signal"),
                Port("fibre_in", "Fibre trigger in", "signal"),
                Port("out1", "Trigger out 1", "signal"),
                Port("out2", "Trigger out 2", "signal"),
                Port("out3", "Trigger out 3", "signal"),
                Port("out4", "Trigger out 4", "signal"),
                Port("out5", "Trigger out 5", "signal"),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}docs5f.htm",
            driver=f"{_PKG}.S5f.S5f",
        ),
        ModuleSpec(
            type="S5g",
            kind="source",
            slot_kind="source",
            label="Fibre-isolated high-frequency source",
            ports=(
                Port("out", "out", "drive"),
                Port("fibre_in", "Fibre in", "signal"),
                Port("dc", "DC control", "signal"),
                Port("vh", "High limit control", "signal"),
                Port("vl", "Low limit control", "signal"),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}docs5g.htm",
            driver=f"{_PKG}.S5g.S5g",
        ),
        ModuleSpec(
            type="S5h",
            kind="source",
            slot_kind="source",
            label="High-frequency clamping amplifier",
            ports=(
                Port("in", "in", "signal"),
                Port("out", "out", "drive"),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}docs5h.htm",
            driver=f"{_PKG}.S5h.S5h",
        ),
        ModuleSpec(
            type="S5j",
            kind="source",
            slot_kind="source",
            label="RF modulator",
            ports=(  # ports inferred from the index row, unverified
                Port("in", "in", "signal"),
                Port("out", "out", "drive"),
                Port("control", "Analog modulation control", "signal"),
            ),
            knobs=(),  # page not found
            doc_url=f"{_DOC}index-mod.htm",  # its own page docs5j.htm is not found
            driver=f"{_PKG}.S5j.S5j",
        ),
        ModuleSpec(
            type="M2d",
            kind="measure",
            slot_kind="measure",
            label="Low-noise differential voltage preamplifier",
            ports=_DIFFERENTIAL_INPUT,
            knobs=(
                Knob(
                    "gain",
                    "AC gain",
                    ("100", "1k", "10k", "100k"),
                    "100",
                    "V/V",
                    "Sets the AC gain. DC gain stays at 100 V/V. Defaults to the first listed position.",
                ),
            ),
            doc_url=f"{_DOC}docm2d.htm",
            driver=f"{_PKG}.M2d.M2d",
        ),
        ModuleSpec(
            type="M2e",
            kind="measure",
            slot_kind="measure",
            label="Voltage preamplifier with zoom and comparator",
            ports=(
                *_DIFFERENTIAL_INPUT,
                Port("opto_out", "Optical out", "signal"),
            ),
            knobs=(
                Knob(
                    "gain",
                    "Gain",
                    ("1", "10", "100", "1k", "10k"),
                    "1",
                    "V/V",
                    "Sets the voltage gain. Defaults to the first listed position.",
                ),
                Knob(
                    "mode",
                    "Mode",
                    ("compare", "amp", "zoom"),
                    "compare",
                    doc="Selects comparison, amplification or 10x zoom. Defaults to the first listed position.",
                ),
            ),
            doc_url=f"{_DOC}docm2e.htm",
            driver=f"{_PKG}.M2e.M2e",
        ),
        ModuleSpec(
            type="M2c",
            kind="measure",
            slot_kind="measure",
            label="High-impedance differential voltage preamplifier",
            ports=(
                *_DIFFERENTIAL_INPUT,
                Port("guard+", "Guard +", "signal"),
                Port("guard-", "Guard -", "signal"),
            ),
            knobs=(
                Knob(
                    "gain",
                    "Gain",
                    ("1", "10", "100"),
                    "1",
                    "V/V",
                    "Sets the voltage gain. Defaults to the first listed position.",
                ),
            ),
            doc_url=f"{_DOC}docm2c.htm",
            driver=f"{_PKG}.M2c.M2c",
        ),
        ModuleSpec(
            type="M2f",
            kind="measure",
            slot_kind="measure",
            label="Fast single-ended voltage preamplifier",
            ports=(
                Port("in", "in", "sense"),
                Port("fibre_out", "Fibre out", "signal"),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}docm2f.htm",
            driver=f"{_PKG}.M2f.M2f",
        ),
        ModuleSpec(
            type="M2g",
            kind="measure",
            slot_kind="measure",
            label="Fibre-isolated voltage postamplifier",
            ports=(
                Port("in", "in", "sense"),
                Port("fibre_out", "Fibre out", "signal"),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}docm2g.htm",
            driver=f"{_PKG}.M2g.M2g",
        ),
        ModuleSpec(
            type="M2i",
            kind="measure",
            slot_kind="measure",
            label="Low-noise differential voltage preamplifier",
            ports=_DIFFERENTIAL_INPUT,
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}docm2i.htm",
            driver=f"{_PKG}.M2i.M2i",
        ),
        ModuleSpec(
            type="M2k",
            kind="measure",
            slot_kind="measure",
            label="Dual AWG buffer",
            ports=(
                Port("inA+", "In A +", "signal"),
                Port("inA-", "In A -", "signal"),
                Port("inB+", "In B +", "signal"),
                Port("inB-", "In B -", "signal"),
                Port("outA", "Out A", "signal"),
                Port("outB", "Out B", "signal"),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}docm2k.htm",
            driver=f"{_PKG}.M2k.M2k",
        ),
        ModuleSpec(
            type="M1h",
            kind="measure",
            slot_kind="measure",
            label="Fast current preamplifier",
            ports=(
                Port("in", "in", "current"),
                Port("ref", "Reference in", "signal"),
            ),
            knobs=(
                Knob(
                    "gain",
                    "Transimpedance gain",
                    ("1M", "10M", "100M", "1G"),
                    "1M",
                    "V/A",
                    "Sets the current-to-voltage gain. Defaults to the first listed position.",
                ),
                Knob(
                    "postgain",
                    "Postgain",
                    ("x100ac", "x1", "x100dc"),
                    "x100ac",
                    doc="Selects AC-only 100x, unity or DC-coupled 100x postgain. Defaults to the first listed position.",
                ),
                Knob(
                    "input_resistance_setting",
                    "Input resistance setting",
                    ("Low Rin", "Low Noise"),
                    "Low Rin",
                    doc="Selects low input resistance or low noise. Defaults to the first listed position.",
                ),
                Knob(
                    "muted",
                    "Mute",
                    (False, True),
                    False,
                    doc="Records whether the output is muted. Defaults to not muted.",
                ),
            ),
            doc_url=f"{_DOC}docm1h.htm",
            driver=f"{_PKG}.M1h.M1h",
        ),
        ModuleSpec(
            type="M1g",
            kind="measure",
            slot_kind="measure",
            label="50 kHz current preamplifier",
            ports=(
                Port("in", "in", "current"),
                Port("ref", "Reference in", "signal"),
            ),
            knobs=(
                Knob(
                    "postgain",
                    "Postgain",
                    ("x10ac", "x1", "x10dc"),
                    "x10ac",
                    doc="Selects AC-only 10x, unity or DC-coupled 10x postgain. Defaults to the first listed position.",
                ),
            ),
            doc_url=f"{_DOC}docm1g.htm",
            driver=f"{_PKG}.M1g.M1g",
        ),
        ModuleSpec(
            type="M1r",
            kind="measure",
            slot_kind="measure",
            label="Remote current converter interface",
            ports=(
                Port("converter", "I/V converter interface", "signal"),
                Port("bias_in", "V-bias in", "signal"),
            ),
            knobs=(
                Knob(
                    "postgain",
                    "Postgain",
                    ("x1", "x10", "x100"),
                    "x1",
                    "V/V",
                    "Sets the postamplifier gain. Defaults to the first listed position.",
                ),
                Knob(
                    "postgain_coupling",
                    "Postgain coupling",
                    ("dc", "ac"),
                    "dc",
                    doc="Selects DC or AC coupling for the postamplifier. Defaults to the first listed position.",
                ),
            ),
            doc_url=f"{_DOC}docm1r.htm",
            driver=f"{_PKG}.M1r.M1r",
        ),
        ModuleSpec(
            type="M1c",
            kind="measure",
            slot_kind="measure",
            label="Cryogenic preamplifier interface",
            ports=(
                Port("preamp", "Cryogenic preamplifier coax", "signal"),
                Port("dc_bias", "DC bias", "signal"),
                Port("dc_monitor", "DC monitor", "signal"),
                Port("fibre_out", "Analogue fibre out", "signal"),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}docm1c.htm",
            driver=f"{_PKG}.M1c.M1c",
        ),
        ModuleSpec(
            type="M3m",
            kind="measure",
            slot_kind="measure",
            label="Critical-current detector",
            ports=(Port("fibre_out", "Trigger fibre out", "signal"),),
            knobs=(
                _M3_MODE,
                Knob(
                    "reference",
                    "Reference",
                    ("int", "ext"),
                    "int",
                    doc="Selects the internal threshold or an external threshold through the rack. Defaults to the first listed position.",
                ),
            ),
            doc_url=f"{_DOC}docm3m.htm",
            driver=f"{_PKG}.M3m.M3m",
        ),
        ModuleSpec(
            type="M3a",
            kind="measure",
            slot_kind="measure",
            label="Critical-current detector with isolated readout",
            ports=(
                Port("iso_out", "ISO out", "signal"),
                Port("fibre_out", "Trigger fibre out", "signal"),
            ),
            knobs=(_M3_MODE,),
            doc_url=f"{_DOC}docm3a.htm",
            driver=f"{_PKG}.M3a.M3a",
        ),
        ModuleSpec(
            type="M3c",
            kind="measure",
            slot_kind="measure",
            label="Critical-current detector with M0b isolated readout",
            ports=(
                Port("iso_out", "ISO out", "signal"),
                Port("fibre_out", "Trigger fibre out", "signal"),
            ),
            knobs=(_M3_MODE,),
            doc_url=f"{_DOC}docm3c.htm",
            driver=f"{_PKG}.M3c.M3c",
        ),
        ModuleSpec(
            type="M3b",
            kind="misc",
            slot_kind="any",
            label="PID feedback controller",
            ports=(
                Port("set", "Set", "signal"),
                Port("measure", "Measure", "signal"),
                Port("init", "Init", "signal"),
                Port("reset", "Reset", "signal"),
            ),
            knobs=(),  # P, I, D and error gain have no documented switch positions.
            doc_url=f"{_DOC}docm3b.htm",
            driver=f"{_PKG}.M3b.M3b",
        ),
        ModuleSpec(
            type="VIa",
            kind="combined",
            slot_kind="measure",
            label="Voltage source and current measurement",
            ports=_VI_PORTS,
            knobs=_VI_KNOBS,
            doc_url=f"{_DOC}docvia.htm",
            driver=f"{_PKG}.VIa.VIa",
        ),
        ModuleSpec(
            type="VIb",
            kind="combined",
            slot_kind="measure",
            label="Voltage source and current measurement",
            ports=_VI_PORTS,
            knobs=_VI_KNOBS,
            doc_url=f"{_DOC}docvib.htm",
            driver=f"{_PKG}.VIb.VIb",
        ),
        ModuleSpec(
            type="VIc",
            kind="combined",
            slot_kind="measure",
            label="Voltage source and current measurement",
            ports=_VI_PORTS,
            # The photo returns 404, so source and transimpedance gains are omitted.
            knobs=(_VI_INPUT_MODE,),
            doc_url=f"{_DOC}docvic.htm",
            driver=f"{_PKG}.VIc.VIc",
        ),
        ModuleSpec(
            type="VId",
            kind="combined",
            slot_kind="measure",
            label="Voltage source and current measurement",
            ports=_VI_PORTS,
            knobs=_VI_KNOBS,
            doc_url=f"{_DOC}docvid.htm",
            driver=f"{_PKG}.VId.VId",
        ),
        ModuleSpec(
            type="IVa",
            kind="combined",
            slot_kind="measure",
            label="Current source and voltage measurement",
            ports=_IV_PORTS,
            knobs=(
                Knob(
                    "range",
                    "Range",
                    ("1n", "10n", "100n", "1u", "10u", "100u", "1m", "10m"),
                    "1n",
                    "A/V",
                    "Sets the source range. Defaults to the first listed position.",
                ),
                Knob(
                    "output_mode",
                    "Output mode",
                    ("symm", "single"),
                    "symm",
                    doc="Selects symmetric or single-ended output. Defaults to the first listed position.",
                ),
                Knob(
                    "gain",
                    "Voltage gain",
                    ("1", "10", "100", "1kdc", "1kac"),
                    "1",
                    "V/V",
                    "Sets voltage gain or selects AC coupling at 1k V/V. Defaults to the first listed position.",
                ),
            ),
            doc_url=f"{_DOC}dociva.htm",
            driver=f"{_PKG}.IVa.IVa",
        ),
        ModuleSpec(
            type="IVb",
            kind="combined",
            slot_kind="measure",
            label="Current source and voltage measurement",
            ports=_IV_PORTS,  # ports inferred from the index row, unverified
            knobs=(),  # page not found
            doc_url=f"{_DOC}index-mod.htm",  # its own page docivb.htm is not found
            driver=f"{_PKG}.IVb.IVb",
        ),
        ModuleSpec(
            type="IVc",
            kind="combined",
            slot_kind="measure",
            label="Current source and voltage measurement",
            ports=_IV_PORTS,
            knobs=(
                Knob(
                    "range",
                    "Range",
                    ("1n", "10n", "100n", "1u", "10u"),
                    "1n",
                    "A/V",
                    "Sets the source range. Defaults to the first listed position.",
                ),
                Knob(
                    "muted",
                    "Mute",
                    (False, True),
                    False,
                    doc="Records whether the output is muted. Defaults to not muted.",
                ),
                Knob(
                    "gain",
                    "Voltage gain",
                    ("1", "10", "100", "1kdc", "1kac"),
                    "1",
                    "V/V",
                    "Sets voltage gain or selects AC coupling at 1k V/V. Defaults to the first listed position.",
                ),
            ),
            doc_url=f"{_DOC}docivc.htm",
            driver=f"{_PKG}.IVc.IVc",
        ),
        ModuleSpec(
            type="IVd",
            kind="combined",
            slot_kind="measure",
            label="Current source and voltage measurement",
            ports=_IV_PORTS,
            knobs=(
                Knob(
                    "range",
                    "Range",
                    ("1n", "10n", "100n", "1u", "10u", "100u", "1m", "10m"),
                    "1n",
                    "A/V",
                    "Sets the source range. Defaults to the first listed position.",
                ),
                Knob(
                    "muted",
                    "Mute",
                    (False, True),
                    False,
                    doc="Records whether the output is muted. Defaults to not muted.",
                ),
                Knob(
                    "gain",
                    "Voltage gain",
                    ("1", "10", "100", "1kdc", "1kac"),
                    "1",
                    "V/V",
                    "Sets voltage gain or selects AC coupling at 1k V/V. Defaults to the first listed position.",
                ),
            ),
            doc_url=f"{_DOC}docivd.htm",
            driver=f"{_PKG}.IVd.IVd",
        ),
        ModuleSpec(
            type="SM1a",
            kind="combined",
            slot_kind="measure",
            label="Potentiostat",
            ports=(
                Port("out", "Voltage source out", "drive"),
                Port("v_in", "Voltage sense in", "sense"),
                Port("i_in", "Current sense in", "current"),
            ),
            knobs=(
                Knob(
                    "source_gain",
                    "Source gain",
                    ("0.04", "4"),
                    "0.04",
                    "V/V",
                    "Sets the voltage source gain. Defaults to the first listed position.",
                ),
                Knob(
                    "gain",
                    "Transimpedance gain",
                    ("1M", "10M", "100M", "1G"),
                    "1M",
                    "V/A",
                    "Sets the current-to-voltage gain. Defaults to the first listed position.",
                ),
            ),
            doc_url=f"{_DOC}docsm1a.htm",
            driver=f"{_PKG}.SM1a.SM1a",
        ),
        ModuleSpec(
            type="U1a",
            kind="misc",
            slot_kind="any",
            label="Six-channel soft switch",
            ports=(
                Port("ch1_tl", "Channel 1 upper left", "signal"),
                Port("ch1_tr", "Channel 1 upper right", "signal"),
                Port("ch1_bl", "Channel 1 lower left", "signal"),
                Port("ch1_br", "Channel 1 lower right", "signal"),
                Port("control1", "Channel 1 control", "signal"),
                Port("ch2_tl", "Channel 2 upper left", "signal"),
                Port("ch2_tr", "Channel 2 upper right", "signal"),
                Port("ch2_bl", "Channel 2 lower left", "signal"),
                Port("ch2_br", "Channel 2 lower right", "signal"),
                Port("control2", "Channel 2 control", "signal"),
                Port("ch3_tl", "Channel 3 upper left", "signal"),
                Port("ch3_tr", "Channel 3 upper right", "signal"),
                Port("ch3_bl", "Channel 3 lower left", "signal"),
                Port("ch3_br", "Channel 3 lower right", "signal"),
                Port("control3", "Channel 3 control", "signal"),
                Port("ch4_tl", "Channel 4 upper left", "signal"),
                Port("ch4_tr", "Channel 4 upper right", "signal"),
                Port("ch4_bl", "Channel 4 lower left", "signal"),
                Port("ch4_br", "Channel 4 lower right", "signal"),
                Port("control4", "Channel 4 control", "signal"),
                Port("ch5_tl", "Channel 5 upper left", "signal"),
                Port("ch5_tr", "Channel 5 upper right", "signal"),
                Port("ch5_bl", "Channel 5 lower left", "signal"),
                Port("ch5_br", "Channel 5 lower right", "signal"),
                Port("control5", "Channel 5 control", "signal"),
                Port("ch6_tl", "Channel 6 upper left", "signal"),
                Port("ch6_tr", "Channel 6 upper right", "signal"),
                Port("ch6_bl", "Channel 6 lower left", "signal"),
                Port("ch6_br", "Channel 6 lower right", "signal"),
                Port("control6", "Channel 6 control", "signal"),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}docu1a.htm",
            driver=f"{_PKG}.U1a.U1a",
        ),
        ModuleSpec(
            type="U1b",
            kind="misc",
            slot_kind="any",
            label="Four-channel changeover soft switch",
            ports=(
                Port("common1", "Channel 1 common", "signal"),
                Port("no1", "Channel 1 normally open", "signal"),
                Port("nc1", "Channel 1 normally closed", "signal"),
                Port("control1", "Channel 1 control", "signal"),
                Port("common2", "Channel 2 common", "signal"),
                Port("no2", "Channel 2 normally open", "signal"),
                Port("nc2", "Channel 2 normally closed", "signal"),
                Port("control2", "Channel 2 control", "signal"),
                Port("common3", "Channel 3 common", "signal"),
                Port("no3", "Channel 3 normally open", "signal"),
                Port("nc3", "Channel 3 normally closed", "signal"),
                Port("control3", "Channel 3 control", "signal"),
                Port("common4", "Channel 4 common", "signal"),
                Port("no4", "Channel 4 normally open", "signal"),
                Port("nc4", "Channel 4 normally closed", "signal"),
                Port("control4", "Channel 4 control", "signal"),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}docu1b.htm",
            driver=f"{_PKG}.U1b.U1b",
        ),
        ModuleSpec(
            type="P2a",
            kind="misc",
            slot_kind="any",
            label="Cryogenic preamplifier supply",
            ports=(
                Port("out", "out", "drive"),
            ),  # ports inferred from the index row, unverified
            knobs=(),  # page not found
            doc_url=f"{_DOC}index-mod.htm",  # its own page docp2a.htm is not found
            driver=f"{_PKG}.P2a.P2a",
        ),
        ModuleSpec(
            type="P2b",
            kind="misc",
            slot_kind="any",
            label="Cryogenic preamplifier supply",
            ports=(
                Port("out", "out", "drive"),
                Port("vmon", "Voltage monitor", "signal"),
                Port("imon", "Current monitor", "signal"),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}docp2b.htm",
            driver=f"{_PKG}.P2b.P2b",
        ),
        ModuleSpec(
            type="P2c",
            kind="misc",
            slot_kind="any",
            label="Dual cryogenic preamplifier supply",
            ports=(
                Port("outA", "out A", "drive"),
                Port("outB", "out B", "drive"),
                Port("vmonA", "Voltage monitor A", "signal"),
                Port("imonA", "Current monitor A", "signal"),
                Port("vmonB", "Voltage monitor B", "signal"),
                Port("imonB", "Current monitor B", "signal"),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}docp2c.htm",
            driver=f"{_PKG}.P2c.P2c",
        ),
        ModuleSpec(
            type="P3",
            kind="misc",
            slot_kind="any",
            label="Cryogenic preamplifier supply interface",
            ports=(  # ports inferred from the index row, unverified
                Port("in", "in", "signal"),
                Port("out", "out", "signal"),
            ),
            knobs=(),  # page not found
            doc_url=f"{_DOC}index-mod.htm",  # its own page docp3.htm is not found
            driver=f"{_PKG}.P3.P3",
        ),
        ModuleSpec(
            type="F1a",
            kind="misc",
            slot_kind="any",
            label="Passive IQ downmixer",
            ports=(  # ports inferred from the index row, unverified
                Port("rf_in", "RF in", "signal"),
                Port("lo", "LO in", "signal"),
                Port("i_out", "I out", "signal"),
                Port("q_out", "Q out", "signal"),
            ),
            knobs=(),  # page not found
            doc_url=f"{_DOC}index-mod.htm",  # its own page docf1a.htm is not found
            driver=f"{_PKG}.F1a.F1a",
        ),
        ModuleSpec(
            type="F1b",
            kind="misc",
            slot_kind="any",
            label="Passive IQ upmixer",
            ports=(  # ports inferred from the index row, unverified
                Port("i_in", "I in", "signal"),
                Port("q_in", "Q in", "signal"),
                Port("lo", "LO in", "signal"),
                Port("rf_out", "RF out", "signal"),
            ),
            knobs=(),  # page not found
            doc_url=f"{_DOC}index-mod.htm",  # its own page docf1b.htm is not found
            driver=f"{_PKG}.F1b.F1b",
        ),
        ModuleSpec(
            type="F1c",
            kind="misc",
            slot_kind="any",
            label="Passive IQ up/down mixer",
            ports=(
                Port("rf", "RF", "signal"),
                Port("i", "I", "signal"),
                Port("q", "Q", "signal"),
                Port("lo", "LO in", "signal"),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}docf1c.htm",
            driver=f"{_PKG}.F1c.F1c",
        ),
        ModuleSpec(
            type="F2a",
            kind="misc",
            slot_kind="any",
            label="Tunable RF bandpass filters",
            ports=(
                Port("in1", "Filter 1 in", "signal"),
                Port("out1", "Filter 1 out", "signal"),
                Port("in2", "Filter 2 in", "signal"),
                Port("out2", "Filter 2 out", "signal"),
                Port("in3", "Filter 3 in", "signal"),
                Port("out3", "Filter 3 out", "signal"),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}docf2a.htm",
            driver=f"{_PKG}.F2a.F2a",
        ),
        ModuleSpec(
            type="A1",
            kind="misc",
            slot_kind="any",
            label="Connector adapter",
            ports=(
                Port("lemo", "LEMO", "signal"),
                Port("bnc_2", "BNC pin 2", "signal"),
                Port("bnc_4", "BNC pin 4", "signal"),
                Port("bnc_24", "BNC pins 2 and 4", "signal"),
                Port("mcx_2", "MCX pin 2", "signal"),
                Port("mcx_4", "MCX pin 4", "signal"),
                Port("banana_1", "Banana pin 1", "signal"),
                Port("banana_2", "Banana pin 2", "signal"),
                Port("banana_3", "Banana pin 3", "signal"),
                Port("banana_4", "Banana pin 4", "signal"),
                Port("ground_1", "Ground 1", "signal"),
                Port("ground_2", "Ground 2", "signal"),
                Port("ground_3", "Ground 3", "signal"),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}doca1.htm",
            driver=f"{_PKG}.A1.A1",
        ),
        ModuleSpec(
            type="A2",
            kind="misc",
            slot_kind="any",
            label="Ground and link adapter",
            ports=(
                *(Port(f"ground_{n}", f"Ground {n}", "signal") for n in range(1, 5)),
                *(
                    Port(f"link_{group}_{n}", f"Link {group} jack {n}", "signal")
                    for group in range(1, 5)
                    for n in range(1, 4)
                ),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}doca2.htm",
            driver=f"{_PKG}.A2.A2",
        ),
        ModuleSpec(
            type="A3c",
            kind="misc",
            slot_kind="any",
            label="Overvoltage protection adapter",
            ports=(
                Port("ground_1", "Ground 1", "signal"),
                Port("ground_2", "Ground 2", "signal"),
                *(
                    Port(
                        f"clamp_{group}_{side}_{n}",
                        f"Clamp {group} {side} jack {n}",
                        "signal",
                    )
                    for group in range(1, 4)
                    for side in ("left", "right")
                    for n in range(1, 3)
                ),
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}doca3c.htm",
            driver=f"{_PKG}.A3c.A3c",
        ),
        ModuleSpec(
            type="A4",
            kind="misc",
            slot_kind="any",
            label="SMA to MCX adapter",
            ports=tuple(
                Port(f"{connector}_{n}", f"{label} {n}", "signal")
                for n in range(1, 7)
                for connector, label in (
                    ("sma", "SMA"),
                    ("mcx", "MCX signal"),
                    ("mcx_gnd", "MCX ground"),
                )
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}doca4.htm",
            driver=f"{_PKG}.A4.A4",
        ),
        ModuleSpec(
            type="A6",
            kind="misc",
            slot_kind="any",
            label="Series current-limiting resistor panel",
            ports=tuple(
                Port(f"resistor_{n}_{side}", f"Resistor {n} {side}", "signal")
                for n in range(1, 13)
                for side in ("left", "right")
            ),
            knobs=(),  # page lists no switches
            doc_url=f"{_DOC}doca6.htm",
            driver=f"{_PKG}.A6.A6",
        ),
        ModuleSpec(
            type="R1",
            kind="misc",
            slot_kind="any",
            label="Sample simulator",
            ports=(
                Port("mcx_2_prime", "MCX 2′", "signal"),
                Port("mcx_4_prime", "MCX 4′", "signal"),
                Port("lemo", "LEMO", "signal"),
                Port("mcx_2", "MCX 2", "signal"),
                Port("mcx_4", "MCX 4", "signal"),
            ),
            knobs=(
                Knob(
                    "resistance",
                    "Resistance",
                    (
                        "0",
                        "10",
                        "100",
                        "1k",
                        "10k",
                        "100k",
                        "1M",
                        "10M",
                        "100M",
                        "1G",
                        "open",
                    ),
                    "0",
                    "Ω",
                    "Sets the simulation resistance. Defaults to the first listed position.",
                ),
                Knob(
                    "mode",
                    "Mode",
                    ("series", "shunt"),
                    "series",
                    doc="Selects the series or shunt resistor connection. Defaults to series.",
                ),
            ),
            doc_url=f"{_DOC}docr1.htm",
            driver=f"{_PKG}.R1.R1",
        ),
        ModuleSpec(
            type="R2",
            kind="misc",
            slot_kind="any",
            label="Dual gate protection resistor",
            ports=tuple(
                Port(f"{port.id}_{side}", f"{port.label} {side}", port.kind)
                for side in ("upper", "lower")
                for port in (
                    Port("gate", "Gate", "gate"),
                    Port("lemo", "LEMO", "signal"),
                    Port("dac_2", "DAC 2", "signal"),
                    Port("dac_4", "DAC 4", "signal"),
                )
            ),
            knobs=tuple(
                Knob(
                    f"resistance_{side}",
                    f"Resistance {side}",
                    ("10M", "100M", "1G"),
                    "10M",
                    "Ω",
                    "Sets the series gate resistance. Defaults to the first listed position.",
                )
                for side in ("upper", "lower")
            ),
            doc_url=f"{_DOC}docr2.htm",
            driver=f"{_PKG}.R2.R2",
        ),
    ]
}
