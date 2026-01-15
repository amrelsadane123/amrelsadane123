#!/usr/bin/env python3
"""Check RDP connectivity for hosts listed in a text file."""

from __future__ import annotations

import argparse
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

DEFAULT_PORT = 3389
DEFAULT_TIMEOUT = 3.0


@dataclass(frozen=True)
class Target:
    host: str
    port: int


@dataclass(frozen=True)
class Result:
    target: Target
    status: str
    error: Optional[str] = None


def parse_target(raw: str, default_port: int) -> Optional[Target]:
    cleaned = raw.strip()
    if not cleaned or cleaned.startswith("#"):
        return None

    if "#" in cleaned:
        cleaned = cleaned.split("#", 1)[0].strip()

    if not cleaned:
        return None

    if ":" in cleaned:
        host, port_str = cleaned.rsplit(":", 1)
        host = host.strip()
        port_str = port_str.strip()
        if not host or not port_str:
            raise ValueError(f"Invalid target line: '{raw}'")
        try:
            port = int(port_str)
        except ValueError as exc:
            raise ValueError(f"Invalid port in line: '{raw}'") from exc
        return Target(host=host, port=port)

    return Target(host=cleaned, port=default_port)


def load_targets(path: Path, default_port: int) -> List[Target]:
    targets: List[Target] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            target = parse_target(raw, default_port)
        except ValueError as exc:
            raise ValueError(f"Line {line_number}: {exc}") from exc
        if target:
            targets.append(target)
    return targets


def check_target(target: Target, timeout: float) -> Result:
    try:
        with socket.create_connection((target.host, target.port), timeout=timeout):
            return Result(target=target, status="open")
    except socket.timeout:
        return Result(target=target, status="timeout")
    except OSError as exc:
        return Result(target=target, status="closed", error=str(exc))


def format_result(result: Result) -> str:
    base = f"{result.target.host}:{result.target.port} -> {result.status}"
    if result.error:
        return f"{base} ({result.error})"
    return base


def write_results(results: Iterable[Result], output: Optional[Path]) -> None:
    lines = [format_result(result) for result in results]
    output_text = "\n".join(lines)
    if output:
        output.write_text(output_text + "\n", encoding="utf-8")
    else:
        print(output_text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check RDP port connectivity for targets listed in a text file.",
    )
    parser.add_argument(
        "file",
        type=Path,
        help="Path to text file containing hosts (one per line).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Default port when not specified (default: {DEFAULT_PORT}).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Socket timeout in seconds (default: {DEFAULT_TIMEOUT}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output file to save results.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.file.exists():
        parser.error(f"File not found: {args.file}")

    try:
        targets = load_targets(args.file, args.port)
    except ValueError as exc:
        parser.error(str(exc))

    if not targets:
        parser.error("No valid targets found in the file.")

    results = [check_target(target, args.timeout) for target in targets]
    write_results(results, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
