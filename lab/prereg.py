"""Pre-registration: the spec is hashed before any statistic runs, and every run re-checks the hash."""
import hashlib
from pathlib import Path


class PreregError(Exception):
    pass


def sha256_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sidecar(prereg) -> Path:
    return Path(prereg).with_suffix(".sha256")


def freeze(prereg) -> str:
    """Write PREREG.sha256 next to PREREG.md. Refuses to overwrite: a frozen spec is never re-frozen."""
    side = sidecar(prereg)
    if side.exists():
        raise PreregError(f"{side} exists: already frozen; register a new lane instead of editing")
    digest = sha256_file(prereg)
    side.write_bytes((digest + "\n").encode())
    return digest


def verify(prereg) -> str:
    """Call first thing in every run script. Raises unless the spec still matches its frozen hash."""
    side = sidecar(prereg)
    if not side.exists():
        raise PreregError(f"{side} missing: freeze the spec before running any statistic")
    frozen = side.read_text().strip()
    actual = sha256_file(prereg)
    if actual != frozen:
        raise PreregError(f"{prereg} changed after freezing: {actual} != {frozen}")
    return actual
