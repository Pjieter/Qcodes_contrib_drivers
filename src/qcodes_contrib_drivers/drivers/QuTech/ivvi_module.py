"""Virtual driver for an IVVI slot module described by the catalogue."""

from typing import TYPE_CHECKING, ClassVar

from qcodes.instrument import Instrument, InstrumentBaseKWArgs
from qcodes.parameters import ManualParameter
from qcodes.validators import Enum

from .catalogue import CATALOGUE, slots_for

if TYPE_CHECKING:
    from typing_extensions import Unpack


class IVVIModule(Instrument):
    """Record the physical slot and knob positions of a manual IVVI module.

    Subclasses set module_type to their key in the catalogue.
    """

    module_type: ClassVar[str]

    def __init__(self, name: str, **kwargs: "Unpack[InstrumentBaseKWArgs]") -> None:
        super().__init__(name, **kwargs)
        spec = CATALOGUE[self.module_type]
        slots = slots_for(spec.slot_kind)
        self.add_parameter(
            "slot",
            parameter_class=ManualParameter,
            initial_value=slots[0],
            label="Module slot",
            vals=Enum(*slots),
            docstring="Rack slot the module sits in.",
        )
        for knob in spec.knobs:
            self.add_parameter(
                knob.name,
                parameter_class=ManualParameter,
                initial_value=knob.initial,
                label=knob.label,
                unit=knob.unit,
                vals=Enum(*knob.values),
                docstring=knob.doc or None,
            )

    def get_idn(self) -> dict[str, str | None]:
        return {
            "vendor": "QuTech",
            "model": self.module_type,
            "serial": None,
            "firmware": None,
        }
