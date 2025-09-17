"""
QCoDeS driver for Zurich Instruments MFLI Lock-in Amplifier.

Based on the HF2LI driver but adapted for MFLI specifics.
"""

from typing import Dict, List, Optional, Sequence, Any, Union
import numpy as np
import logging
log = logging.getLogger(__name__)

import zhinst.utils
import qcodes as qc
from qcodes.instrument import Instrument
import qcodes.validators as vals

class MFLI(Instrument):
    """QCoDeS driver for Zurich Instruments MFLI lockin amplifier.

    This driver is meant to emulate a single-channel lockin amplifier,
    so one instance has a single demodulator, a single sigout channel,
    and multiple auxout channels (for X, Y, R, Theta, or an arbitrary manual value).
    Multiple instances can be run simultaneously as independent lockin amplifiers.

    This instrument has a great deal of additional functionality that is
    not currently supported by this driver.

    Args:
        name: Name of instrument.
        device: Device name, e.g. "dev1234", used to create zhinst API session.
        demod: Index of the demodulator to use.
        sigout: Index of the sigout channel to use as excitation source.
        auxouts: Dict of the form {output: index},
            where output is a key of MFLI.OUTPUT_MAPPING, for example {"X": 0, "Y": 3}
            to use the instrument as a lockin amplifier in X-Y mode with auxout channels 0 and 3.
        num_sigout_mixer_channels: Number of mixer channels to enable on the sigouts. Default: 1.
    """
    OUTPUT_MAPPING = {-1: 'manual', 0: 'X', 1: 'Y', 2: 'R', 3: 'Theta'}
    
    def __init__(self, name: str, device: str, demod: int, sigout: int,
        auxouts: Dict[str, int], num_sigout_mixer_channels: int=1, **kwargs) -> None:
        super().__init__(name, **kwargs)
        instr = zhinst.utils.create_api_session(device, 1, required_devtype='MFLI')
        self.daq, self.dev_id, self.props = instr
        self.demod = demod
        self.sigout = sigout
        self.auxouts = auxouts
        log.info(f'Successfully connected to {name}.')

        # Add auxout parameters for X, Y, R, Theta readouts
        for ch in self.auxouts:
            self.add_parameter(
                name=ch,
                label=f'Scaled {ch} output value',
                unit='V',
                get_cmd=lambda channel=ch: self._get_output_value(channel),
                get_parser=float,
                docstring=f'Scaled and demodulated {ch} value.'
            )
            self.add_parameter(
                name=f'gain_{ch}',
                label=f'{ch} output gain',
                unit='V/Vrms',
                get_cmd=lambda channel=ch: self._get_gain(channel),
                get_parser=float,
                set_cmd=lambda gain, channel=ch: self._set_gain(gain, channel),
                vals=vals.Numbers(),
                docstring=f'Gain factor for {ch}.'
            )
            self.add_parameter(
                name=f'offset_{ch}',
                label=f'{ch} output offset',
                unit='V',
                get_cmd=lambda channel=ch: self._get_offset(channel),
                get_parser=float,
                set_cmd=lambda offset, channel=ch: self._set_offset(offset, channel),
                vals=vals.Numbers(-10, 10),  # MFLI has wider range than HF2LI
                docstring=f'Manual offset for {ch}, applied after scaling.'
            )
            self.add_parameter(
                name=f'output_{ch}',
                label=f'{ch} output select',
                get_cmd=lambda channel=ch: self._get_output_select(channel),
                get_parser=str
            )
            # Making output select only gettable, since we are
            # explicitly mapping auxouts to X, Y, R, Theta, etc.
            self._set_output_select(ch)

        # Demodulator parameters
        self.add_parameter(
            name='phase',
            label='Phase',
            unit='deg',
            get_cmd=self._get_phase,
            get_parser=float,
            set_cmd=self._set_phase,
            vals=vals.Numbers(-180, 180)
        )
        self.add_parameter(
            name='time_constant',
            label='Time constant',
            unit='s',
            get_cmd=self._get_time_constant,
            get_parser=float,
            set_cmd=self._set_time_constant,
            vals=vals.Numbers()
        )
        self.add_parameter(
            name='frequency',
            label='Frequency',
            unit='Hz',
            get_cmd=self._get_frequency,
            get_parser=float,
            set_cmd=self._set_frequency,
            vals=vals.Numbers(1e-3, 5e6)  # MFLI frequency range
        )
        self.add_parameter(
            name='sensitivity',
            label='Input sensitivity',
            unit='V',
            get_cmd=self._get_sensitivity,
            get_parser=float,
            set_cmd=self._set_sensitivity,
            vals=vals.Enum(1e-9, 3e-9, 10e-9, 30e-9, 100e-9, 300e-9, 
                          1e-6, 3e-6, 10e-6, 30e-6, 100e-6, 300e-6,
                          1e-3, 3e-3, 10e-3, 30e-3, 100e-3, 300e-3, 1.0)
        )
        self.add_parameter(
            name='input_range',
            label='Input range',
            unit='V',
            get_cmd=self._get_input_range,
            get_parser=float,
            set_cmd=self._set_input_range,
            vals=vals.Enum(10e-3, 100e-3, 1.0, 10.0)  # MFLI input ranges
        )

        # Signal output parameters
        self.add_parameter(
            name='output_on',
            label='Signal output on',
            get_cmd=self._get_output_on,
            get_parser=bool,
            set_cmd=self._set_output_on,
            vals=vals.Bool()
        )
        self.add_parameter(
            name='amplitude',
            label='Signal output amplitude',
            unit='V',
            get_cmd=self._get_amplitude,
            get_parser=float,
            set_cmd=self._set_amplitude,
            vals=vals.Numbers(0, 1.5),  # MFLI amplitude range
            docstring='RMS amplitude of signal output'
        )
        self.add_parameter(
            name='sigout_range',
            label='Signal output range',
            unit='V',
            get_cmd=self._get_sigout_range,
            get_parser=float,
            set_cmd=self._set_sigout_range,
            vals=vals.Enum(0.01, 0.1, 1, 10)
        )
        self.add_parameter(
            name='sigout_offset',
            label='Signal output offset',
            unit='V',
            get_cmd=self._get_sigout_offset,
            get_parser=float,
            set_cmd=self._set_sigout_offset,
            vals=vals.Numbers(-1, 1),
            docstring='Multiply by sigout_range to get actual offset voltage.'
        )
        
        # Signal output mixer channels
        for i in range(num_sigout_mixer_channels):
            self.add_parameter(
                name=f'sigout_enable{i}',
                label=f'Signal output mixer {i} enable',
                get_cmd=lambda mixer_channel=i: self._get_sigout_enable(mixer_channel),
                get_parser=int,
                set_cmd=lambda val, mixer_channel=i: self._set_sigout_enable(mixer_channel, val),
                vals=vals.Enum(0, 1, 2, 3),
                docstring="""\
                0: Channel off (unconditionally)
                1: Channel on (unconditionally)
                2: Channel off (will be turned off on next change of sign from negative to positive)
                3: Channel on (will be turned on on next change of sign from negative to positive)
                """
            )
            self.add_parameter(
                name=f'sigout_amplitude{i}',
                label=f'Signal output mixer {i} amplitude',
                unit='Gain',
                get_cmd=lambda mixer_channel=i: self._get_sigout_amplitude(mixer_channel),
                get_parser=float,
                set_cmd=lambda amp, mixer_channel=i: self._set_sigout_amplitude(mixer_channel, amp),
                vals=vals.Numbers(-1, 1),
                docstring='Multiply by sigout_range to get actual output voltage.'
            )

    # Demodulator methods
    def _get_phase(self) -> float:
        path = f'/{self.dev_id}/demods/{self.demod}/phaseshift'
        return self.daq.getDouble(path)

    def _set_phase(self, phase: float) -> None:
        path = f'/{self.dev_id}/demods/{self.demod}/phaseshift'
        self.daq.setDouble(path, phase)

    def _get_time_constant(self) -> float:
        path = f'/{self.dev_id}/demods/{self.demod}/timeconstant'
        return self.daq.getDouble(path)

    def _set_time_constant(self, tc: float) -> None:
        path = f'/{self.dev_id}/demods/{self.demod}/timeconstant'
        self.daq.setDouble(path, tc)

    def _get_frequency(self) -> float:
        path = f'/{self.dev_id}/demods/{self.demod}/freq'
        return self.daq.getDouble(path)

    def _set_frequency(self, freq: float) -> None:
        path = f'/{self.dev_id}/demods/{self.demod}/freq'
        self.daq.setDouble(path, freq)

    def _get_sensitivity(self) -> float:
        # MFLI uses current range, need to convert to sensitivity
        path = f'/{self.dev_id}/demods/{self.demod}/range'
        return self.daq.getDouble(path)

    def _set_sensitivity(self, sensitivity: float) -> None:
        path = f'/{self.dev_id}/demods/{self.demod}/range'
        self.daq.setDouble(path, sensitivity)

    def _get_input_range(self) -> float:
        path = f'/{self.dev_id}/sigins/{self.demod}/range'
        return self.daq.getDouble(path)

    def _set_input_range(self, range_val: float) -> None:
        path = f'/{self.dev_id}/sigins/{self.demod}/range'
        self.daq.setDouble(path, range_val)

    # Auxout methods
    def _get_gain(self, channel: str) -> float:
        path = f'/{self.dev_id}/auxouts/{self.auxouts[channel]}/scale'
        return self.daq.getDouble(path)

    def _set_gain(self, gain: float, channel: str) -> None:
        path = f'/{self.dev_id}/auxouts/{self.auxouts[channel]}/scale'
        self.daq.setDouble(path, gain)

    def _get_offset(self, channel: str) -> float:
        path = f'/{self.dev_id}/auxouts/{self.auxouts[channel]}/offset'
        return self.daq.getDouble(path)

    def _set_offset(self, offset: float, channel: str) -> None:
        path = f'/{self.dev_id}/auxouts/{self.auxouts[channel]}/offset'
        self.daq.setDouble(path, offset)

    def _get_output_value(self, channel: str) -> float:
        path = f'/{self.dev_id}/auxouts/{self.auxouts[channel]}/value'
        return self.daq.getDouble(path)

    def _get_output_select(self, channel: str) -> str:
        path = f'/{self.dev_id}/auxouts/{self.auxouts[channel]}/outputselect'
        idx = self.daq.getInt(path)
        return self.OUTPUT_MAPPING[idx]

    def _set_output_select(self, channel: str) -> None:
        path = f'/{self.dev_id}/auxouts/{self.auxouts[channel]}/outputselect'
        keys = list(self.OUTPUT_MAPPING.keys())
        idx = keys[list(self.OUTPUT_MAPPING.values()).index(channel)]
        self.daq.setInt(path, idx)

    # Signal output methods
    def _get_output_on(self) -> bool:
        path = f'/{self.dev_id}/sigouts/{self.sigout}/on'
        return bool(self.daq.getInt(path))

    def _set_output_on(self, state: bool) -> None:
        path = f'/{self.dev_id}/sigouts/{self.sigout}/on'
        self.daq.setInt(path, int(state))

    def _get_amplitude(self) -> float:
        # Get amplitude from mixer channel 0
        path = f'/{self.dev_id}/sigouts/{self.sigout}/amplitudes/0'
        return self.daq.getDouble(path)

    def _set_amplitude(self, amplitude: float) -> None:
        # Set amplitude on mixer channel 0
        path = f'/{self.dev_id}/sigouts/{self.sigout}/amplitudes/0'
        self.daq.setDouble(path, amplitude)

    def _get_sigout_range(self) -> float:
        path = f'/{self.dev_id}/sigouts/{self.sigout}/range'
        return self.daq.getDouble(path)

    def _set_sigout_range(self, rng: float) -> None:
        path = f'/{self.dev_id}/sigouts/{self.sigout}/range'
        self.daq.setDouble(path, rng)

    def _get_sigout_offset(self) -> float:
        path = f'/{self.dev_id}/sigouts/{self.sigout}/offset'
        return self.daq.getDouble(path)

    def _set_sigout_offset(self, offset: float) -> None:
        path = f'/{self.dev_id}/sigouts/{self.sigout}/offset'
        self.daq.setDouble(path, offset)

    def _get_sigout_amplitude(self, mixer_channel: int) -> float:
        path = f'/{self.dev_id}/sigouts/{self.sigout}/amplitudes/{mixer_channel}'
        return self.daq.getDouble(path)

    def _set_sigout_amplitude(self, mixer_channel: int, amp: float) -> None:
        path = f'/{self.dev_id}/sigouts/{self.sigout}/amplitudes/{mixer_channel}'
        self.daq.setDouble(path, amp)

    def _get_sigout_enable(self, mixer_channel: int) -> int:
        path = f'/{self.dev_id}/sigouts/{self.sigout}/enables/{mixer_channel}'
        return self.daq.getInt(path)

    def _set_sigout_enable(self, mixer_channel: int, val: int) -> None:
        path = f'/{self.dev_id}/sigouts/{self.sigout}/enables/{mixer_channel}'
        self.daq.setInt(path, val)

    def sample(self) -> dict:
        """Get a single sample from the demodulator."""
        path = f'/{self.dev_id}/demods/{self.demod}/sample'
        return self.daq.getSample(path)