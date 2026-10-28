"""Inference engine: Forward Chaining (full data) and Backward Chaining (ask only what is needed).

Rule kinds (knowledge/rules.json):
  derive   : if conditions hold -> assert an intermediate fact (e.g. any_fast_sign)
  conclude : if conditions hold -> conclude a triage level with a Certainty Factor

Decision policy (safety-first): the most severe level (lowest number) that any rule supports wins.
CFs of all rules supporting that level are combined with CF = CF1 + CF2*(1-CF1).
"""
import operator

from .certainty import combine_all
from .facts import esi_danger_zone

OPS = {"==": operator.eq, ">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le}

DEFAULT_CF = 0.30


class NeedAnswer(Exception):
    """Raised by an 'ask' callback when the answer is not available yet (used by the UI)."""

    def __init__(self, fact):
        super().__init__(fact)
        self.fact = fact


def _norm(cond):
    if isinstance(cond, str):
        return {"fact": cond, "op": "==", "value": True}
    return cond


def _check(cond, value):
    cond = _norm(cond)
    if value is None:
        return False
    return OPS[cond["op"]](value, cond["value"])


class InferenceEngine:
    def __init__(self, rules, catalog):
        self.rules = rules
        self.catalog = catalog
        self.derive_rules = [r for r in rules if r["type"] == "derive"]
        self.conclude_rules = [r for r in rules if r["type"] == "conclude"]
        self.derived_facts = {r["then"]["fact"] for r in self.derive_rules}

    # ---------- helpers ----------
    def _default(self, fact):
        return False if self.catalog.get(fact, {}).get("type") == "bool" else None

    def _matches(self, rule, getter):
        for c in rule.get("if_all", []):
            c = _norm(c)
            if not _check(c, getter(c["fact"])):
                return False
        anys = rule.get("if_any", [])
        if not anys:
            return True
        for c in anys:
            c = _norm(c)
            if _check(c, getter(c["fact"])):
                return True
        return False

    def _result(self, level, fired, default=False, danger_details=None, level_cfs=None):
        if default:
            return {"level": 4, "cf": DEFAULT_CF, "fired": [], "default": True,
                    "level_cfs": {}, "danger_details": danger_details or []}
        winners = [r for r in fired if r["type"] == "conclude" and r["then"]["level"] == level]
        cf = combine_all(r["cf"] for r in winners)
        return {"level": level, "cf": cf, "fired": fired, "default": False,
                "level_cfs": level_cfs or {level: cf}, "danger_details": danger_details or []}

    # ---------- Forward chaining ----------
    def forward(self, answers):
        """answers: dict of known input facts (missing bool = False, missing number = unknown)."""
        wm = {f: self._default(f) for f, s in self.catalog.items() if s.get("kind") == "input"}
        wm.update(answers)
        flag, details = esi_danger_zone(wm.get("age_months"), wm.get("hr"), wm.get("rr"), wm.get("spo2"))
        wm["danger_zone_vitals"] = flag

        getter = lambda f: wm.get(f, self._default(f))
        fired, fired_ids, changed = [], set(), True
        while changed:  # run until no new rule fires (fixpoint)
            changed = False
            for r in self.rules:
                if r["id"] in fired_ids:
                    continue
                if self._matches(r, getter):
                    fired_ids.add(r["id"])
                    fired.append(r)
                    changed = True
                    if r["type"] == "derive":
                        wm[r["then"]["fact"]] = True

        concl = [r for r in fired if r["type"] == "conclude"]
        if not concl:
            return self._result(4, fired, default=True, danger_details=details)
        by_level = {}
        for r in concl:
            by_level.setdefault(r["then"]["level"], []).append(r["cf"])
        level_cfs = {lvl: combine_all(cfs) for lvl, cfs in by_level.items()}
        level = min(level_cfs)  # safety first: most severe level wins
        return self._result(level, fired, danger_details=details if flag else [], level_cfs=level_cfs)

    # ---------- Backward chaining ----------
    def backward(self, answers, ask):
        """Goal-driven: try to prove level 1, then 2, then 3. Facts are requested only when a rule needs them.

        ask(fact) -> True/False/number/None. May raise NeedAnswer(fact) (UI re-run pattern).
        """
        wm = dict(answers)
        fired, fired_ids, details = [], set(), []

        def note(rule):
            if rule["id"] not in fired_ids:
                fired_ids.add(rule["id"])
                fired.append(rule)

        def value(fact):
            if fact in wm:
                return wm[fact]
            if fact == "danger_zone_vitals":
                flag, det = esi_danger_zone(value("age_months"), value("hr"), value("rr"), value("spo2"))
                wm[fact] = flag
                details.extend(det)
                return flag
            if fact in self.derived_facts:
                res = False
                for dr in self.derive_rules:
                    if dr["then"]["fact"] == fact and self._matches(dr, value):
                        note(dr)
                        res = True
                        break
                wm[fact] = res
                return res
            v = ask(fact)
            if v is None and self.catalog.get(fact, {}).get("type") == "bool":
                v = False
            wm[fact] = v
            return v

        for level in (1, 2, 3):
            winners = [r for r in self.conclude_rules
                       if r["then"]["level"] == level and self._matches(r, value)]
            if winners:
                for r in winners:
                    note(r)
                return self._result(level, fired, danger_details=details)
        return self._result(4, fired, default=True, danger_details=details)
