from datetime import date
from pathlib import Path

from fixed_width_generator.prefix import SegmentPrefixBuilder
from main_example import build_master


def test_prefix_numbering_25_chars():
    builder = SegmentPrefixBuilder(
        prefix_length=25,
        prefix_length_field="0000000",
    )

    generation_date = date(2026, 8, 14)  # day-of-year 226

    assert builder.build_prefix(1, 1, generation_date) == "NB222610000000002000011SE"
    assert builder.build_prefix(2, 2, generation_date) == "NB222610000000002000022SE"
    assert builder.build_prefix(3, 3, generation_date) == "NB222610000000002000033SE"

    assert builder.build_prefix(4, 1, generation_date) == "NB222610000000002000041SE"
    assert builder.build_prefix(5, 2, generation_date) == "NB222610000000002000052SE"
    assert builder.build_prefix(6, 3, generation_date) == "NB222610000000002000063SE"


def test_prefix_numbering_with_custom_reference_field():
    builder = SegmentPrefixBuilder(
        prefix_length=26,
        prefix_length_field="00000000",
    )

    generation_date = date(2026, 8, 14)

    assert builder.build_prefix(4, 1, generation_date) == "NB2226100000000002000041SE"
    assert builder.build_prefix(5, 2, generation_date) == "NB2226100000000002000052SE"
    assert builder.build_prefix(6, 3, generation_date) == "NB2226100000000002000063SE"


def test_one_source_record_can_generate_several_logical_lines():
    master = build_master()

    record = {
        "numero_compte": "12345",
        "libelle_compte": "Compte principal",
        "tope_code": "MI",
        "nom": "Dupont",
        "raison_sociale": "",
        "titulaires": [
            {"nom": "Dupont", "prenom": "Jean"},
            {"nom": "Martin", "prenom": "Alice"},
        ],
    }

    physical_lines = master.build_physical_lines_for_record(record)

    # One COMPTE logical line + two TITULAIRE logical lines.
    # Each logical line of 600 chars is split into 3 physical lines.
    assert len(physical_lines) == 9

    for line in physical_lines:
        assert len(line) == 225

    assert physical_lines[0].startswith("NB222610000000002000011SE")
    assert physical_lines[1].startswith("NB222610000000002000022SE")
    assert physical_lines[2].startswith("NB222610000000002000033SE")

    assert physical_lines[3].startswith("NB222610000000002000041SE")
    assert physical_lines[4].startswith("NB222610000000002000052SE")
    assert physical_lines[5].startswith("NB222610000000002000063SE")

    assert physical_lines[6].startswith("NB222610000000002000071SE")
    assert physical_lines[7].startswith("NB222610000000002000082SE")
    assert physical_lines[8].startswith("NB222610000000002000093SE")


def test_generate_file(tmp_path: Path):
    master = build_master()

    records = [
        {
            "numero_compte": "12345",
            "libelle_compte": "Compte principal",
            "tope_code": "MI",
            "nom": "Dupont",
            "raison_sociale": "",
            "titulaires": [
                {"nom": "Dupont", "prenom": "Jean"},
                {"nom": "Martin", "prenom": "Alice"},
            ],
        }
    ]

    output_path = tmp_path / "output.txt"

    master.generate(records, str(output_path))

    lines = output_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 9
    assert all(len(line) == 225 for line in lines)
