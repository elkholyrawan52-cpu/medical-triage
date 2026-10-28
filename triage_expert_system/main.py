"""CLI: python main.py demo | interview [--lang en]"""
import sys

from engine.explain import format_text
from engine.inference import InferenceEngine
from engine.kb import load_catalog, load_rules, load_sources
from engine.levels import DISCLAIMER_AR, DISCLAIMER_EN

DEMO_CASES = {
    "Stroke signs (face droop + slurred speech)": {"age_months": 62 * 12, "face_droop": True, "slurred_speech": True},
    "Chest squeezing pain + sweating": {"age_months": 55 * 12, "chest_pain": True, "chest_pain_tight_pressure": True, "sweating": True},
    "Sprained ankle, pain 8/10 (ESI: not automatically level 2)": {"age_months": 25 * 12, "pain_score": 8},
    "Baby 2 months, temp 38.6": {"age_months": 2, "temp_c": 38.6},
    "No symptoms": {"age_months": 30 * 12},
}


def ask_cli(catalog, lang):
    def ask(fact):
        spec = catalog[fact]
        label = spec[lang]
        if spec["type"] == "bool":
            while True:
                a = input(f"{label}? (y/n/skip): ").strip().lower()
                if a in ("y", "yes", "ن", "نعم"):
                    return True
                if a in ("n", "no", "ل", "لا", "", "skip"):
                    return False
        a = input(f"{label} (Enter = unknown): ").strip()
        return float(a) if a else None
    return ask


def main():
    lang = "en" if "--lang" in sys.argv and sys.argv[sys.argv.index("--lang") + 1] == "en" else "ar"
    rules, catalog, sources = load_rules(), load_catalog(), load_sources()
    engine = InferenceEngine(rules, catalog)
    mode = sys.argv[1] if len(sys.argv) > 1 else "demo"
    if mode == "demo":
        for name, case in DEMO_CASES.items():
            print(f"\n### {name}")
            print(format_text(engine.forward(case), sources, lang))
    elif mode == "interview":
        age = float(input("Age (years): "))
        base = {"age_months": age * 12}
        for f, label in (("temp_c", "Temperature C"), ("hr", "Heart rate"), ("rr", "Resp rate"), ("spo2", "SpO2")):
            v = input(f"{label} (Enter = unknown): ").strip()
            base[f] = float(v) if v else None
        base["pain_score"] = float(input("Pain 0-10 (Enter = 0): ") or 0)
        print(format_text(engine.backward(base, ask_cli(catalog, lang)), sources, lang))
    print("\n" + (DISCLAIMER_AR if lang == "ar" else DISCLAIMER_EN))


if __name__ == "__main__":
    main()
