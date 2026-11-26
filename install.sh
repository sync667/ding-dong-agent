#!/bin/sh
# ding-dong-agent installer.
#
# From a clone:  ./install.sh [options]
# One line:      curl -fsSL https://raw.githubusercontent.com/sync667/ding-dong-agent/v1.3.0/install.sh | sh -s -- [options]
#
# Run from a clone, it uses the files next to it. Piped into sh, it downloads
# the release tagged below over HTTPS into a temporary folder, runs installer.py
# from there and deletes the folder. installer.py copies what it needs into
# ~/.local/share/ding-dong-agent, so nothing is left behind.
#
# Options are passed to installer.py: --agents, --dry-run, --uninstall, --no-skill, --force.
set -eu

VERSION="v1.3.0"
ARCHIVE="https://github.com/sync667/ding-dong-agent/archive/refs/tags/${VERSION}.tar.gz"

say() { printf 'ding-dong-agent: %s\n' "$*" >&2; }
die() { say "$*"; exit 1; }

# Everything runs inside main, so a download cut off half-way does nothing.
main() {
    command -v python3 >/dev/null 2>&1 || die "python3 is required (3.8 or newer)"

    case "$0" in
        */install.sh | install.sh)
            here=$(cd "$(dirname "$0")" && pwd)
            if [ -f "$here/installer.py" ]; then
                exec python3 "$here/installer.py" "$@"
            fi
            ;;
    esac

    command -v tar >/dev/null 2>&1 || die "tar is required"
    tmp=$(mktemp -d 2>/dev/null || mktemp -d -t ding-dong-agent)
    trap 'rm -rf "$tmp"' EXIT INT TERM

    say "downloading ${VERSION}"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL --proto '=https' --tlsv1.2 "$ARCHIVE" -o "$tmp/src.tar.gz"
    elif command -v wget >/dev/null 2>&1; then
        wget -q --https-only -O "$tmp/src.tar.gz" "$ARCHIVE"
    else
        die "curl or wget is required"
    fi

    tar -xzf "$tmp/src.tar.gz" -C "$tmp"
    src=$(find "$tmp" -mindepth 2 -maxdepth 2 -name installer.py -print | head -n 1)
    [ -n "$src" ] || die "installer.py not found in the downloaded archive"

    python3 "$src" "$@"
}

main "$@"
