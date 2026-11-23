"""Luraph v15 plugin: devirtualizer + behaviour trace (notes: LURAPH.md)."""
import re
import sys

from obfuscators.base import Obfuscator

HEADER = re.compile(r"This file was protected using Luraph Obfuscator v(\d+)(?:\.(\d+))?")
HEADER_LINE = re.compile(r"\s*--[ \t]*This file was protected using Luraph Obfuscator v[\d.]+[ \t]*"
                         r"\[https?://lura\.ph/?\]")


JUNKIE_KEY = re.compile(
    r"""[ \t]*getgenv[ \t]*\([ \t]*\)[ \t]*\.[ \t]*SCRIPT_KEY[ \t]*=[ \t]*"""
    r"""(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[A-Za-z_]\w*|[-+]?\d+(?:\.\d+)?|nil|true|false)"""
    r"""[ \t]*;?[ \t]*(?:--.*)?"""
)
VM_PAYLOAD = re.compile(r"^[ \t]*return[ \t]+setmetatable[ \t]*\(", re.M)


class LuraphV15(Obfuscator):
    name = "luraph_v15"
    label = "Luraph v15"
    doc = "LURAPH.md"

    def detect(self, source):
        m = HEADER.search(source[:500])
        if m:
            return 1.0 if m.group(1) == "15" else 0.3     # other versions: probably close, not verified
        # header stripped: v15's shape is `return setmetatable({...VM object...}, ...)`
        # with numeric-keyed library slots (`[75]=bit32.rrotate`) and `LPH` markers
        head = source.lstrip()[:2000]
        if head.startswith("return setmetatable({") and (
                re.search(r"\[\d+\]=(bit32|buffer|string|table|math)\.\w+", head) or "LPH" in source[:200000]):
            return 0.8
        return 0.0

    def add_arguments(self, ap):
        g = ap.add_argument_group("Luraph v15")
        g.add_argument("--no-hooks", action="store_true",
                       help="do not instrument VM functions (no anti-tamper trap attribution, no lifting)")
        g.add_argument("--max-runs", type=int, default=12, help="maximum number of trace runs (trap reruns)")
        g.add_argument("--devirt-rounds", type=int, default=200,
                       help="max lift + constant-request rounds (default 200; stops early when no new "
                            "constants turn up)")

    def deobfuscate(self, job):
        from obfuscators.luraph_v15 import driver
        fixed = restore_header_newline(job.source)
        if fixed != job.source:
            print("[*] header comment ran into the code (lost newline): split it", file=sys.stderr)

        fixed, key_removed = strip_junkie_script_key(fixed)
        if key_removed:
            print("[*] ignored owner-injected getgenv().SCRIPT_KEY before the Luraph payload",
                  file=sys.stderr)

        if fixed != job.source:
            # Keep source_path byte-for-byte aligned with the text being instrumented.
            # The copy keeps the input's name (Path2D cache, messages use job.input).
            job.source = fixed
            job.source_path = job.write(job.path(".src.lua"), fixed, encoding="latin-1")
        return driver.run(job)


def strip_junkie_script_key(source):
    """Remove only the standalone Junkie key line injected before a Luraph VM.

    The assignment is stripped only when it is the first executable line
    after a Luraph header and the next executable line is the VM bootstrap.
    Other SCRIPT_KEY uses and ordinary Luau source are left untouched.
    """
    header = HEADER.search(source[:500])
    if not header:
        return source, False

    header_end = source.find("\n", header.end())
    if header_end < 0:
        return source, False

    start = header_end + 1
    payload = VM_PAYLOAD.search(source, start)
    if not payload:
        return source, False

    pos = start
    for line in source[start:payload.start()].splitlines(keepends=True):
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            pos += len(line)
            continue
        if not JUNKIE_KEY.fullmatch(line.rstrip("\r\n")):
            return source, False

        # Between the key and VM bootstrap there must be comments/blank lines only.
        tail = source[pos + len(line):payload.start()]
        if any(part.strip() and not part.lstrip().startswith("--")
               for part in tail.splitlines()):
            return source, False
        return source[:pos] + source[pos + len(line):], True

    return source, False


def restore_header_newline(source):
    """Pasted copies (e.g. Discord's message.txt) can lose the newline after
    the `-- This file was protected ... [https://lura.ph/]` line, which turns
    the whole script into that comment. Put it back."""
    m = HEADER_LINE.match(source)
    if m and source[m.end():m.end() + 1] not in ("", "\n", "\r"):
        return source[:m.end()] + "\n" + source[m.end():].lstrip(" \t")
    return source
