"""Root pytest configuration.

Adds src/ to sys.path so tests can import modules from src/ without
installing the package.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
