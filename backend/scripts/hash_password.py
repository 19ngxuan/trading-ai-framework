from getpass import getpass
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.auth.security import hash_password  # noqa: E402


def main() -> int:
    password = getpass("Password: ")
    confirm = getpass("Confirm password: ")
    if not password:
        print("Password must not be empty.", file=sys.stderr)
        return 1
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        return 1
    print(hash_password(password))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
