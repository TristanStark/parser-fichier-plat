from datetime import date

from fixed_width_generator import SegmentedFlatFileMaster
from example_sources import (
    SOURCE_REGISTRY,
    get_next_line_type_compte_titulaires,
)


def build_master() -> SegmentedFlatFileMaster:
    master = SegmentedFlatFileMaster(
        source_registry=SOURCE_REGISTRY,
        get_next_line_type=get_next_line_type_compte_titulaires,
        logical_length=600,
        segment_payload_length=200,
        physical_prefix_length=25,
        encoding="utf-8",
        generation_date=date(2026, 8, 14),  # day-of-year = 226
    )

    # COMPTE logical line.
    master.register(
        line_type="COMPTE",
        start=1,
        length=10,
        function_name="get_type_ligne",
        name="type_ligne_compte",
        truncate=True,
    )

    master.register(
        line_type="COMPTE",
        start=11,
        length=20,
        function_name="get_numero_compte",
        name="numero_compte",
        align="right",
        pad_char="0",
    )

    master.register(
        line_type="COMPTE",
        start=31,
        length=40,
        function_name="get_libelle_compte",
        name="libelle_compte",
        truncate=True,
    )

    master.register(
        line_type="COMPTE",
        start=71,
        length=2,
        function_name="get_tope_code",
        name="tope_code",
        required=True,
    )

    # Same position, different source depending on a predicate.
    master.register(
        line_type="COMPTE",
        start=73,
        length=30,
        function_name="get_nom_personne_physique",
        name="nom_personne_physique",
        conditions=["tope_code = MI"],
        truncate=True,
    )

    master.register(
        line_type="COMPTE",
        start=73,
        length=30,
        function_name="get_raison_sociale_personne_morale",
        name="raison_sociale_personne_morale",
        conditions=["tope_code <> MI"],
        truncate=True,
    )

    # TITULAIRE logical line.
    master.register(
        line_type="TITULAIRE",
        start=1,
        length=10,
        function_name="get_type_ligne",
        name="type_ligne_titulaire",
        truncate=True,
    )

    master.register(
        line_type="TITULAIRE",
        start=11,
        length=20,
        function_name="get_numero_compte",
        name="numero_compte_rappel",
        align="right",
        pad_char="0",
    )

    master.register(
        line_type="TITULAIRE",
        start=31,
        length=2,
        function_name="get_numero_titulaire",
        name="numero_titulaire",
        align="right",
        pad_char="0",
    )

    master.register(
        line_type="TITULAIRE",
        start=33,
        length=30,
        function_name="get_nom_titulaire",
        name="nom_titulaire",
        truncate=True,
    )

    master.register(
        line_type="TITULAIRE",
        start=63,
        length=30,
        function_name="get_prenom_titulaire",
        name="prenom_titulaire",
        truncate=True,
    )

    return master


def main():
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
        },
        {
            "numero_compte": "98765",
            "libelle_compte": "Compte entreprise",
            "tope_code": "PM",
            "nom": "",
            "raison_sociale": "ACME Corporation",
            "titulaires": [
                {"nom": "Durand", "prenom": "Paul"},
            ],
        },
    ]

    master = build_master()
    master.generate(records, "output.txt")

    print("Generated output.txt")


if __name__ == "__main__":
    main()
