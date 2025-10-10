# Helper to import OwlBuilder when running tests directly
import sys
import os
from importlib import import_module

# Ensure the directory containing 'Project Files' is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Import OwlBuilder from the same folder
from OwlBuilder import OwlBuilder

def builder_serialize_from_updates(updates):
    builder = OwlBuilder()
    result = builder.process(updates)
    return result.get('owl', '')
