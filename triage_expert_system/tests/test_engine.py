import random
import unittest

from engine.inference import InferenceEngine, NeedAnswer
from engine.kb import load_catalog, load_rules, load_sources

RULES, CATALOG, SOURCES = load_rules(), load_catalog(), load_sources()
ENGINE = InferenceEngine(RULES, CATALOG)
ADULT = 30 * 12


def fwd(**facts):
    facts.setdefault("age_months", ADULT)
    return ENGINE.forward(facts)


class TestKnowledgeBase(unittest.TestCase):
    def test_every_rule_has_valid_sources_and_bilingual_reasons(self):
        for r in RULES:
            self.assertTrue(r["sources"], r["id"])
            for s in r["sources"]:
                self.assertIn(s, SOURCES)
            self.assertTrue(r["reason_ar"] and r["reason_en"], r["id"])

    def test_rule_ids_unique(self):
        ids = [r["id"] for r in RULES]
        self.assertEqual(len(ids), len(set(ids)))


class TestForward(unittest.TestCase):
    def test_unresponsive_is_level_1(self):
        self.assertEqual(fwd(unresponsive=True)["level"], 1)

    def test_low_spo2_is_level_1(self):
        self.assertEqual(fwd(spo2=85)["level"], 1)

    def test_fast_sign_is_level_2(self):
        r = fwd(face_droop=True)
        self.assertEqual(r["level"], 2)
        self.assertIn("R-STROKE-FAST", [x["id"] for x in r["fired"]])

    def test_chest_pain_squeezing_is_level_2(self):
        self.assertEqual(fwd(chest_pain=True, chest_pain_tight_pressure=True)["level"], 2)

    def test_mild_chest_pain_only_is_level_3(self):
        self.assertEqual(fwd(chest_pain=True)["level"], 3)

    def test_pain_8_sprain_not_automatically_level_2(self):
        self.assertEqual(fwd(pain_score=8)["level"], 3)

    def test_no_symptoms_default_level_4(self):
        r = fwd()
        self.assertEqual(r["level"], 4)
        self.assertTrue(r["default"])

    def test_infant_fever_level_2_unless_post_vaccination(self):
        self.assertEqual(ENGINE.forward({"age_months": 2, "temp_c": 38.5})["level"], 2)
        self.assertEqual(ENGINE.forward({"age_months": 2, "temp_c": 38.5,
                                         "fever_after_vaccination_48h": True})["level"], 4)

    def test_danger_zone_vitals_by_age(self):
        self.assertEqual(fwd(hr=110)["level"], 2)                      # adult HR > 100
        self.assertEqual(ENGINE.forward({"age_months": 5 * 12, "hr": 110})["level"], 4)  # 3-8y limit is 140

    def test_cf_combination(self):
        r = fwd(chest_pain=True, chest_pain_tight_pressure=True, sweating=True)
        self.assertAlmostEqual(r["cf"], 0.85 + 0.85 * 0.15, places=4)

    def test_safety_first_most_severe_wins(self):
        self.assertEqual(fwd(unresponsive=True, pain_score=9, chest_pain=True)["level"], 1)

    def test_meningitis_rash(self):
        self.assertEqual(fwd(non_blanching_rash=True)["level"], 2)

    def test_anaphylaxis(self):
        self.assertEqual(fwd(swelling_lips_mouth_throat_tongue=True)["level"], 1)
        self.assertEqual(fwd(allergen_exposure_or_hives=True, throat_tight_difficulty_swallowing=True)["level"], 1)


class TestBackward(unittest.TestCase):
    def test_forward_and_backward_agree_on_random_cases(self):
        rng = random.Random(7)
        bools = [f for f, s in CATALOG.items() if s["kind"] == "input" and s["type"] == "bool"]
        for _ in range(600):
            world = {f: rng.random() < 0.12 for f in bools}
            world["age_months"] = rng.choice([1, 2, 6, 24, 60, 120, 400, 800])
            world["temp_c"] = rng.choice([None, 36.6, 38.2, 39.5])
            world["hr"] = rng.choice([None, 70, 105, 150, 190])
            world["rr"] = rng.choice([None, 16, 25, 45])
            world["spo2"] = rng.choice([None, 98, 91, 85])
            world["pain_score"] = rng.choice([0, 3, 7, 9])
            f = ENGINE.forward(world)
            b = ENGINE.backward({k: v for k, v in world.items() if CATALOG[k]["type"] == "number"},
                                lambda fact: world[fact])
            self.assertEqual(f["level"], b["level"], world)
            self.assertAlmostEqual(f["cf"], b["cf"], places=6, msg=str(world))

    def test_backward_asks_few_questions_for_clear_emergency(self):
        asked = []

        def ask(fact):
            asked.append(fact)
            return fact == "unresponsive"
        r = ENGINE.backward({"age_months": ADULT}, ask)
        self.assertEqual(r["level"], 1)
        self.assertLess(len(asked), 8)

    def test_need_answer_pattern(self):
        def ask(fact):
            raise NeedAnswer(fact)
        with self.assertRaises(NeedAnswer):
            ENGINE.backward({"age_months": ADULT}, ask)


if __name__ == "__main__":
    unittest.main()
