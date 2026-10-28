# Medical Triage Expert System (Python)

نظام خبير للفرز الطبي الأولي — Rule-based، بقواعد مرتبطة بمصادر طبية رسمية.
**ليس تشخيصًا ولا بديلًا عن الطبيب.** / **Not a diagnosis; not a substitute for a doctor.**

## Run
```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v      # 18 tests
python main.py demo                          # sample cases (add: --lang en)
python main.py interview                     # CLI interview (backward chaining)
streamlit run ui/app.py                      # web UI (Arabic / English)
```

## Architecture
| Expert-system part | File |
|---|---|
| Knowledge Base (rules + sources) | `knowledge/rules.json` |
| Facts catalog (bilingual labels) | `knowledge/facts_catalog.json` |
| Working memory + Forward chaining + Backward chaining | `engine/inference.py` |
| Certainty Factors | `engine/certainty.py` |
| Age-based ESI danger-zone vitals | `engine/facts.py` |
| Explanation facility (rules + sources) | `engine/explain.py` |
| User interface | `ui/app.py`, `main.py` |

Decision policy: the most severe level supported by any fired rule wins (safety-first);
CFs of rules supporting that level are combined with `CF = CF1 + CF2*(1-CF1)`.

## Sources used (every rule cites at least one)
- AHRQ — Emergency Severity Index (ESI) v4 Implementation Handbook: https://www.ahrq.gov/research/esi/esihandbk.pdf
- NHS — Act FAST (stroke): https://www.nhs.uk/actFAST
- NHS Wales (BCUHB) — Signs of stroke: https://bcuhb.nhs.wales/services/hospital-services/stroke-service/signs-of-stroke-fast/
- NHS — Heart attack: https://www.nhs.uk/conditions/heart-attack/
- NHS — Chest pain: https://www.nhs.uk/symptoms/chest-pain/
- NHS — Anaphylaxis: https://www.nhs.uk/conditions/anaphylaxis/
- NHS — Angioedema: https://www.nhs.uk/conditions/angioedema/causes/
- NHS — Meningitis: https://www.nhs.uk/conditions/meningitis/
- NHS Nottingham & Nottinghamshire ICB — fever in babies under 3 months: see `rules.json`
- Also recommended for the report: ESI Handbook 5th edition (Emergency Nurses Association, 2023).

## Known limitations (state these in the report)
- Small knowledge base (25 rules): stroke, heart attack, anaphylaxis, meningitis/sepsis, breathing, infant fever, vital signs, severe pain.
- ESI levels 3-5 depend on a nurse's estimate of resources; this system only outputs a simplified "urgent" / "non-urgent default".
- UK (NHS) guidance is used for symptom red flags; emergency number for Egypt (123) must be verified locally.
- Rules must be reviewed by a licensed clinician before any real-world use.
- No patient data is stored.

## Add a rule
Add an object to `knowledge/rules.json` with `id`, `type` (`derive`/`conclude`), `if_all`/`if_any`, `then`, `cf`,
`sources` (ids from `sources`), and `reason_ar`/`reason_en`. Tests will fail if a source id is missing.
