# pro-tooling

Outillage CLI pour l'activité freelance.

## Principes

- Scripts PEP 723 self-contained, exécutés via `uv`.
- Appelés depuis les Makefile de `pro-vault` et `pro-website`.
- Chemin exposé via variable d'environnement `PRO_TOOLING`.

## Setup

Ajouter à la config shell (~/.zshrc, ~/.bashrc, etc.) :

    export PRO_TOOLING="$HOME/repos/pro-tooling"

## Scripts

- `bin/vault-tasks.py <prospects_dir>` : liste les tâches prospect triées par date.
