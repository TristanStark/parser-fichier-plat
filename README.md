# Fixed Width Segmented Generator

Petit squelette Python **sans dataclasses** pour générer des fichiers plats à largeur fixe.

## Ce que fait le projet

Le générateur permet de :

- créer des enregistrements logiques de **600 caractères** ;
- enregistrer des champs avec `register(line_type, start, length, function_name, conditions)` ;
- utiliser des fonctions source au format :

```python
def ma_source(input_record, context):
    return valeur_a_ecrire, context
```

- partager un dictionnaire `context` entre les champs ;
- appliquer des conditions du type :

```python
conditions=["tope_code = MI"]
conditions=["tope_code <> MI"]
```

- produire plusieurs lignes logiques pour un même enregistrement source :

```text
record source
  -> ligne logique COMPTE
  -> ligne logique TITULAIRE
  -> ligne logique TITULAIRE
  -> None => record source suivant
```

- découper chaque ligne logique de 600 caractères en **3 lignes physiques** :

```text
ligne physique = préfixe 25 + segment 200 = 225 caractères
```

## Structure du projet

```text
fixed_width_segmented_generator/
  fixed_width_generator/
    __init__.py
    codegen.py
    codegen_cli.py
    common.py
    conditions.py
    fields.py
    master.py
    prefix.py
    solver.py
  example_sources.py
  main_example.py
  tests/
    test_codegen.py
    test_prefix_and_generation.py
  .github/
    workflows/
      ci.yml
      release.yml
  README.md
```

## Générateur de code depuis CSV

Le module `fixed_width_generator.codegen_cli` génère un fichier Python prêt à compléter à partir de plusieurs fichiers CSV de structure.

Chaque CSV doit contenir les colonnes suivantes, séparées par `;` :

```csv
nom colonne;longueur;format;start position
Code ligne;2;AN;1
Nombre titulaires;2;N;3
Nom;30;AN;5
```

Formats supportés :

- `AN` : alphanumérique ;
- `A` : alphabétique / texte ;
- `N` : numérique, aligné à droite et paddé avec des zéros dans le code généré.

Lancement interactif :

```bash
python -m fixed_width_generator.codegen_cli
```

Avec quelques paramètres déjà renseignés :

```bash
python -m fixed_width_generator.codegen_cli \
  --line-length 600 \
  --line-type-count 3 \
  --output generated_bordereau.py
```

Le CLI demande ensuite, pour chaque type de ligne :

1. le nom du type de ligne, par exemple `A`, `B`, `C`, `COMPTE`, `TITULAIRE` ;
2. le chemin vers le CSV décrivant sa structure ;
3. s'il existe un type de ligne suivant, la variable numérique du type courant qui indique combien de lignes du type suivant doivent être générées.

Exemple :

```text
A -> contient Nombre B
B -> contient Nombre C
C -> dernier type
```

Le générateur produit automatiquement :

- les fonctions `get_*` à remplir avec la vraie logique métier ;
- le `SOURCE_REGISTRY` ;
- la fonction générique `get_next_line_type(input_record, context)` ;
- les appels `master.register(...)` pour tous les champs de tous les types de lignes ;
- le `build_master(...)` prêt à utiliser.

Les fonctions générées sont préfixées par type de ligne pour éviter les collisions :

```python
get_a_nom(...)
get_b_nom(...)
get_compte_numero_compte(...)
get_titulaire_nom(...)
```

Par défaut, les fonctions générées lisent soit la clé courte (`nom`), soit la clé qualifiée (`a_nom`, `titulaire_nom`) dans `input_record` ou `context`. Tu peux donc tester vite avec un dictionnaire, puis remplacer les fonctions par ta vraie logique.

## Exemple de code généré

Le fichier généré contient une fonction de ce type :

