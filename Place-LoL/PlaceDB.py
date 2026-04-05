"""
Compatibility shim.

Historical scripts under this repo use `import PlaceDB` while the actual module
lives in `dreamplace/PlaceDB.py`.
"""

from dreamplace.PlaceDB import *  # noqa: F401,F403

