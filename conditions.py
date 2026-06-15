from typing import Any, Callable, Dict, List, Optional, Tuple


SourceResult = Tuple[str, Dict[str, Any]]
SourceFunction = Callable[[Dict[str, Any], Dict[str, Any]], SourceResult]
PredicateFunction = Callable[[Dict[str, Any], Dict[str, Any]], bool]


class Condition:
    """
    Condition simple du type :
        tope_code = MI
        tope_code <> MI
        type_ligne != HEADER

    La condition est évaluée d'abord sur le contexte,
    puis sur l'enregistrement d'entrée.
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

        raise ValueError(f"Opérateur non supporté : {self.operator}")

    def __repr__(self):
        return f"Condition({self.field_name} {self.operator} {self.expected_value})"


class RegisteredField:
    """
    Champ enregistré dans le solveur.

    Plusieurs RegisteredField peuvent avoir la même position de départ.
    Le solveur choisit celui dont les conditions matchent.
    """

    def __init__(
        self,
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
        self.name = name
        self.start = start
        self.length = length
        self.function_name = function_name
        self.conditions = conditions or []
        self.align = align
        self.pad_char = pad_char
        self.truncate = truncate
        self.required = required
        self.priority = priority

    def matches(self, input_record: Dict[str, Any], context: Dict[str, Any]) -> bool:
        for condition in self.conditions:
            if isinstance(condition, Condition):
                if not condition.matches(input_record, context):
                    return False

            elif callable(condition):
                if not condition(input_record, context):
                    return False

            else:
                raise TypeError(
                    f"Condition invalide pour le champ {self.name}: {condition!r}"
                )

        return True

    def end(self) -> int:
        return self.start + self.length - 1

    def __repr__(self):
        return (
            f"RegisteredField(name={self.name!r}, start={self.start}, "
            f"length={self.length}, function_name={self.function_name!r}, "
            f"conditions={self.conditions!r})"
        )

def parse_condition(expression: str) -> Condition:
    """
    Convertit une expression texte simple en Condition.

    Supporté :
        champ = valeur
        champ == valeur
        champ != valeur
        champ <> valeur
    """

    operators = ["<>", "!=", "==", "="]

    for operator in operators:
        if operator in expression:
            left, right = expression.split(operator, 1)

            field_name = left.strip()
            expected_value = right.strip()

            return Condition(field_name, operator, expected_value)

    raise ValueError(f"Condition impossible à parser : {expression!r}")


def normalize_conditions(conditions: Optional[List[Any]]) -> List[Any]:
    if not conditions:
        return []

    normalized = []

    for condition in conditions:
        if isinstance(condition, str):
            normalized.append(parse_condition(condition))
        else:
            normalized.append(condition)

    return normalized