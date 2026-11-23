#!/usr/bin/env bash
# Builds Luau 0.739 (`luau` and `luau-ast`) for Linux / GitHub Codespaces into
# deobf/bin. The binaries in the v15 repo are Windows .exe files and the
# interpreter needs one patch (vector metatable left writable, see
# deobf/build_luau.py). Takes a few minutes the first time; safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"

TAG=0.739
WORK=.build/luau
SUDO=""
if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then SUDO="sudo"; fi

if ! command -v cmake >/dev/null 2>&1 || ! command -v g++ >/dev/null 2>&1 || ! command -v git >/dev/null 2>&1; then
    $SUDO apt-get update -y
    $SUDO apt-get install -y cmake g++ git
fi

mkdir -p deobf/bin .build
if [ ! -d "$WORK/src" ]; then
    git clone -q --depth 1 --branch "$TAG" https://github.com/luau-lang/luau.git "$WORK/src"
fi

# same patch build_luau.py applies (idempotent)
python3 -c "import sys; sys.path.insert(0, 'deobf'); import build_luau; build_luau.patch(sys.argv[1])" "$WORK/src"

cmake -S "$WORK/src" -B "$WORK/build" -DCMAKE_BUILD_TYPE=Release -DLUAU_BUILD_TESTS=OFF \
    -DCMAKE_C_FLAGS_RELEASE="-O2 -DNDEBUG" -DCMAKE_CXX_FLAGS_RELEASE="-O2 -DNDEBUG" >/dev/null
cmake --build "$WORK/build" --target Luau.Repl.CLI Luau.Ast.CLI --parallel "$(nproc)"

cp "$WORK/build/luau" "$WORK/build/luau-ast" deobf/bin/
chmod +x deobf/bin/luau deobf/bin/luau-ast

echo 'print(_VERSION, vector ~= nil)' > "$WORK/smoke.luau"
deobf/bin/luau "$WORK/smoke.luau"
echo "ok: deobf/bin/luau and deobf/bin/luau-ast are ready"
