"""Verify the unchanged published v0.69 release, or the new development tree."""
from pathlib import Path
import argparse
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--development', action='store_true')
    args = parser.parse_args()
    target = ROOT/'scenarios/verify_layout.py' if args.development else ROOT/'releases/v0.69-v3-current-source/verify_release.py'
    raise SystemExit(subprocess.call([sys.executable, str(target)], cwd=target.parent))

if __name__ == '__main__':
    main()
