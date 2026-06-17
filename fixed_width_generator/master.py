import csv
from datetime import date
from typing import Any, Dict, List, Optional

from .common import NextLineTypeFunction, SourceFunction
from .prefix import SegmentPrefixBuilder
from .solver import FixedWidthLineSolver


class SegmentedFlatFileMaster:
    """
    Master generator.

    A source record may generate several logical lines.

    Example:
        one source record
          -> logical line type COMPTE, 600 chars
          -> logical line type TITULAIRE, 600 chars
          -> logical line type TITULAIRE, 600 chars
          -> None means next source record

    Each logical line is then split into physical lines:

        600 chars = 3 payload segments of 200 chars

        physical line = prefix of 25 chars + payload of 200 chars
        physical line length = 225 chars
    """

    def __init__(
        self,
        source_registry: Dict[str, SourceFunction],
        get_next_line_type: NextLineTypeFunction,
        logical_length: int = 600,
        segment_payload_length: int = 200,
        physical_prefix_length: int = 25,
        encoding: str = "utf-8",
        newline: str = "\n",
        generation_date: Optional[date] = None,
        max_logical_lines_per_record: int = 100,
        filler: str = " ",
        strict_multiple_match: bool = True,
    ):
        if logical_length % segment_payload_length != 0:
            raise ValueError(
                "logical_length must be divisible by segment_payload_length"
            )

        self.source_registry = source_registry
        self.get_next_line_type = get_next_line_type

        self.logical_length = logical_length
        self.segment_payload_length = segment_payload_length
        self.physical_prefix_length = physical_prefix_length
        self.segment_count = logical_length // segment_payload_length

        self.encoding = encoding
        self.newline = newline
        self.generation_date = generation_date or date.today()
        self.max_logical_lines_per_record = max_logical_lines_per_record

        self.solver = FixedWidthLineSolver(
            logical_length=logical_length,
            source_registry=source_registry,
            filler=filler,
            strict_multiple_match=strict_multiple_match,
        )

        self.prefix_builder = SegmentPrefixBuilder(
            prefix_length=physical_prefix_length,
        )

        self.global_physical_line_number = 1

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
        Register a field on the 600-character logical line.

        Args:
            line_type: Logical line type, e.g. "COMPTE" or "TITULAIRE".
            start: 1-based position inside the 600-character logical line.
            length: Field length.
            function_name: Source function name.
            conditions: Optional field conditions, e.g. ["tope_code = MI"].
        """

        self.solver.register(
            line_type=line_type,
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
        """
        Generate the output file from a list of input dictionaries.
        """

        self.global_physical_line_number = 1

        with open(output_path, "w", encoding=self.encoding, newline="") as file:
            for source_record_index, record in enumerate(records, start=1):
                context = dict(record)
                context["_source_record_index"] = source_record_index
                context["_total_source_records"] = len(records)
                context["_logical_line_index_for_source_record"] = 0

                safety_counter = 0

                while True:
                    safety_counter += 1

                    if safety_counter > self.max_logical_lines_per_record:
                        raise RuntimeError(
                            f"Too many logical lines generated for source record "
                            f"{source_record_index}. "
                            f"Probable infinite loop in get_next_line_type()."
                        )

                    line_type = self.get_next_line_type(record, context)

                    if line_type is None:
                        break

                    context["_line_type"] = line_type
                    context["_logical_line_index_for_source_record"] += 1

                    logical_line, context = self.solver.build_logical_line(
                        input_record=record,
                        line_type=line_type,
                        initial_context=context,
                    )

                    physical_lines = self._split_logical_line_into_physical_lines(
                        logical_line=logical_line,
                        line_type=line_type,
                        context=context,
                    )

                    for physical_line in physical_lines:
                        file.write(physical_line + self.newline)

    def generate_from_csv(
        self,
        input_csv_path: str,
        output_path: str,
        delimiter: str = ";",
    ):
        """
        Generate from a flat CSV file.

        For nested use cases, such as one account with several holders, loading
        records from JSON is often easier than CSV. CSV support is kept as a
        convenience for simpler input records.
        """

        records = self._read_csv(input_csv_path, delimiter)
        self.generate(records, output_path)

    def build_physical_lines_for_record(
        self,
        record: Dict[str, Any],
        source_record_index: int = 1,
    ) -> List[str]:
        """
        Utility method useful for tests.

        It builds all physical lines for a single source record without writing
        a file. It still updates the global physical line counter.
        """

        context = dict(record)
        context["_source_record_index"] = source_record_index
        context["_total_source_records"] = 1
        context["_logical_line_index_for_source_record"] = 0

        output_lines = []
        safety_counter = 0

        while True:
            safety_counter += 1

            if safety_counter > self.max_logical_lines_per_record:
                raise RuntimeError(
                    "Too many logical lines generated for source record. "
                    "Probable infinite loop in get_next_line_type()."
                )

            line_type = self.get_next_line_type(record, context)

            if line_type is None:
                break

            context["_line_type"] = line_type
            context["_logical_line_index_for_source_record"] += 1

            logical_line, context = self.solver.build_logical_line(
                input_record=record,
                line_type=line_type,
                initial_context=context,
            )

            output_lines.extend(
                self._split_logical_line_into_physical_lines(
                    logical_line=logical_line,
                    line_type=line_type,
                    context=context,
                )
            )

        return output_lines

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
        line_type: str,
        context: Dict[str, Any],
    ) -> List[str]:
        if len(logical_line) != self.logical_length:
            raise ValueError(
                f"Invalid logical line for {line_type}: "
                f"length {len(logical_line)}, expected {self.logical_length}"
            )

        physical_lines = []

        for segment_number in range(1, self.segment_count + 1):
            start_index = (segment_number - 1) * self.segment_payload_length
            end_index = start_index + self.segment_payload_length

            payload = logical_line[start_index:end_index]

            prefix = self.prefix_builder.build_prefix(
                global_line_number=self.global_physical_line_number,
                segment_number=segment_number,
                generation_date=self.generation_date,
            )

            physical_line = prefix + payload

            expected_length = self.physical_prefix_length + self.segment_payload_length

            if len(physical_line) != expected_length:
                raise ValueError(
                    f"Invalid physical line for {line_type}: "
                    f"length {len(physical_line)}, expected {expected_length}"
                )

            physical_lines.append(physical_line)

            self.global_physical_line_number += 1

        return physical_lines
