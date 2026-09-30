"""Entry point for source runs and the frozen Windows application."""

import os
import runpy
import sys


def main():
    if getattr(sys, "frozen", False):
        os.chdir(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)))

    if len(sys.argv) > 2 and sys.argv[1] == "--aria-run-script":
        script_path = os.path.abspath(sys.argv[2])
        sys.argv = [script_path, *sys.argv[3:]]
        runpy.run_path(script_path, run_name="__main__")
        return

    from main import main as run_aria

    run_aria()


if __name__ == "__main__":
    main()