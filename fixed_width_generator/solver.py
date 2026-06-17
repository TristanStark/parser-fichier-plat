from typing import Any, Dict, List, Optional, Tuple

from .common import SourceFunction
from .fields import RegisteredField


class FixedWidthLineSolver:
    """
    Builds a complete logical fixed-width line.

    In the BRN-like use case:
        logical_length = 600

    You register fields against positions 1..600 and a line_type.
    The master generator will later split this 600-character logical line into
    physical lines.
    """

    def __init__(
        self,
        logical_length: int,
        source_registry: Dict[str, SourceFunction],
        filler: str = " ",
        strict_multiple_match: bool = True,
    ):
        if logical_length < 1:
            raise ValueError("logical_length must be greater than zero")

        if len(filler) != 1:
            raise ValueError("filler must be exactly one character")

        self.logical_length = logical_length
        self.source_registry = source_registry
        self.filler = filler
        self.strict_multiple_match = strict_multiple_match
        self.fields_by_start: Dict[int, List[RegisteredField]] = {}

    def register(
        self,
        line_type: str,
        start: int,
        length: int,
        function_name: str,
        conditions: Optional[List[Any]] = None,
        name: Optional[str] = None,
        align: str = "left",
        pad_char: str = " ",
        truncate: bool = False,
        required: bool = False,
        priority: int = 0,
    ):
        """
        Register one fixed-width field for a given logical line type.

        Args:
            line_type: Type of logical line, for example "COMPTE" or "TITULAIRE".
            start: 1-based position in the logical line.
            length: Field length.
            function_name: Name of the source function in source_registry.
            conditions: Optional conditions, such as ["tope_code = MI"].
            name: Technical field name used in context and error messages.
            align: "left" or "right".
            pad_char: Padding character.
            truncate: Whether too-long values should be cut instead of raising.
            required: Whether an empty value is an error.
            priority: Used when multiple fields match at the same position.
        """

        if name is None:
            name = function_name

        if not line_type:
            raise ValueError(f"line_type is required for {name}")

        if start < 1:
            raise ValueError(f"Invalid start for {line_type}.{name}: {start}")

        if length < 1:
            raise ValueError(f"Invalid length for {line_type}.{name}: {length}")

        end = start + length - 1

        if end > self.logical_length:
            raise ValueError(
                f"Field {line_type}.{name} exceeds logical length: "
                f"{end} > {self.logical_length}"
            )

        if function_name not in self.source_registry:
            raise ValueError(f"Unknown source function: {function_name}")

        field = RegisteredField(
            line_type=line_type,
            name=name,
            start=start,
            length=length,
            function_name=function_name,
            conditions=conditions,
            align=align,
            pad_char=pad_char,
            truncate=truncate,
            required=required,
            priority=priority,
        )

        self.fields_by_start.setdefault(start, []).append(field)

    def build_logical_line(
        self,
        input_record: Dict[str, Any],
        line_type: str,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build one logical line of the requested type.

        Returns:
            tuple(logical_line, updated_context)
        """

        if initial_context is None:
            context = dict(input_record)
        else:
            context = dict(initial_context)

        context["_line_type"] = line_type

        buffer = [self.filler] * self.logical_length
        written_by: Dict[int, str] = {}

        position = 1

        while position <= self.logical_length:
            candidates = self.fields_by_start.get(position, [])

            if not candidates:
                position += 1
                continue

            matching_fields = []

            for field in candidates:
                if field.matches(line_type, input_record, context):
                    matching_fields.append(field)

            if not matching_fields:
                position += 1
                continue

            selected_field = self._select_field(position, matching_fields)

            source_func = self.source_registry[selected_field.function_name]
            raw_value, context = source_func(input_record, context)

            formatted_value = self._format_value(raw_value, selected_field)

            self._write_value(
                buffer=buffer,
                written_by=written_by,
                field=selected_field,
                value=formatted_value,
            )

            context[selected_field.name] = formatted_value

            position = selected_field.start + selected_field.length

        return "".join(buffer), context

    def _select_field(
        self,
        position: int,
        matching_fields: List[RegisteredField],
    ) -> RegisteredField:
        if len(matching_fields) == 1:
            return matching_fields[0]

        sorted_fields = sorted(
            matching_fields,
            key=lambda field: field.priority,
            reverse=True,
        )

        best = sorted_fields[0]
        second = sorted_fields[1]

        if best.priority > second.priority:
            return best

        if self.strict_multiple_match:
            names = [
                f"{field.line_type}.{field.name}"
                for field in matching_fields
            ]
            raise ValueError(
                f"Several fields match at position {position}: {names}. "
                "Add more precise conditions or different priorities."
            )

        return best

    def _format_value(self, value: Any, field: RegisteredField) -> str:
        if value is None:
            value = ""

        value = str(value)

        if field.required and value == "":
            raise ValueError(f"Required field is empty: {field.line_type}.{field.name}")

        if len(value) > field.length:
            if field.truncate:
                value = value[:field.length]
            else:
                raise ValueError(
                    f"Value too long for {field.line_type}.{field.name}: "
                    f"{value!r} is {len(value)} chars, expected {field.length}"
                )

        missing = field.length - len(value)

        if len(field.pad_char) != 1:
            raise ValueError(
                f"pad_char must be exactly one character for "
                f"{field.line_type}.{field.name}"
            )

        if field.align == "left":
            return value + (field.pad_char * missing)

        if field.align == "right":
            return (field.pad_char * missing) + value

        raise ValueError(
            f"Invalid alignment for {field.line_type}.{field.name}: {field.align}"
        )

    def _write_value(
        self,
        buffer: List[str],
        written_by: Dict[int, str],
        field: RegisteredField,
        value: str,
    ):
        for offset, char in enumerate(value):
            position = field.start + offset

            if position in written_by:
                raise ValueError(
                    f"Runtime collision at position {position}: "
                    f"{field.line_type}.{field.name} tries to write over "
                    f"{written_by[position]}"
                )

            buffer[position - 1] = char
            written_by[position] = f"{field.line_type}.{field.name}"
