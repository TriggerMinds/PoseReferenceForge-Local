"""Recursive native-type sanitizer for JSON serialization.

Ensures numpy types, Enums, and other non-native types are converted
to their Python native equivalents. Prevents default=str from producing
"True"/"False" strings instead of true/false booleans.
"""
import numpy as np
from pathlib import Path
from enum import Enum


def sanitize(obj):
    """Recursively convert all values to JSON-native Python types."""
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize(v) for v in obj]
    elif isinstance(obj, tuple):
        return tuple(sanitize(v) for v in obj)
    elif isinstance(obj, Path):
        return str(obj)
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return sanitize(obj.tolist())
    elif isinstance(obj, bool):
        return bool(obj)
    elif isinstance(obj, int):
        return int(obj)
    elif isinstance(obj, float):
        return float(obj)
    elif obj is None:
        return None
    return obj
