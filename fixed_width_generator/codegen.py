import csv
import keyword
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional


class LineField:
    """Description of one field read from a structure CSV file."""

    def __init__(self, original_name: str, name: str, length: int, field_format: str, start: int):
        self.original_name = original_name
        self.name = name
        self.length = length
        self.field_format = field_format
        self.start = start

    def is_numeric(self) -> bool:
        return self.field_format == "N"


class LineTypeSpec:
    """Description of one generated logical line type."""

    def __init__(self, name: str, fields: List[LineField], csv_path: str):
        self.name = name
        self.fields = fields
        self.csv_path = csv_path

    def safe_name(self) -> str:
        return safe_identifier(self.name).upper()

    def safe_prefix(self) -> str:
        return safe_identifier(self.name).lower()

    def numeric_fields(self) -> List[LineField]:
        return [field for field in self.fields if field.is_numeric()]


class GenerationSpec:
    """Complete code generation specification."""

    def __init__(
        self,
        logical_length: int,
        line_types: List[LineTypeSpec],
        next_count_fields: Optional[Dict[str, str]] = None,
        segment_payload_length: int = 200,
        physical_prefix_length: int = 25,
    ):
        self.logical_length = logical_length
        self.segment_payload_length = segment_payload_length
        self.physical_prefix_length = physical_prefix_length
        self.line_types = line_types
        self.next_count_fields = next_count_fields or {}


def safe_identifier(value: str, fallback: str = "field") -> str:
    """Return a valid snake_case Python identifier without using dataclasses."""

    value = remove_accents(str(value or "")).strip().lower()
    value = re.sub(r"[^a-z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")

    if not value:
        value = fallback

    if value[0].isdigit():
        value = f"_{value}"

    if keyword.iskeyword(value):
        value = f"{value}_"

    return value


def remove_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_header(value: str) -> str:
    return safe_identifier(value, fallback="header")


def resolve_column(headers: Dict[str, str], aliases: List[str]) -> str:
    normalized_aliases = [normalize_header(alias) for alias in aliases]

    for alias in normalized_aliases:
        if alias in headers:
            return headers[alias]

    available = ", ".join(sorted(headers.keys()))
    expected = ", ".join(aliases)
    raise ValueError(
        f"Missing expected CSV column. Expected one of [{expected}]. "
        f"Available normalized columns: [{available}]"
    )


def read_structure_csv(csv_path: str, delimiter: str = ";") -> List[LineField]:
    """
    Read a structure CSV file.

    Expected columns, with permissive aliases:
        - nom colonne
        - longueur
        - format
        - start position
    """

    fields = []

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=delimiter)

        if not reader.fieldnames:
            raise ValueError(f"CSV file has no header: {csv_path}")

        headers = {normalize_header(header): header for header in reader.fieldnames}

        name_column = resolve_column(
            headers,
            ["nom colonne", "nom_colonne", "nom", "colonne", "name", "field", "field name"],
        )
        length_column = resolve_column(
            headers,
            ["longueur", "length", "taille", "size"],
        )
        format_column = resolve_column(
            headers,
            ["format", "type", "format (AN / N / A)", "format an n a"],
        )
        start_column = resolve_column(
            headers,
            ["start position", "start", "position", "position debut", "debut"],
        )

        used_names = {}

        for row_number, row in enumerate(reader, start=2):
            original_name = (row.get(name_column) or "").strip()

            if not original_name:
                raise ValueError(f"Empty field name in {csv_path}, row {row_number}")

            name = safe_identifier(original_name)

            if name in used_names:
                used_names[name] += 1
                name = f"{name}_{used_names[name]}"
            else:
                used_names[name] = 1

            try:
                length = int(str(row.get(length_column, "")).strip())
            except ValueError as exc:
                raise ValueError(
                    f"Invalid length for field {original_name!r} in {csv_path}, row {row_number}"
                ) from exc

            field_format = str(row.get(format_column, "")).strip().upper()

            if field_format not in ("AN", "N", "A"):
                raise ValueError(
                    f"Invalid format for field {original_name!r} in {csv_path}, row {row_number}: "
                    f"{field_format!r}. Expected AN, N or A."
                )

            try:
                start = int(str(row.get(start_column, "")).strip())
            except ValueError as exc:
                raise ValueError(
                    f"Invalid start position for field {original_name!r} in {csv_path}, row {row_number}"
                ) from exc

            if length < 1:
                raise ValueError(f"Length must be >= 1 for field {original_name!r}")

            if start < 1:
                raise ValueError(f"Start position must be >= 1 for field {original_name!r}")

            fields.append(LineField(original_name, name, length, field_format, start))

    return fields


def build_source_function_name(line_type: LineTypeSpec, field: LineField) -> str:
    return f"get_{line_type.safe_prefix()}_{field.name}"


