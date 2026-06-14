"""Make `import engine` / `import strategies` work when pytest collects this dir."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
