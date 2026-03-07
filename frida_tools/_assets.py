from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Iterator

_PACKAGE_ROOT = Path(__file__).resolve().parent
_SOURCE_ROOT = _PACKAGE_ROOT.parent
_BUILD_DIR_ENV = "FRIDA_TOOLS_BUILD_DIR"

_BUILD_ASSET_PATHS = {
    "fs_agent.js": Path("agents") / "fs" / "fs_agent.js",
    "itracer_agent.js": Path("agents") / "itracer" / "itracer_agent.js",
    "repl_agent.js": Path("agents") / "repl" / "repl_agent.js",
    "tracer_agent.js": Path("agents") / "tracer" / "tracer_agent.js",
    "tracer_ui.zip": Path("apps") / "tracer" / "tracer_ui.zip",
}


def _iter_build_roots() -> Iterator[Path]:
    build_dir = os.environ.get(_BUILD_DIR_ENV)
    if build_dir is not None:
        yield Path(build_dir)

    yield _SOURCE_ROOT / "build"

    if _SOURCE_ROOT.parent.name == "subprojects":
        yield _SOURCE_ROOT.parent.parent / "build" / "subprojects" / _SOURCE_ROOT.name


def _iter_unique(paths: Iterable[Path]) -> Iterator[Path]:
    seen = set()
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        yield path


def _find_existing_path(name: str, candidates: Iterable[Path]) -> Path:
    tried = []
    for candidate in _iter_unique(candidates):
        tried.append(candidate)
        if candidate.exists():
            return candidate

    searched = "\n".join(f"- {path}" for path in tried)
    raise FileNotFoundError(f"Unable to locate {name}. Looked in:\n{searched}")


def resolve_asset(name: str) -> Path:
    build_relpath = _BUILD_ASSET_PATHS.get(name)
    candidates = [_PACKAGE_ROOT / name]
    if build_relpath is not None:
        candidates.extend(root / build_relpath for root in _iter_build_roots())
    return _find_existing_path(name, candidates)


def read_text_asset(name: str) -> str:
    return resolve_asset(name).read_text(encoding="utf-8")


def resolve_bridge(name: str) -> Path:
    filename = f"{name.lower()}.js"
    candidates = [_PACKAGE_ROOT / "bridges" / filename]
    candidates.extend(root / "bridges" / filename for root in _iter_build_roots())
    return _find_existing_path(filename, candidates)
