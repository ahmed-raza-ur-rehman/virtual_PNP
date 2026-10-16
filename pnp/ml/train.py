"""Training script entrypoint."""
from __future__ import annotations

import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--epochs", type=int, default=10)
    args = parser.parse_args()
    print(f"Training for {args.epochs} epochs on {args.data}")
    # placeholder training loop
    for e in range(args.epochs):
        print(f"epoch {e+1}/{args.epochs}")


if __name__ == "__main__":
    main()
