######################
QCoDeS contrib drivers
######################

This repository contains QCoDeS instrument drivers developed by members of the QCoDeS community.
These drivers are not supported by the QCoDeS developers but instead supported on a best effort basis
by the developers of the individual drivers.

Default branch is now main
##########################

The default branch in qcodes_contrib_drivers has been renamed to main.
If you are working with a local clone of qcodes_contrib_drivers you should update it as follows.

* Run ``git fetch origin`` and ``git checkout main``
* Run ``git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main`` to update your HEAD reference.

IVVI_rack Signal Chain Virtual Instrument
#########################################

New modular QCoDeS architecture for IVVI_rack with current-setpoint control.

Topology
********

::

  [MFLI AC Voltage Source] → [Manual V→I Transformer] → [Sample] → [Manual Voltage Preamp] → [MFLI Input & Demod]

Features
********

* **Single current setpoint parameter (I_set)**: Set target current and automatically compute required source voltage
* **Open-loop current control**: Via manual transconductance (gm) with optional closed-loop refinement capability
* **Coupled frequency control**: Single reference_frequency parameter updates both source and lock-in
* **Guard functions**: Advisory warnings for predicted lock-in input overload (configurable threshold)
* **Derived physics parameters**: Pure functions for I_cmd, I_meas, V_sample_ac_meas, recommended_sensitivity
* **Modular architecture**: Abstract bases + concrete nodes for extensibility
* **Manual parameter snapshots**: Proper QCoDeS ManualParameter usage for operator state capture

Quick Start
***********

.. code-block:: python

   from qcodes_contrib_drivers.nodes import (
       MFLISource, ManualVITransformer, 
       ManualVoltagePreamp, MFLILockIn
   )
   from qcodes_contrib_drivers.virtual import SignalChain
   
   # Create device nodes (adapt to your actual MFLI driver)
   src_v = MFLISource(your_mfli_driver)
   vi = ManualVITransformer()
   preamp = ManualVoltagePreamp()
   lockin = MFLILockIn(your_mfli_driver)
   
   # Create signal chain
   chain = SignalChain(src_v, vi, preamp, lockin)
   
   # Configure
   chain.gm_a_per_v(1e-3)      # 1 mA/V transconductance
   chain.preamp_gain(100.0)    # 100 V/V gain
   chain.R_est(10e3)           # 10 kΩ sample resistance estimate
   chain.reference_frequency(1000)  # 1 kHz coupled frequency
   
   # Set target current - automatically computes source voltage
   chain.I_set(1e-6)           # 1 µA target current
   
   # Read back values
   print(f"Commanded current: {chain.I_cmd()} A")
   print(f"Measured current: {chain.I_meas()} A")  # if R_est set
   print(f"Sample voltage: {chain.V_sample_ac_meas()} V")

Units and Conventions
********************

* **Current**: Amperes (A)
* **Voltage**: Volts (V, RMS for AC unless noted)
* **Frequency**: Hertz (Hz)
* **Resistance**: Ohms (Ω)
* **Transconductance**: A/V (RMS)
* **Voltage Gain**: V/V
* **Amplitude Convention**: RMS (default), with conversion support for peak/peak-to-peak

Safety Notes
************

* Guard functions warn when predicted preamp output exceeds 80% of lock-in input range
* Manual parameters (gm, gain, R_est) must be set by operator based on physical setup
* Open-loop current control assumes stable transconductance - verify gm calibration regularly
* Always verify I_cmd vs I_meas agreement when R_est is available

Example
*******

See ``examples/ivvi_rack_signal_chain_demo.ipynb`` for a complete working example.

Getting started
###############

Prerequisites
*************

The drivers in this repository work with and heavily depend on QCoDeS. Start by installing `QCoDeS <https://github.com/QCoDeS/Qcodes>`_ .

Installation
************

Install the contrib drivers with ``pip``

.. code-block::

  pip install qcodes_contrib_drivers

Drivers documentation
*********************

The documentations of the drivers in this repository can be read `here <https://qcodes.github.io/Qcodes_contrib_drivers>`_.

Contributing
############

This repository is open for contribution of new drivers,
as well as improvements to existing drivers. Each driver should
contain an implementation of the driver and a Jupyter notebook showing how the
driver should be used. In addition we strongly encourage writing tests for the drivers.
An introduction for writing tests with PyVISA-sim can be found in the QCoDeS documentation linked
below.

Drivers are expected to be added to ``qcodes_contrib_drivers/drivers/MakerOfInstrument/`` folder
while examples should be added to the ``docs/examples`` folder and tests placed in the
``qcodes_contrib_drivers/tests/MakerOfInstrument`` folder. Please follow naming conventions for
consistency.

For general information about writing drivers and how to write tests refer to the `QCoDeS documentation <http://microsoft.github.io/Qcodes/>`_.
Especially the examples `here <https://microsoft.github.io/Qcodes/examples/index.html#writing-drivers>`__
are useful.

LICENSE
#######

QCoDeS-Contrib-drivers is licensed under the MIT license except the ``Tektronix AWG520`` and
``Tektronix Keithley 2700`` drivers which are licensed under the GPL 2 or later License.
