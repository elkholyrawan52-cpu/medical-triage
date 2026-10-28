"""Knowledge-base loading (rules, facts catalog, sources)."""
import json
from pathlib import Path

KB_DIR = Path(__file__).resolve().parent.parent / "knowledge"


def _load(name):
    with open(KB_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def load_rules():
    return _load("rules.json")["rules"]


def load_sources():
    return _load("rules.json")["sources"]


def load_catalog():
    return _load("facts_catalog.json")
