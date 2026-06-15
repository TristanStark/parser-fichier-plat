from typing import Any, Dict, List, Optional, Tuple
from .conditions import RegisteredField, normalize_conditions, SourceResult, SourceFunction


class FixedWidthLineSolver:
    """
    Solveur de ligne plate.

    Il avance caractère par caractère.
    À chaque position :
        - il cherche les champs enregistrés à cette position
        - il filtre selon les conditions
        - il choisit le champ applicable
        - il appelle sa fonction source
        - il écrit la donnée
        - il avance à la position suivante après le champ
    """

    def __init__(
        self,
        line_length: int,
        source_registry: Dict[str, SourceFunction],
        filler: str = " ",
        strict_multiple_match: bool = True,
    ):
        self.line_length = line_length
        self.source_registry = source_registry
        self.filler = filler
        self.strict_multiple_match = strict_multiple_match
        self.fields_by_start = {}

    def register(
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
        if start < 1:
            raise ValueError(f"Position invalide pour {name}: {start}")

        if length < 1:
            raise ValueError(f"Longueur invalide pour {name}: {length}")

        if start + length - 1 > self.line_length:
            raise ValueError(
                f"Le champ {name} dépasse la longueur de ligne : "
                f"{start + length - 1} > {self.line_length}"
            )

        if function_name not in self.source_registry:
            raise ValueError(f"Fonction source inconnue : {function_name}")

        field = RegisteredField(
            name=name,
            start=start,
            length=length,
            function_name=function_name,
            conditions=normalize_conditions(conditions),
            align=align,
            pad_char=pad_char,
            truncate=truncate,
            required=required,
            priority=priority,
        )

        self.fields_by_start.setdefault(start, []).append(field)

    def build_line(
        self,
        input_record: Dict[str, Any],
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        if initial_context is None:
            context = dict(input_record)
        else:
            context = dict(initial_context)

        buffer = [self.filler] * self.line_length
        written_by = {}

        position = 1

        while position <= self.line_length:
            candidates = self.fields_by_start.get(position, [])

            if not candidates:
                position += 1
                continue

            matching_fields = []

            for field in candidates:
                if field.matches(input_record, context):
                    matching_fields.append(field)

            if not matching_fields:
                # Aucun champ applicable à cette position.
                # On laisse blanc et on avance d'un caractère.
                position += 1
                continue

            selected_field = self._select_field(position, matching_fields)

            raw_value, context = self._call_source_function(
                selected_field,
                input_record,
                context,
            )

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
            names = [field.name for field in matching_fields]
            raise ValueError(
                f"Plusieurs champs matchent à la position {position}: {names}. "
                "Ajoute des conditions plus précises ou une priorité différente."
            )

        return best

    def _call_source_function(
        self,
        field: RegisteredField,
        input_record: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SourceResult:
        source_func = self.source_registry[field.function_name]
        return source_func(input_record, context)

    def _format_value(self, value: Any, field: RegisteredField) -> str:
        if value is None:
            value = ""

        value = str(value)

        if field.required and value == "":
            raise ValueError(f"Champ obligatoire vide : {field.name}")

        if len(value) > field.length:
            if field.truncate:
                value = value[:field.length]
            else:
                raise ValueError(
                    f"Valeur trop longue pour {field.name}: "
                    f"{value!r} fait {len(value)} caractères, "
                    f"longueur attendue = {field.length}"
                )

        missing = field.length - len(value)

        if field.align == "left":
            return value + (field.pad_char * missing)

        if field.align == "right":
            return (field.pad_char * missing) + value

        raise ValueError(f"Alignement invalide : {field.align}")

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
                    f"Collision runtime à la position {position}: "
                    f"{field.name} tente d'écrire sur {written_by[position]}"
                )

            buffer[position - 1] = char
            written_by[position] = field.name