#!/usr/bin/env sh
# porkbun-api-skill installer for macOS and Linux.
#
# Two ways to run:
#
#   1. Inside a cloned checkout:
#        ./install.sh
#
#   2. One-liner (works after the repo is published):
#        curl -fsSL https://raw.githubusercontent.com/aditya-m-bharadwaj/porkbun-api-skill/main/install.sh | sh
#
# Flags (env vars):
#   PORKBUN_CTL_PREFIX   target dir for the symlink     (default: ~/.local/bin)
#   PORKBUN_CTL_HOME     where to clone the repo        (default: ~/.local/share/porkbun-api-skill)
#   PORKBUN_CTL_REPO     git URL to clone               (default: aditya-m-bharadwaj/porkbun-api-skill placeholder)
#   PORKBUN_CTL_REF      branch/tag/SHA to check out    (default: main)
#   INSTALL_SKILL        1 = also install Claude skill  (default: 0; prompts if interactive)
#   RUN_SETUP            1 = run `porkbun-api-skill setup` after install (default: prompts if interactive)
#   NO_SETUP             1 = never prompt to run setup
#
# This script:
#   * verifies Python 3.8+,
#   * clones the repo (or uses the current checkout),
#   * symlinks `bin/porkbun-api-skill` into the prefix dir,
#   * optionally installs the Claude skill into ~/.claude/skills/porkbun-api-skill/,
#   * optionally runs `porkbun-api-skill setup` so you can paste your API key pair now.
#
# Neither key is read by this shell script. They are read by Python's
# getpass (hidden input) in the `setup` subcommand, never appear in argv
# or environment, and never written to disk in cleartext (they go to the
# OS keystore, or to a mode-0600 JSON file when no keystore is available).
#
# STATUS: this script is a SKELETON. It is structurally correct (parallels
# `linode-api-skill/install.sh`) but has not been smoke-tested end-to-end
# against a published GitHub repo (the repo doesn't exist yet).

set -e

# Default to the placeholder repo URL; override via PORKBUN_CTL_REPO when published.
DEFAULT_REPO="https://github.com/aditya-m-bharadwaj/porkbun-api-skill.git"

PREFIX="${PORKBUN_CTL_PREFIX:-$HOME/.local/bin}"
HOME_DIR="${PORKBUN_CTL_HOME:-$HOME/.local/share/porkbun-api-skill}"
REPO_URL="${PORKBUN_CTL_REPO:-$DEFAULT_REPO}"
REF="${PORKBUN_CTL_REF:-main}"

C_BLUE=$(printf '\033[1;34m')
C_YELLOW=$(printf '\033[1;33m')
C_RED=$(printf '\033[1;31m')
C_OFF=$(printf '\033[0m')

info() { printf '%s[install]%s %s\n' "$C_BLUE" "$C_OFF" "$1"; }
warn() { printf '%s[warn]%s %s\n' "$C_YELLOW" "$C_OFF" "$1"; }
die()  { printf '%s[error]%s %s\n' "$C_RED" "$C_OFF" "$1" >&2; exit 1; }

# --- Detect: in-checkout vs. clone-fresh
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
if [ -f "$SCRIPT_DIR/bin/porkbun-api-skill" ]; then
    SOURCE_DIR="$SCRIPT_DIR"
    info "Using current checkout: $SOURCE_DIR"
else
    info "Cloning $REPO_URL -> $HOME_DIR (ref=$REF)"
    mkdir -p "$(dirname "$HOME_DIR")"
    if [ -d "$HOME_DIR/.git" ]; then
        ( cd "$HOME_DIR" && git fetch --quiet && git checkout --quiet "$REF" && git pull --quiet --ff-only )
    else
        git clone --quiet --depth 1 --branch "$REF" "$REPO_URL" "$HOME_DIR" \
            || die "git clone failed (is the repo published yet? See README)"
    fi
    SOURCE_DIR="$HOME_DIR"
fi

# --- Verify Python 3.8+
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)' 2>/dev/null; then
            PYTHON="$candidate"
            break
        fi
    fi
done
[ -n "$PYTHON" ] || die "Python 3.8+ not found. Install Python 3.8 or newer and rerun."
info "Python: $PYTHON ($($PYTHON --version 2>&1))"

# --- Symlink into prefix
mkdir -p "$PREFIX"
ln -sf "$SOURCE_DIR/bin/porkbun-api-skill" "$PREFIX/porkbun-api-skill"
info "Symlinked: $PREFIX/porkbun-api-skill -> $SOURCE_DIR/bin/porkbun-api-skill"

# --- PATH warning
case ":$PATH:" in
    *":$PREFIX:"*) ;;
    *)
        warn "$PREFIX is not on your PATH."
        warn "Add to your shell rc (~/.bashrc or ~/.zshrc):"
        warn "    export PATH=\"\$HOME/.local/bin:\$PATH\""
        ;;
esac

# --- Optional: install the Claude skill
INSTALL_SKILL_DECISION=${INSTALL_SKILL:-}
if [ -z "$INSTALL_SKILL_DECISION" ] && [ -t 0 ]; then
    printf '\n[install] Install the Claude skill to ~/.claude/skills/porkbun-api-skill? (y/N): '
    read -r reply
    case "$reply" in y|Y) INSTALL_SKILL_DECISION=1 ;; *) INSTALL_SKILL_DECISION=0 ;; esac
fi
if [ "$INSTALL_SKILL_DECISION" = "1" ]; then
    mkdir -p "$HOME/.claude/skills/porkbun-api-skill"
    cp -f "$SOURCE_DIR/.claude/skills/porkbun-api-skill/SKILL.md" "$HOME/.claude/skills/porkbun-api-skill/SKILL.md"
    info "Skill installed at: $HOME/.claude/skills/porkbun-api-skill/SKILL.md"
fi

# --- Optional: run setup now
RUN_SETUP_DECISION=${RUN_SETUP:-}
if [ -n "$NO_SETUP" ]; then
    RUN_SETUP_DECISION=0
elif [ -z "$RUN_SETUP_DECISION" ] && [ -t 0 ]; then
    # shellcheck disable=SC2016
    printf '\n[install] Run `porkbun-api-skill setup` now to store your API key pair? (y/N): '
    read -r reply
    case "$reply" in y|Y) RUN_SETUP_DECISION=1 ;; *) RUN_SETUP_DECISION=0 ;; esac
fi
if [ "$RUN_SETUP_DECISION" = "1" ]; then
    # Re-attach to /dev/tty so `getpass` works even when this script was piped
    # from `curl | sh`. Same trick as linode-api-skill/install.sh.
    if [ -t 0 ]; then
        "$PREFIX/porkbun-api-skill" setup || warn "Setup did not complete."
    else
        "$PREFIX/porkbun-api-skill" setup </dev/tty || warn "Setup did not complete."
    fi
fi

info ""
info "Installed. Next steps:"
info "  1. Run:  porkbun-api-skill setup        # paste your API key pair (input is hidden)"
info "  2. Run:  porkbun-api-skill whoami       # verify auth"
info "  - To change credentials later: porkbun-api-skill setup    (or 'rotate-credentials')"
info "  - To remove credentials:       porkbun-api-skill uninstall-credentials --yes"
info "  - Read: $SOURCE_DIR/README.md"
