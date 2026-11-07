"""Command-line interface for pdf-extract."""

import argparse


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="pdf-extract",
        description="Convert every PDF in a directory into a JSON text snapshot.",
    )


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    return 0
