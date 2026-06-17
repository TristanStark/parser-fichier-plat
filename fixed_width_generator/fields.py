from typing import Any, Dict, List, Optional

from .conditions import Condition, normalize_conditions


class RegisteredField:
    """
    Describes one field in one logical line type.

    Several fields may share the same start position. At generation time, the
    solver keeps only fields matching the current line type and their conditions.
    """

    def __init__(
        self,
        line_type: str,
        name: str,
        start: int,
        length: int,
        function_name: str,
        conditions: Optional[List[Any]] = None,
        align: str = "left",
        pad_char: str = " ",
        truncate: bool = False,
        required: bool = False,
        priority: int = 0,
    ):
        self.line_type = line_type
        self.name = name
        self.start = start
        self.length = length
        self.function_name = function_name
        self.conditions = normalize_conditions(conditions)
        self.align = align
        self.pad_char = pad_char
        self.truncate = truncate
        self.required = required
        self.priority = priority

    def matches(
        self,
        current_line_type: str,
        input_record: Dict[str, Any],
        context: Dict[str, Any],
    ) -> bool:
        if self.line_type != current_line_type:
            return False

        for condition in self.conditions:
            if isinstance(condition, Condition):
                if not condition.matches(input_record, context):
                    return False
            elif callable(condition):
                if not condition(input_record, context):
                    return False
            else:
                raise TypeError(
                    f"Invalid condition for {self.line_type}.{self.name}: "
                    f"{condition!r}"
                )

        return True

    def end(self) -> int:
        return self.start + self.length - 1

    def __repr__(self) -> str:
        return (
            f"RegisteredField(line_type={self.line_type!r}, name={self.name!r}, "
            f"start={self.start}, length={self.length}, "
            f"function_name={self.function_name!r})"
        )
