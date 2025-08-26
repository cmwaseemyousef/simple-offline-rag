# Ensure the workspace root is on sys.path so `import src...` works when running pytest from various contexts.
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
