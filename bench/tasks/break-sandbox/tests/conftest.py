import pathlib
import sys

# At capture time this lives at <worktree>/_eval_tests/conftest.py. The
# model's exploit.py is one level up at the worktree root — put it on
# sys.path so `import exploit` resolves.
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
