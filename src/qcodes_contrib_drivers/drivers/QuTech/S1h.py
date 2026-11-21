from .ivvi_module import IVVIModule


class S1h(IVVIModule):
    """Virtual driver for the QuTech S1h high-voltage source module. https://qtwork.tudelft.nl/~schouten/ivvi/doc-mod/docs1h.htm"""

    module_type = "S1h"
