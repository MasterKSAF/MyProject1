from pathlib import Path
import runpy
import sys

TARGET = Path(__file__).resolve().parents[1] / "stages" / "stage4" / "scripts" / "stage4_baseline_train.py"

if __name__ == "__main__":
    sys.path.insert(0, str(TARGET.parent))
    runpy.run_path(str(TARGET), run_name="__main__")
