from datetime import date
import csv
from typing import Any, Dict, List, Optional
from .fixed_width_line_solver import FixedWidthLineSolver
from .conditions import SourceFunction

class SegmentPrefixBuilder:
    """
    Construit le début de ligne physique.

    Format cible de 25 caractères :

        NB2
        + quantième sur 3
        + 100
        + longueur préfixe sur 7 : 0000025
        + 2
        + numéro de ligne global sur 5
        + numéro de segment sur 1
        + SE

    Exemple :
        NB222610000000252000051SE

    Découpage :
        NB2      3
        226      3
        100      3
        0000025  7
        2        1
        00005    5
        1        1
        SE       2
        total   25
    """

    def __init__(
        self,
        prefix_length: int = 25,
        prefix_length_field: str = "0000025",
        file_code: str = "NB2",
        constant_100: str = "100",
        constant_2: str = "2",
        suffix: str = "SE",
    ):
        self.prefix_length = prefix_length
        self.prefix_length_field = prefix_length_field
        self.file_code = file_code
        self.constant_100 = constant_100
        self.constant_2 = constant_2
        self.suffix = suffix

    def build_prefix(
        self,
        global_line_number: int,
        segment_number: int,
        generation_date: date,
    ) -> str:
        day_of_year = generation_date.timetuple().tm_yday

        prefix = (
            self.file_code
            + f"{day_of_year:03d}"
            + self.constant_100
            + self.prefix_length_field
            + self.constant_2
            + f"{global_line_number:05d}"
            + str(segment_number)
            + self.suffix
        )

        if len(prefix) != self.prefix_length:
            raise ValueError(
                f"Préfixe invalide : longueur {len(prefix)}, "
                f"attendu {self.prefix_length}. "
                f"Préfixe généré = {prefix!r}"
            )

        return prefix

class SegmentedFlatFileMaster:
    """
    Classe maître.

    Elle permet de register des champs sur un enregistrement logique de 600 caractères,
    puis elle écrit physiquement 3 lignes de 225 caractères :

        ligne physique 1 = préfixe 25 + caractères 001-200
        ligne physique 2 = préfixe 25 + caractères 201-400
        ligne physique 3 = préfixe 25 + caractères 401-600
    """

    def __init__(
        self,
        source_registry: Dict[str, SourceFunction],
        logical_length: int = 600,
        segment_payload_length: int = 200,
        physical_prefix_length: int = 25,
        encoding: str = "utf-8",
        newline: str = "\n",
        generation_date: Optional[date] = None,
    ):
        if logical_length % segment_payload_length != 0:
            raise ValueError(
                "La longueur logique doit être divisible par la longueur de segment."
            )

        self.logical_length = logical_length
        self.segment_payload_length = segment_payload_length
        self.physical_prefix_length = physical_prefix_length
        self.segment_count = logical_length // segment_payload_length

        self.encoding = encoding
        self.newline = newline
        self.generation_date = generation_date or date.today()

        self.solver = FixedWidthLineSolver(
            logical_length=logical_length,
            source_registry=source_registry,
        )

        self.prefix_builder = SegmentPrefixBuilder(
            prefix_length=physical_prefix_length,
        )

        self.global_line_number = 1

    def register(
        self,
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
        Enregistre un champ sur l'enregistrement LOGIQUE de 600 caractères.

        Exemple :
            master.register(
                start=250,
                length=10,
                function_name="get_code",
            )

        Cette donnée sera écrite dans le segment 2,
        parce que les positions 201-400 correspondent au segment 2.
        """

        self.solver.register(
            start=start,
            length=length,
            function_name=function_name,
            conditions=conditions,
            name=name,
            align=align,
            pad_char=pad_char,
            truncate=truncate,
            required=required,
            priority=priority,
        )

    def generate(
        self,
        records: List[Dict[str, Any]],
        output_path: str,
    ):
        self.global_line_number = 1

        with open(output_path, "w", encoding=self.encoding, newline="") as file:
            for record_index, record in enumerate(records, start=1):
                context = dict(record)
                context["_record_index"] = record_index
                context["_total_records"] = len(records)

                logical_line, final_context = self.solver.build_logical_line(
                    input_record=record,
                    initial_context=context,
                )

                physical_lines = self._split_logical_line_into_physical_lines(
                    logical_line=logical_line,
                    record_index=record_index,
                    context=final_context,
                )

                for physical_line in physical_lines:
                    file.write(physical_line + self.newline)

    def generate_from_csv(
        self,
        input_csv_path: str,
        output_path: str,
        delimiter: str = ";",
    ):
        records = self._read_csv(input_csv_path, delimiter)
        self.generate(records, output_path)

    def _read_csv(
        self,
        input_csv_path: str,
        delimiter: str,
    ) -> List[Dict[str, Any]]:
        with open(input_csv_path, "r", encoding=self.encoding, newline="") as file:
            reader = csv.DictReader(file, delimiter=delimiter)
            return list(reader)

    def _split_logical_line_into_physical_lines(
        self,
        logical_line: str,
        record_index: int,
        context: Dict[str, Any],
    ) -> List[str]:
        if len(logical_line) != self.logical_length:
            raise ValueError(
                f"Ligne logique invalide : longueur {len(logical_line)}, "
                f"attendu {self.logical_length}"
            )

        physical_lines = []

        for segment_number in range(1, self.segment_count + 1):
            start_index = (segment_number - 1) * self.segment_payload_length
            end_index = start_index + self.segment_payload_length

            payload = logical_line[start_index:end_index]

            prefix = self.prefix_builder.build_prefix(
                global_line_number=self.global_line_number,
                segment_number=segment_number,
                generation_date=self.generation_date,
            )

            physical_line = prefix + payload

            expected_physical_length = (
                self.physical_prefix_length + self.segment_payload_length
            )

            if len(physical_line) != expected_physical_length:
                raise ValueError(
                    f"Ligne physique invalide : longueur {len(physical_line)}, "
                    f"attendu {expected_physical_length}"
                )

            physical_lines.append(physical_line)

            self.global_line_number += 1

        return physical_lines