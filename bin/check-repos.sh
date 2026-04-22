#!/usr/bin/env bash
# Check all pro-* repos for uncommitted changes and unpushed commits.

for repo in "$HOME/repos/pro-"*; do
    [ -d "$repo/.git" ] || continue
    name=$(basename "$repo")

    dirty=$(git -C "$repo" status --porcelain)
    unpushed=$(git -C "$repo" log @{u}.. --oneline 2>/dev/null)

    if [ -n "$dirty" ] || [ -n "$unpushed" ]; then
        echo "=== $name ==="
        [ -n "$dirty" ] && echo "  Uncommitted:" && echo "$dirty" | sed 's/^/    /'
        [ -n "$unpushed" ] && echo "  Unpushed:" && echo "$unpushed" | sed 's/^/    /'
    fi
done