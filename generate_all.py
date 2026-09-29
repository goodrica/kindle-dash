#!/usr/bin/env python3
"""
Master generator: runs calendar + scores, uploads to VPS2.
Designed to be run as a Hermes cron job.
"""
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
VPS2_HOST = "hermes-vps2"  # From ~/.ssh/config
VPS2_PATH = "/var/www/thegoodrichfamily/kindle/"

def run_step(name: str, script: str) -> bool:
    print(f"\n{'='*50}")
    print(f"  {name}")
    print(f"{'='*50}")
    result = subprocess.run(
        [sys.executable, str(PROJECT_DIR / script)],
        capture_output=False,  # Stream output live
        timeout=60,
    )
    ok = result.returncode == 0
    print(f"  {'✓ OK' if ok else '✗ FAILED'} (exit {result.returncode})")
    return ok


def upload():
    """scp the output files to VPS2."""
    output_dir = PROJECT_DIR / "output"
    files = list(output_dir.glob("*.html"))
    if not files:
        print("  No HTML files to upload")
        return False
    
    for f in files:
        print(f"  Uploading {f.name}...")
        result = subprocess.run(
            ["scp", str(f), f"{VPS2_HOST}:{VPS2_PATH}{f.name}"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            print(f"    → https://project.thegoodrichfamily.net/kindle/{f.name}")
        else:
            print(f"    ✗ scp failed: {result.stderr.strip()}")
            return False
    return True


def main():
    print("Kindle Dashboard Generator")
    print(f"  {PROJECT_DIR}")
    
    ok = True
    ok &= run_step("Calendar", "generate_calendar.py")
    ok &= run_step("Scores", "generate_scores.py")
    
    if ok:
        print("\nUploading to VPS2...")
        if upload():
            print("\n✓ All done!")
        else:
            print("\n⚠ Generated OK but upload failed")
            sys.exit(2)
    else:
        print("\n✗ Generation failed — skipping upload")
        sys.exit(1)


if __name__ == "__main__":
    main()