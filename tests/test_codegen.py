import py_compile
from pathlib import Path

from fixed_width_generator.codegen import (
    GenerationSpec,
    LineTypeSpec,
    read_structure_csv,
    safe_identifier,
    write_generated_code,
)


def test_safe_identifier_removes_accents_and_invalid_chars():
    assert safe_identifier("Nombre de titulaires") == "nombre_de_titulaires"
    assert safe_identifier("2ème nom") == "_2eme_nom"


def test_read_structure_csv_with_expected_columns(tmp_path: Path):
    csv_path = tmp_path / "structure.csv"
    csv_path.write_text(
        "nom colonne;longueur;format;start position\n"
        "Nom Client;30;AN;1\n"
        "Nombre B;2;N;31\n",
        encoding="utf-8",
    )

    fields = read_structure_csv(str(csv_path))

    assert len(fields) == 2
    assert fields[0].name == "nom_client"
    assert fields[0].length == 30
    assert fields[0].field_format == "AN"
    assert fields[0].start == 1
    assert fields[1].is_numeric()


def test_generate_code_wires_next_count_function_and_compiles(tmp_path: Path):
    a_csv = tmp_path / "a.csv"
    b_csv = tmp_path / "b.csv"

    a_csv.write_text(
        "nom colonne;longueur;format;start position\n"
        "Code A;2;AN;1\n"
        "Nombre B;2;N;3\n",
        encoding="utf-8",
    )
    b_csv.write_text(
        "nom colonne;longueur;format;start position\n"
        "Code B;2;AN;1\n",
        encoding="utf-8",
    )

    line_a = LineTypeSpec("A", read_structure_csv(str(a_csv)), str(a_csv))
    line_b = LineTypeSpec("B", read_structure_csv(str(b_csv)), str(b_csv))
    spec = GenerationSpec(
        logical_length=600,
        line_types=[line_a, line_b],
        next_count_fields={"A": "nombre_b"},
    )

    output_path = tmp_path / "generated_flat_file.py"
    write_generated_code(spec, str(output_path))
    generated = output_path.read_text(encoding="utf-8")

    assert "NEXT_LINE_TYPES = {'A': 'B'}" in generated
    assert "NEXT_COUNT_FIELDS = {'A': 'a_nombre_b'}" in generated
    assert "NEXT_COUNT_FUNCTIONS = {'A': 'get_a_nombre_b'}" in generated
    assert "function_name='get_a_nombre_b'" in generated
    assert "line_type='B'" in generated

    py_compile.compile(str(output_path), doraise=True)
