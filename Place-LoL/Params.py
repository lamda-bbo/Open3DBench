"""
Compatibility shim.

Historical scripts under this repo use `import Params` while the actual module
lives in `dreamplace/Params.py`. Keeping this thin wrapper lets conversion-only
workflows avoid touching the rest of the DreamPlace code.
"""

from dreamplace.Params import *  # noqa: F401,F403

