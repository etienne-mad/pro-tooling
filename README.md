# pro-tooling

Outillage CLI pour l'activité freelance.

## Principes

- Scripts PEP 723 self-contained, exécutés via `uv`.
- `$PRO_TOOLING/bin` ajouté au PATH via `aliases.sh`.
- Appelés depuis les Makefile de `pro-vault` et `pro-website`, ou directement en CLI.

## Setup

Ajouter à la config shell (`~/.zshrc`, `~/.bashrc`, etc.) :

    source "$HOME/repos/pro-tooling/aliases.sh"

## Scripts

- `tasks [dir]` — liste les notes avec `next_action` / `next_action_date` (+ tâches `recurring`), triées par date. Scanne le vault par défaut, ou un sous-dossier si spécifié.
- `context <file|dir>...` — rassemble des fichiers en un bloc prêt à coller pour Claude (copié dans le presse-papier).
- `check-repos.sh` — vérifie tous les repos `~/repos/*` pour modifications non committées et commits non poussés.
- `sync-todos.sh` — crée les symlinks TODO dans les repos `pro-*` pointant vers les notes du vault (`98 External backlogs`).