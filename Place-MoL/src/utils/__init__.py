"""
Utility modules for placement algorithms.
"""

# Import modules that may have optional dependencies
try:
    from .hpwl_computer import HPWLComputer
except ModuleNotFoundError:
    HPWLComputer = None

try:
    from .layout_plotter import LayoutPlotter
except ModuleNotFoundError:
    LayoutPlotter = None

try:
    from .def_processor import DefProcessor
except ModuleNotFoundError:
    DefProcessor = None

__all__ = [
    'HPWLComputer',
    'LayoutPlotter',
    'DefProcessor',
]

