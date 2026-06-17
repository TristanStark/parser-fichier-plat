from typing import Any, Dict, Optional, Tuple


SourceResult = Tuple[str, Dict[str, Any]]


def get_next_line_type_compte_titulaires(
    input_record: Dict[str, Any],
    context: Dict[str, Any],
) -> Optional[str]:
    """
    Example next-line resolver.

    For each source record:
        1. generate one COMPTE logical line
        2. generate one TITULAIRE logical line per holder
        3. return None to move to the next source record
    """

    if not context.get("_compte_line_done"):
        context["_compte_line_done"] = True
        return "COMPTE"

    titulaires = input_record.get("titulaires", [])
    titulaire_index = context.get("_titulaire_index", 0)

    if titulaire_index < len(titulaires):
        context["_current_titulaire"] = titulaires[titulaire_index]
        context["_current_titulaire_number"] = titulaire_index + 1
        context["_titulaire_index"] = titulaire_index + 1
        return "TITULAIRE"

    return None


def get_type_ligne(
    input_record: Dict[str, Any],
    context: Dict[str, Any],
) -> SourceResult:
    return context["_line_type"], context


def get_numero_compte(
    input_record: Dict[str, Any],
    context: Dict[str, Any],
) -> SourceResult:
    numero_compte = input_record.get("numero_compte", "").strip()
    context["numero_compte"] = numero_compte
    return numero_compte, context


def get_libelle_compte(
    input_record: Dict[str, Any],
    context: Dict[str, Any],
) -> SourceResult:
    libelle = input_record.get("libelle_compte", "").strip().upper()
    context["libelle_compte"] = libelle
    return libelle, context


def get_tope_code(
    input_record: Dict[str, Any],
    context: Dict[str, Any],
) -> SourceResult:
    tope_code = input_record.get("tope_code", "").strip().upper()
    context["tope_code"] = tope_code
    return tope_code, context


def get_nom_personne_physique(
    input_record: Dict[str, Any],
    context: Dict[str, Any],
) -> SourceResult:
    nom = input_record.get("nom", "").strip().upper()
    context["nom"] = nom
    return nom, context


def get_raison_sociale_personne_morale(
    input_record: Dict[str, Any],
    context: Dict[str, Any],
) -> SourceResult:
    raison_sociale = input_record.get("raison_sociale", "").strip().upper()
    context["raison_sociale"] = raison_sociale
    return raison_sociale, context


def get_numero_titulaire(
    input_record: Dict[str, Any],
    context: Dict[str, Any],
) -> SourceResult:
    numero = context.get("_current_titulaire_number", 0)
    return str(numero), context


def get_nom_titulaire(
    input_record: Dict[str, Any],
    context: Dict[str, Any],
) -> SourceResult:
    titulaire = context.get("_current_titulaire", {})
    nom = titulaire.get("nom", "").strip().upper()
    context["nom_titulaire"] = nom
    return nom, context


def get_prenom_titulaire(
    input_record: Dict[str, Any],
    context: Dict[str, Any],
) -> SourceResult:
    titulaire = context.get("_current_titulaire", {})
    prenom = titulaire.get("prenom", "").strip().upper()
    context["prenom_titulaire"] = prenom
    return prenom, context


SOURCE_REGISTRY = {
    "get_type_ligne": get_type_ligne,
    "get_numero_compte": get_numero_compte,
    "get_libelle_compte": get_libelle_compte,
    "get_tope_code": get_tope_code,
    "get_nom_personne_physique": get_nom_personne_physique,
    "get_raison_sociale_personne_morale": get_raison_sociale_personne_morale,
    "get_numero_titulaire": get_numero_titulaire,
    "get_nom_titulaire": get_nom_titulaire,
    "get_prenom_titulaire": get_prenom_titulaire,
}
