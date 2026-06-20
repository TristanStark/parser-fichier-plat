"""
Fixed-width segmented file generator.

This package provides a small framework to generate fixed-width logical records
that can produce multiple logical line types per source record and then split
each logical line into physical segments with a generated prefix.
"""

from .conditions import Condition, parse_condition, normalize_conditions
from .fields import RegisteredField
from .prefix import SegmentPrefixBuilder
from .solver import FixedWidthLineSolver
from .master import SegmentedFlatFileMaster
from .codegen import (
    GenerationSpec,
    LineField,
    LineTypeSpec,
    generate_code,
    read_structure_csv,
    safe_identifier,
    write_generated_code,
)

__all__ = [
    "Condition",
    "parse_condition",
    "normalize_conditions",
    "RegisteredField",
    "SegmentPrefixBuilder",
    "FixedWidthLineSolver",
    "SegmentedFlatFileMaster",
    "GenerationSpec",
    "LineField",
    "LineTypeSpec",
    "generate_code",
    "read_structure_csv",
    "safe_identifier",
    "write_generated_code",
]
