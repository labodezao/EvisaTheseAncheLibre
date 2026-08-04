"""`python -m banc_recherche …` → même CLI que `banc-recherche-cli`."""
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
