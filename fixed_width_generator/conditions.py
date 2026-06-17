from typing import Any, Dict, List, Optional


class Condition:
    """
    Simple condition used by registered fields.

    Supported textual expressions:
        field = value
        field == value
        field != value
        field <> value

    Values are read first from the runtime context, then from the input record.
    """

    def __init__(self, field_name: str, operator: str, expected_value: Any):
        self.field_name = field_name
        self.operator = operator
        self.expected_value = expected_value

    def matches(self, input_record: Dict[str, Any], context: Dict[str, Any]) -> bool:
        if self.field_name in context:
            actual_value = context.get(self.field_name)
        else:
            actual_value = input_record.get(self.field_name)

        actual_value = "" if actual_value is None else str(actual_value)
        expected_value = "" if self.expected_value is None else str(self.expected_value)

        if self.operator in ("=", "=="):
            return actual_value == expected_value

        if self.operator in ("!=", "<>"):
            return actual_value != expected_value

        raise ValueError(f"Unsupported operator: {self.operator}")

    def __repr__(self) -> str:
        return f"Condition({self.field_name} {self.operator} {self.expected_value})"


def parse_condition(expression: str) -> Condition:
    """
    Parse a simple textual condition.

    Examples:
        "tope_code = MI"
        "tope_code <> MI"
    """

    operators = ["<>", "!=", "==", "="]

    for operator in operators:
        if operator in expression:
            left, right = expression.split(operator, 1)
            return Condition(left.strip(), operator, right.strip())

    raise ValueError(f"Cannot parse condition: {expression!r}")


def normalize_conditions(conditions: Optional[List[Any]]) -> List[Any]:
    """
    Convert string conditions to Condition instances.

    Callable predicates are preserved as-is.
    """

    if not conditions:
        return []

    result = []

    for condition in conditions:
        if isinstance(condition, str):
            result.append(parse_condition(condition))
        else:
            result.append(condition)

    return result
