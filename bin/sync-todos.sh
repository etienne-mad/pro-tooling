#!/usr/bin/env bash
# Create symlinks in pro-* repos pointing to their TODO note in the vault.
# Idempotent: skips if symlink already exists and points to the right target.

BACKLOG_DIR="$PRO_VAULT/90-99 System & meta/98 External backlogs"

for repo in "$HOME/repos/pro-"*; do
    [ -d "$repo/.git" ] || continue
    name=$(basename "$repo")
    [ "$name" = "pro-vault" ] && continue

    target="$BACKLOG_DIR/${name}.md"
    [ -f "$target" ] || continue

    link="$repo/TODO"

    if [ -L "$link" ] && [ "$(readlink "$link")" = "$target" ]; then
        echo "OK: $name (already linked)"
    else
        ln -sf "$target" "$link"
        echo "Linked: $name"
    fi
done