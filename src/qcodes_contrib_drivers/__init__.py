
try:
    from ._version import __version__
except ImportError:
    __version__ = "0.0.dev"

# Import virtual instruments and nodes for easy access
try:
    from .virtual import SignalChain
    from .nodes import (
        AbstractSource, AbstractConverter, AbstractAmplifier, AbstractLockIn,
        MFLISource, ManualVITransformer, ManualVoltagePreamp, MFLILockIn
    )
    __all__ = [
        '__version__',
        'SignalChain',
        'AbstractSource', 'AbstractConverter', 'AbstractAmplifier', 'AbstractLockIn',
        'MFLISource', 'ManualVITransformer', 'ManualVoltagePreamp', 'MFLILockIn'
    ]
except ImportError:
    # QCoDeS not available, only expose version
    __all__ = ['__version__']