def build_qualified_field_name(line_type: LineTypeSpec, field: LineField) -> str:
    return f"{line_type.safe_prefix()}_{field.name}"


def generate_code(spec: GenerationSpec) -> str:
    """Generate a standalone Python module that registers all fields."""

    if not spec.line_types:
        raise ValueError("At least one line type is required")

    parts = []
    parts.append(_render_header(spec))
    parts.append(_render_metadata(spec))
    parts.append(_render_helpers())
    parts.append(_render_source_functions(spec))
    parts.append(_render_source_registry(spec))
    parts.append(_render_next_line_type(spec))
    parts.append(_render_register_all(spec))
    parts.append(_render_build_master())
    parts.append(_render_main_hint())

    return "\n\n".join(part.rstrip() for part in parts) + "\n"


def write_generated_code(spec: GenerationSpec, output_path: str) -> None:
    content = generate_code(spec)
    Path(output_path).write_text(content, encoding="utf-8")


def _render_header(spec: GenerationSpec) -> str:
    return f'''"""
Generated fixed-width file generator skeleton.

This file was generated from {len(spec.line_types)} CSV structure file(s).
Fill the generated get_* functions with the real business extraction logic.
"""

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from fixed_width_generator import SegmentedFlatFileMaster


SourceResult = Tuple[str, Dict[str, Any]]
'''


def _render_metadata(spec: GenerationSpec) -> str:
    line_type_names = [line_type.safe_name() for line_type in spec.line_types]
    next_line_types = {}
    next_count_fields = {}
    next_count_functions = {}

    for index, line_type in enumerate(spec.line_types[:-1]):
        next_type = spec.line_types[index + 1]
        count_field_name = spec.next_count_fields.get(line_type.safe_name())

        if count_field_name:
            field = _find_field_by_name(line_type, count_field_name)
            next_line_types[line_type.safe_name()] = next_type.safe_name()
            next_count_fields[line_type.safe_name()] = build_qualified_field_name(line_type, field)
            next_count_functions[line_type.safe_name()] = build_source_function_name(line_type, field)

    return f'''LOGICAL_LENGTH = {spec.logical_length}
SEGMENT_PAYLOAD_LENGTH = {spec.segment_payload_length}
PHYSICAL_PREFIX_LENGTH = {spec.physical_prefix_length}
LINE_TYPES = {line_type_names!r}
NEXT_LINE_TYPES = {next_line_types!r}
NEXT_COUNT_FIELDS = {next_count_fields!r}
NEXT_COUNT_FUNCTIONS = {next_count_functions!r}
'''


def _render_helpers() -> str:
    return '''def _clean_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _default_value(length: int, field_format: str) -> str:
    if field_format == "N":
        return "0" * length
    return " " * length


def _read_input_value(
    input_record: Dict[str, Any],
    context: Dict[str, Any],
    short_name: str,
    qualified_name: str,
    length: int,
    field_format: str,
) -> str:
    """
    Default generated source behavior.

    Override the generated get_* functions for real business logic.
    This fallback lets you test quickly with dictionaries whose keys match either
    the short CSV field name or the generated qualified name.
    """

    if qualified_name in context:
        value = context.get(qualified_name)
    elif short_name in context:
        value = context.get(short_name)
    elif qualified_name in input_record:
        value = input_record.get(qualified_name)
    elif short_name in input_record:
        value = input_record.get(short_name)
    else:
        return _default_value(length, field_format)

    value = _clean_value(value)

    if value == "":
        return _default_value(length, field_format)

    return value


def _store_value(
    context: Dict[str, Any],
    short_name: str,
    qualified_name: str,
    value: str,
) -> Dict[str, Any]:
    context[qualified_name] = value

    # Convenience alias. If several line types share the same short field name,
    # this contains the last generated line's value.
    context[short_name] = value

    return context


def _to_int(value: Any) -> int:
    text = _clean_value(value).replace(" ", "")

    if text == "":
        return 0

    try:
        return int(text)
    except ValueError:
        raise ValueError(f"Cannot convert value to int: {value!r}")
'''


def _render_source_functions(spec: GenerationSpec) -> str:
    functions = []

    for line_type in spec.line_types:
        for field in line_type.fields:
            function_name = build_source_function_name(line_type, field)
            qualified_name = build_qualified_field_name(line_type, field)
            functions.append(
                f'''def {function_name}(
    input_record: Dict[str, Any],
    context: Dict[str, Any],
) -> SourceResult:
    """TODO: replace generated fallback for CSV column {field.original_name!r}."""

    value = _read_input_value(
        input_record=input_record,
        context=context,
        short_name={field.name!r},
        qualified_name={qualified_name!r},
        length={field.length},
        field_format={field.field_format!r},
    )
    context = _store_value(context, {field.name!r}, {qualified_name!r}, value)
    return value, context
'''
            )

    return "\n\n".join(functions)


