import os
import sys

# Ensure tests can find parent dir.
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    )

import lib
