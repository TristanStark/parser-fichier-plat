# Fixed Width Segmented Generator

Squelette Python pour générer des fichiers plats à largeur fixe.

## Utilisation

Le moteur permet de déclarer des champs à position fixe avec :

```python
master.register(line_type, start, length, function_name, conditions)
```

Chaque fonction source reçoit l'enregistrement d'entrée et le contexte courant :

```python
def ma_source(input_record, context):
    return valeur_a_ecrire, context
```

## Générateur CSV

Le CLI génère un squelette Python à partir de fichiers CSV de structure.

```bash
python -m fixed_width_generator.codegen_cli
```

Format CSV attendu :

```csv
nom colonne;longueur;format;start position
Code ligne;2;AN;1
Nombre TYPE_Bs;2;N;3
Nom;30;AN;5
```

Formats supportés : `AN`, `A`, `N`.

## Préfixe

Le préfixe est configurable via `SegmentPrefixBuilder`.

```python
master.prefix_builder = SegmentPrefixBuilder(
    prefix_length=25,
    prefix_length_field="0000000",
)
```

## Tests

```bash
python -m pytest
```

## Build local

```bash
python -m pip install --upgrade build
python -m build
```

Les fichiers produits sont placés dans `dist`.

## CI et releases

La CI doit lancer les tests, construire le package, puis conserver les fichiers de build comme artefacts.

La release doit publier les fichiers de build générés, en plus de l'archive du dépôt.

## Pas de dataclasses

Le projet n'utilise pas `@dataclass`.
