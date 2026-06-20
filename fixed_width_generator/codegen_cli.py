import argparse
from pathlib import Path
from typing import Dict, List

from .codegen import GenerationSpec, LineTypeSpec, read_structure_csv, write_generated_code


def ask_int(prompt: str, minimum: int = 1, default=None) -> int:
    while True:
        suffix = f" [{default}]" if default is not None else ""
        raw = input(f"{prompt}{suffix}: ").strip()

        if raw == "" and default is not None:
            value = int(default)
        else:
            try:
                value = int(raw)
            except ValueError:
                print("Veuillez saisir un nombre entier.")
                continue

        if value < minimum:
            print(f"La valeur doit être >= {minimum}.")
            continue

        return value


def ask_text(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    raw = input(f"{prompt}{suffix}: ").strip()
    return raw or default


def ask_csv_path(line_type_name: str) -> str:
    while True:
        raw_path = ask_text(f"Chemin du CSV décrivant la ligne {line_type_name}")
        path = Path(raw_path)

        if path.is_file():
            return str(path)

        print(f"Fichier introuvable: {raw_path}")


def choose_next_count_field(line_type: LineTypeSpec, next_line_type: LineTypeSpec) -> str:
    numeric_fields = line_type.numeric_fields()

    if not numeric_fields:
        raise ValueError(
            f"Aucune variable numérique trouvée dans {line_type.safe_name()} pour piloter "
            f"le nombre de lignes {next_line_type.safe_name()}."
        )

    print()
    print(
        f"Variables NUMERIQUES de {line_type.safe_name()} pouvant piloter "
        f"le nombre de lignes {next_line_type.safe_name()} :"
    )

    for index, field in enumerate(numeric_fields, start=1):
        print(
            f"  {index}. {field.original_name} "
            f"-> {field.name} (start={field.start}, length={field.length})"
        )

    choice = ask_int(
        f"Numéro de la variable indiquant combien de {next_line_type.safe_name()} générer",
        minimum=1,
    )

    if choice > len(numeric_fields):
        raise ValueError(f"Choix invalide: {choice}")

    return numeric_fields[choice - 1].name


def collect_spec_interactively(args) -> GenerationSpec:
    logical_length = args.line_length or ask_int("Longueur logique X de chaque ligne", default=600)
    segment_payload_length = args.segment_payload_length
    physical_prefix_length = args.physical_prefix_length

    line_type_count = args.line_type_count or ask_int("Nombre de types de lignes différents")
    line_types: List[LineTypeSpec] = []
    next_count_fields: Dict[str, str] = {}

    for index in range(line_type_count):
        default_name = chr(ord("A") + index) if index < 26 else f"TYPE_{index + 1}"
        line_type_name = ask_text(f"Nom du type de ligne #{index + 1}", default=default_name)
        csv_path = ask_csv_path(line_type_name)
        fields = read_structure_csv(csv_path)
        line_types.append(LineTypeSpec(line_type_name, fields, csv_path))

        if index > 0:
            previous = line_types[index - 1]
            current = line_types[index]
            next_count_fields[previous.safe_name()] = choose_next_count_field(previous, current)

    return GenerationSpec(
        logical_length=logical_length,
        segment_payload_length=segment_payload_length,
        physical_prefix_length=physical_prefix_length,
        line_types=line_types,
        next_count_fields=next_count_fields,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Python fixed-width generator code from structure CSV files."
    )
    parser.add_argument(
        "-o",
        "--output",
        default="generated_flat_file.py",
        help="Generated Python file path. Default: generated_flat_file.py",
    )
    parser.add_argument(
        "--line-length",
        type=int,
        default=None,
        help="Logical line length X. If omitted, the CLI asks interactively.",
    )
    parser.add_argument(
        "--line-type-count",
        type=int,
        default=None,
        help="Number of logical line types. If omitted, the CLI asks interactively.",
    )
    parser.add_argument(
        "--segment-payload-length",
        type=int,
        default=200,
        help="Payload length per physical segment. Default: 200.",
    )
    parser.add_argument(
        "--physical-prefix-length",
        type=int,
        default=25,
        help="Physical prefix length. Default: 25.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    spec = collect_spec_interactively(args)
    write_generated_code(spec, args.output)

    print()
    print(f"Code généré dans: {args.output}")
    print("Tu peux maintenant remplir les fonctions get_* générées avec la vraie logique métier.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