```python
def build_master(generation_date=None):
    master = SegmentedFlatFileMaster(
        source_registry=SOURCE_REGISTRY,
        get_next_line_type=get_next_line_type,
        logical_length=LOGICAL_LENGTH,
        segment_payload_length=SEGMENT_PAYLOAD_LENGTH,
        physical_prefix_length=PHYSICAL_PREFIX_LENGTH,
        generation_date=generation_date,
    )
    register_all(master)
    return master
```

Tu peux ensuite faire :

```python
from generated_bordereau import build_master

master = build_master()
master.generate(records=[mon_record], output_path="output.txt")
```

## Préfixe physique

Format par défaut, 25 caractères :

```text
NB2 + quantième + 100 + 0000025 + 2 + numéro ligne globale sur 5 + segment 1/2/3 + SE
```

Exemple au quantième 226 :

```text
NB222610000000252000041SE
```

Ici :

```text
00004 = 4e ligne physique globale du fichier
1     = segment 1 de la ligne logique courante
```

Donc pour le deuxième enregistrement logique, on a bien :

```text
NB222610000000252000041SE
NB222610000000252000052SE
NB222610000000252000063SE
```

et non :

```text
NB222610000000252000044SE
NB222610000000252000055SE
NB222610000000252000066SE
```

## Attention sur `00000025`

Si la spec impose vraiment le champ littéral `00000025`, le préfixe fait 26 caractères :

```text
NB2      3
226      3
100      3
00000025 8
2        1
00004    5
1        1
SE       2
TOTAL   26
```

Dans ce cas, configure :

```python
from fixed_width_generator import SegmentPrefixBuilder

master.prefix_builder = SegmentPrefixBuilder(
    prefix_length=26,
    prefix_length_field="00000025",
)
```

Mais la ligne physique fera alors :

```text
26 + 200 = 226 caractères
```

## Lancer l'exemple

```bash
python main_example.py
```

Cela génère un fichier `output.txt`.

## Lancer les tests

```bash
python -m pytest
```

## CI et releases

Le repo contient deux workflows GitHub Actions :

- `.github/workflows/ci.yml` : lance `pytest` sur push et pull request ;
- `.github/workflows/release.yml` : à chaque tag `v*`, lance les tests, crée une archive ZIP du repo, puis publie une release GitHub avec notes générées automatiquement.

Exemple de tag :

```bash
git tag v0.1.0
git push origin v0.1.0
```

## Exemple minimal

```python
from datetime import date

from fixed_width_generator import SegmentedFlatFileMaster
from example_sources import SOURCE_REGISTRY, get_next_line_type_compte_titulaires

master = SegmentedFlatFileMaster(
    source_registry=SOURCE_REGISTRY,
    get_next_line_type=get_next_line_type_compte_titulaires,
    logical_length=600,
    segment_payload_length=200,
    physical_prefix_length=25,
    generation_date=date(2026, 8, 14),
)

master.register(
    line_type="COMPTE",
    start=1,
    length=10,
    function_name="get_type_ligne",
    name="type_ligne_compte",
    truncate=True,
)

master.register(
    line_type="TITULAIRE",
    start=1,
    length=10,
    function_name="get_type_ligne",
    name="type_ligne_titulaire",
    truncate=True,
)
```

## Principe du `get_next_line_type`

Le moteur appelle cette fonction en boucle pour chaque record source.

Elle doit retourner :

- `"COMPTE"` pour produire une ligne logique compte ;
- `"TITULAIRE"` pour produire une ligne logique titulaire ;
- `None` pour passer au record source suivant.

Exemple :

```python
def get_next_line_type(input_record, context):
    if not context.get("_compte_line_done"):
        context["_compte_line_done"] = True
        return "COMPTE"

    titulaires = input_record.get("titulaires", [])
    index = context.get("_titulaire_index", 0)

    if index < len(titulaires):
        context["_current_titulaire"] = titulaires[index]
        context["_current_titulaire_number"] = index + 1
        context["_titulaire_index"] = index + 1
        return "TITULAIRE"

    return None
```

## Pas de dataclasses

Le projet n'utilise pas `@dataclass`.
