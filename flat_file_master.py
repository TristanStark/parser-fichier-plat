from typing import Any, Dict, List, Optional
from .conditions import SourceFunction
from .fixed_width_line_solver import FixedWidthLineSolver

class FlatFileMaster:
    """
    Classe maître.

    Elle possède :
        - un solveur pour l'entête
        - un solveur pour les lignes détail
        - une méthode register_header(...)
        - une méthode register_detail(...)
        - une méthode generate(...)
    """

    def __init__(
        self,
        source_registry: Dict[str, SourceFunction],
        header_length: int,
        detail_length: int,
        encoding: str = "utf-8",
        newline: str = "\n",
    ):
        self.source_registry = source_registry
        self.header_solver = FixedWidthLineSolver(
            line_length=header_length,
            source_registry=source_registry,
        )
        self.detail_solver = FixedWidthLineSolver(
            line_length=detail_length,
            source_registry=source_registry,
        )
        self.encoding = encoding
        self.newline = newline

    def register_header(
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
        self.header_solver.register(
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

    def register_detail(
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
        self.detail_solver.register(
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

    def generate(
        self,
        records: List[Dict[str, Any]],
        output_path: str,
    ):
        header_record = self._build_header_record(records)

        with open(output_path, "w", encoding=self.encoding, newline="") as file:
            header_line, header_context = self.header_solver.build_line(
                input_record=header_record,
                initial_context=header_record,
            )

            file.write(header_line + self.newline)

            for index, record in enumerate(records, start=1):
                context = dict(record)
                context["_line_number"] = index
                context["_total_records"] = len(records)
                context["_header"] = header_context

                detail_line, detail_context = self.detail_solver.build_line(
                    input_record=record,
                    initial_context=context,
                )

                file.write(detail_line + self.newline)

    def _build_header_record(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "type_ligne": "H",
            "total_records": len(records),
            "file_code": "BRN",
        }