"""Extract stack hints as data; paths are matched only against sealed relative paths."""

import re
from dataclasses import dataclass

PYTHON_FRAME = re.compile(r'File ["\']([^"\']+)["\'], line (\d+)(?:, in ([\w.<>]+))?')
OTHER_FRAME = re.compile(
    r"(?:^|[\s(])([^\s()]+\.(?:py|js|jsx|ts|tsx|go|rs|java|c|cpp)):(\d+)(?::\d+)?"
)


@dataclass(frozen=True)
class StackHint:
    file_path: str
    line: int
    symbol: str


def hints(trace: str) -> list[StackHint]:
    """Normalize safe syntax without opening any path mentioned in a trace."""
    result = []
    for pattern in (PYTHON_FRAME, OTHER_FRAME):
        for match in pattern.finditer(trace[:16000]):
            path = match[1].replace("\\", "/")
            if ".." in path.split("/") or "%" in path or "://" in path or "\x00" in path:
                continue
            line = int(match[2]) if len(match[2]) < 10 else 0
            symbol = (match[3] or "") if pattern is PYTHON_FRAME else ""
            if line > 0:
                result.append(StackHint(path, line, symbol))
    return result[:128]


def matching_path(path: str, indexed_paths: set[str]) -> str | None:
    """Accept exact paths or a unique complete suffix; never guess ambiguous basenames."""
    if path in indexed_paths:
        return path
    candidates = [relative for relative in indexed_paths if path.endswith("/" + relative)]
    return candidates[0] if len(candidates) == 1 else None


def exact_tier(file_path: str, symbol: str, start: int, end: int, frames: list[StackHint]) -> int:
    tiers = [
        2
        if start <= frame.line <= end
        else 1
        if symbol
        and frame.symbol
        and (symbol == frame.symbol or symbol.endswith("." + frame.symbol))
        else 0
        for frame in frames
        if frame.file_path == file_path
    ]
    return max(tiers, default=0)