def _render_source_registry(spec: GenerationSpec) -> str:
    lines = ["SOURCE_REGISTRY = {"]

    for line_type in spec.line_types:
        for field in line_type.fields:
            function_name = build_source_function_name(line_type, field)
            lines.append(f'    "{function_name}": {function_name},')

    lines.append("}")
    return "\n".join(lines)


def _render_next_line_type(spec: GenerationSpec) -> str:
    root_line_type = spec.line_types[0].safe_name()

    return f'''def _resolve_next_count(
    line_type: str,
    input_record: Dict[str, Any],
    context: Dict[str, Any],
) -> int:
    count_field_name = NEXT_COUNT_FIELDS.get(line_type)
    count_function_name = NEXT_COUNT_FUNCTIONS.get(line_type)

    if not count_field_name or not count_function_name:
        return 0

    if count_field_name in context:
        return _to_int(context.get(count_field_name))

    count_function = SOURCE_REGISTRY[count_function_name]
    value, context = count_function(input_record, context)
    return _to_int(value)


def get_next_line_type(
    input_record: Dict[str, Any],
    context: Dict[str, Any],
) -> Optional[str]:
    """
    Generic generated hierarchy driver.

    It emits the first line type once, then uses the selected numeric fields to
    decide how many child lines must be emitted for each parent line.
    """

    if "_codegen_line_stack" not in context:
        context["_codegen_line_stack"] = [
            {{"line_type": {root_line_type!r}, "count": 1, "next_index": 0}}
        ]
        context["_codegen_pending_children_for"] = None

    stack = context["_codegen_line_stack"]

    while True:
        pending_parent_type = context.get("_codegen_pending_children_for")

        if pending_parent_type is not None:
            context["_codegen_pending_children_for"] = None
            child_type = NEXT_LINE_TYPES.get(pending_parent_type)
            child_count = _resolve_next_count(pending_parent_type, input_record, context)

            if child_type is not None and child_count > 0:
                stack.append({{"line_type": child_type, "count": child_count, "next_index": 0}})

        while stack:
            frame = stack[-1]

            if frame["next_index"] >= frame["count"]:
                stack.pop()
                continue

            frame["next_index"] += 1
            current_line_type = frame["line_type"]
            current_index = frame["next_index"]

            context["_current_line_type"] = current_line_type
            context[f"_current_{{current_line_type.lower()}}_index"] = current_index

            if current_line_type in NEXT_LINE_TYPES:
                context["_codegen_pending_children_for"] = current_line_type

            return current_line_type

        return None
'''


def _render_register_all(spec: GenerationSpec) -> str:
    lines = ["def register_all(master: SegmentedFlatFileMaster) -> None:"]

    for line_type in spec.line_types:
        lines.append(f"    # {line_type.safe_name()} generated from {line_type.csv_path}")

        for field in line_type.fields:
            function_name = build_source_function_name(line_type, field)
            qualified_name = build_qualified_field_name(line_type, field)
            align = "right" if field.is_numeric() else "left"
            pad_char = "0" if field.is_numeric() else " "

            lines.append(
                "    master.register(\n"
                f"        line_type={line_type.safe_name()!r},\n"
                f"        start={field.start},\n"
                f"        length={field.length},\n"
                f"        function_name={function_name!r},\n"
                f"        name={qualified_name!r},\n"
                f"        align={align!r},\n"
                f"        pad_char={pad_char!r},\n"
                "        truncate=True,\n"
                "    )"
            )

    if len(lines) == 1:
        lines.append("    pass")

    return "\n".join(lines)


def _render_build_master() -> str:
    return '''def build_master(generation_date: Optional[date] = None) -> SegmentedFlatFileMaster:
    master = SegmentedFlatFileMaster(
        source_registry=SOURCE_REGISTRY,
        get_next_line_type=get_next_line_type,
        logical_length=LOGICAL_LENGTH,
        segment_payload_length=SEGMENT_PAYLOAD_LENGTH,
        physical_prefix_length=PHYSICAL_PREFIX_LENGTH,
        generation_date=generation_date,
    )
    register_all(master)
    return master
'''


def _render_main_hint() -> str:
    return '''if __name__ == "__main__":
    # Minimal smoke test. Replace this with your real input loading logic.
    master = build_master()
    master.generate(records=[{}], output_path="generated_output.txt")
    print("Generated generated_output.txt")
'''


def _find_field_by_name(line_type: LineTypeSpec, field_name: str) -> LineField:
    normalized = safe_identifier(field_name)

    for field in line_type.fields:
        if field.name == normalized:
            return field

    available = ", ".join(field.name for field in line_type.fields)
    raise ValueError(
        f"Cannot find field {field_name!r} in line type {line_type.safe_name()}. "
        f"Available fields: {available}"
    )
