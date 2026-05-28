"""Uses unwrapped random — must diverge on replay."""

from __future__ import annotations

import random


def main() -> str:
    if random.random() > 0.5:
        return "branch_a"
    return "branch_b"


if __name__ == "__main__":
    print(main())
