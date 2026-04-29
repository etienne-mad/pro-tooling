#!/usr/bin/env bash
# context — gather files into a clipboard-ready block for Claude.
#
# Usage:
#   context file1.md dir/ file2.py ...
#
# Directories are scanned recursively for readable text files.
# Binary files are skipped. Output is copied to clipboard and
# printed to stderr so you see what was collected.

set -euo pipefail

if [ $# -eq 0 ]; then
  echo "Usage: context <file|dir> [file|dir ...]" >&2
  exit 1
fi

# --- Directories to skip (edit this list) ---------------------------------

SKIP_DIRS=(.git .obsidian node_modules __pycache__ .venv .trash)

# --- Collect file list ---------------------------------------------------

prune_args=()
for d in "${SKIP_DIRS[@]}"; do
  prune_args+=(-name "$d" -o)
done
# remove trailing -o, wrap in prune clause
unset 'prune_args[-1]'

files=()
for arg in "$@"; do
  if [ -f "$arg" ]; then
    files+=("$arg")
  elif [ -d "$arg" ]; then
    while IFS= read -r f; do
      files+=("$f")
    done < <(find "$arg" \( -type d \( "${prune_args[@]}" \) -prune \) -o -type f -print | sort)
  else
    echo "warning: skipping '$arg' (not a file or directory)" >&2
  fi
done

if [ ${#files[@]} -eq 0 ]; then
  echo "No files found." >&2
  exit 1
fi

# --- Build output ---------------------------------------------------------

output=""
count=0

for f in "${files[@]}"; do
  # skip binary files
  if ! file --brief --mime-encoding "$f" 2>/dev/null | grep -qi 'ascii\|utf'; then
    echo "skip (binary): $f" >&2
    continue
  fi

  content=$(<"$f")
  output+="--- $f ---"$'\n'
  output+="$content"$'\n\n'
  count=$((count + 1))
  echo "  added: $f" >&2
done

# --- Clipboard ------------------------------------------------------------

copied=false
if command -v xclip &>/dev/null; then
  printf '%s' "$output" | xclip -selection clipboard
  copied=true
elif command -v xsel &>/dev/null; then
  printf '%s' "$output" | xsel --clipboard --input
  copied=true
elif command -v pbcopy &>/dev/null; then
  printf '%s' "$output" | pbcopy
  copied=true
fi

if $copied; then
  echo "✓ $count file(s) copied to clipboard." >&2
else
  echo "⚠ No clipboard tool found. Printing to stdout instead." >&2
  printf '%s' "$output"
fi
