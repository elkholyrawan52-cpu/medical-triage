#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Medical Triage Expert System - SINGLE FILE VERSION
نظام خبير للفرز الطبي الأولي - ملف واحد

Run / التشغيل:
    python triage.py              -> text menu (demo / interview / UI / tests)
    python triage.py demo         -> sample cases        (add: --lang en)
    python triage.py interview    -> CLI interview (backward chaining)
    python triage.py test         -> self-tests
    python triage.py ui           -> launches the web UI (needs: pip install streamlit)
    (add  --region EG|GB|US|AU|NZ|SG|OTHER  to choose the emergency number; default EG = 123)
    streamlit run triage.py       -> web UI directly

Parts of the expert system inside this file:
    1) Knowledge Base  : SOURCES / FACTS_CATALOG / RULES (every rule cites an official source)
    2) Inference Engine: forward chaining + backward chaining + Certainty Factors
    3) Explanation     : rules that fired + sources
    4) Emergency guidance: ambulance number by region + pre-arrival first aid (sourced)
    5) Voice           : read-aloud (browser + gTTS) and voice answers (SpeechRecognition)
    6) Interfaces      : CLI + Streamlit web UI (Arabic / English, light + dark theme)

Optional voice libraries (the app works without them):  pip install gTTS SpeechRecognition

NOT a diagnosis and NOT a substitute for a doctor. Rules must be reviewed by a licensed clinician
before any real-world use. No patient data is stored.
"""
import operator
import random
import subprocess
import sys

# =====================================================================================
# 1) KNOWLEDGE BASE
# =====================================================================================

SOURCES = {'ESI_V4': {'title': 'Emergency Severity Index (ESI) v4 Implementation Handbook, Chapter 3',
            'org': 'AHRQ (U.S. Dept. of Health & Human Services)',
            'url': 'https://www.ahrq.gov/research/esi/esihandbk.pdf'},
 'NHS_FAST': {'title': 'Symptoms of a stroke (Act FAST)', 'org': 'NHS (UK)', 'url': 'https://www.nhs.uk/actFAST'},
 'NHS_STROKE_WALES': {'title': 'Signs of stroke - FAST',
                      'org': 'Betsi Cadwaladr University Health Board (NHS Wales)',
                      'url': 'https://bcuhb.nhs.wales/services/hospital-services/stroke-service/signs-of-stroke-fast/'},
 'NHS_HEART_ATTACK': {'title': 'Heart attack',
                      'org': 'NHS (UK)',
                      'url': 'https://www.nhs.uk/conditions/heart-attack/'},
 'NHS_CHEST_PAIN': {'title': 'Chest pain', 'org': 'NHS (UK)', 'url': 'https://www.nhs.uk/symptoms/chest-pain/'},
 'NHS_ANAPHYLAXIS': {'title': 'Anaphylaxis', 'org': 'NHS (UK)', 'url': 'https://www.nhs.uk/conditions/anaphylaxis/'},
 'NHS_ANGIOEDEMA': {'title': 'Angioedema',
                    'org': 'NHS (UK)',
                    'url': 'https://www.nhs.uk/conditions/angioedema/causes/'},
 'NHS_MENINGITIS': {'title': 'Meningitis', 'org': 'NHS (UK)', 'url': 'https://www.nhs.uk/conditions/meningitis/'},
 'NOTTS_ICB_FEVER': {'title': 'Concerned your child is unwell - meningitis (fever in babies under 3 months)',
                     'org': 'NHS Nottingham and Nottinghamshire ICB',
                     'url': 'https://notts.icb.nhs.uk/your-services/childrens-health-and-wellbeing/concerned-your-child-is-unwell-3-months-and-older/meningitis/'},
 'SYSTEM_DEFAULT': {'title': 'System default when no red-flag rule fires (not a clinical source)',
                    'org': 'This project',
                    'url': ''}}

FACTS_CATALOG = {'age_months': {'type': 'number', 'kind': 'input', 'group': 'vitals', 'ar': 'العمر بالشهور', 'en': 'Age in months'},
 'temp_c': {'type': 'number',
            'kind': 'input',
            'group': 'vitals',
            'ar': 'درجة الحرارة (°م)',
            'en': 'Temperature (°C)'},
 'hr': {'type': 'number', 'kind': 'input', 'group': 'vitals', 'ar': 'النبض (ضربة/دقيقة)', 'en': 'Heart rate (bpm)'},
 'rr': {'type': 'number',
        'kind': 'input',
        'group': 'vitals',
        'ar': 'معدل التنفس (نفس/دقيقة)',
        'en': 'Respiratory rate (breaths/min)'},
 'spo2': {'type': 'number',
          'kind': 'input',
          'group': 'vitals',
          'ar': 'تشبّع الأكسجين SpO2 (%)',
          'en': 'Oxygen saturation SpO2 (%)'},
 'pain_score': {'type': 'number',
                'kind': 'input',
                'group': 'vitals',
                'ar': 'شدة الألم من 0 إلى 10',
                'en': 'Pain score 0-10'},
 'unresponsive': {'type': 'bool',
                  'kind': 'input',
                  'group': 'consciousness',
                  'ar': 'فاقد الوعي أو مش بيستجيب خالص',
                  'en': 'Unresponsive / cannot be woken'},
 'new_confusion': {'type': 'bool',
                   'kind': 'input',
                   'group': 'consciousness',
                   'ar': 'تشوش أو تخليط أو نعاس شديد جديد (تغيّر مفاجئ عن المعتاد)',
                   'en': 'New confusion, disorientation or extreme drowsiness (sudden change from normal)'},
 'seizure_first_time': {'type': 'bool',
                        'kind': 'input',
                        'group': 'consciousness',
                        'ar': 'تشنجات لأول مرة في حياته',
                        'en': 'First-ever seizure (fit)'},
 'severe_respiratory_distress': {'type': 'bool',
                                 'kind': 'input',
                                 'group': 'breathing',
                                 'ar': 'صعوبة شديدة في التنفس (بيلهث أو مش قادر يكمّل جملة)',
                                 'en': 'Severe difficulty breathing (gasping, choking, cannot get words out)'},
 'sudden_more_breathless': {'type': 'bool',
                            'kind': 'input',
                            'group': 'breathing',
                            'ar': 'ضيق النفس زاد فجأة عن المعتاد',
                            'en': 'Suddenly more short of breath than usual'},
 'shortness_of_breath': {'type': 'bool',
                         'kind': 'input',
                         'group': 'breathing',
                         'ar': 'ضيق في النفس',
                         'en': 'Shortness of breath'},
 'chest_pain': {'type': 'bool',
                'kind': 'input',
                'group': 'chest',
                'ar': 'ألم أو انزعاج في الصدر',
                'en': 'Chest pain or discomfort'},
 'chest_pain_tight_pressure': {'type': 'bool',
                               'kind': 'input',
                               'group': 'chest',
                               'ar': 'الألم زي ضغط أو عصر أو تقل على الصدر',
                               'en': 'Pain feels tight, squeezing, heavy or like pressure'},
 'chest_pain_spreads': {'type': 'bool',
                        'kind': 'input',
                        'group': 'chest',
                        'ar': 'الألم بينتشر للذراع أو الرقبة أو الفك أو الضهر',
                        'en': 'Pain spreads to arm, neck, jaw or back'},
 'chest_pain_over_15min': {'type': 'bool',
                           'kind': 'input',
                           'group': 'chest',
                           'ar': 'الألم مستمر أكتر من 15 دقيقة',
                           'en': 'Pain lasting more than 15 minutes'},
 'sweating': {'type': 'bool', 'kind': 'input', 'group': 'chest', 'ar': 'عرق بارد أو غزير', 'en': 'Sweating'},
 'nausea_vomiting': {'type': 'bool',
                     'kind': 'input',
                     'group': 'chest',
                     'ar': 'غثيان أو قيء',
                     'en': 'Feeling or being sick'},
 'lightheaded': {'type': 'bool',
                 'kind': 'input',
                 'group': 'chest',
                 'ar': 'دوخة أو إحساس بالإغماء',
                 'en': 'Lightheaded or faint'},
 'pale_blue_grey_skin': {'type': 'bool',
                         'kind': 'input',
                         'group': 'chest',
                         'ar': 'جلد شاحب أو أزرق أو رمادي (الشفايف/اللسان/راحة اليد)',
                         'en': 'Pale, blue or grey skin (lips, tongue, palms)'},
 'face_droop': {'type': 'bool',
                'kind': 'input',
                'group': 'neuro',
                'ar': 'ميلان أو ارتخاء في جانب من الوجه / مش قادر يبتسم',
                'en': 'Face drooping on one side / cannot smile'},
 'arm_weakness': {'type': 'bool',
                  'kind': 'input',
                  'group': 'neuro',
                  'ar': 'مش قادر يرفع الدراعين ويثبتهم (ضعف أو تنميل في دراع)',
                  'en': 'Cannot raise both arms and keep them there (weakness/numbness in one arm)'},
 'slurred_speech': {'type': 'bool',
                    'kind': 'input',
                    'group': 'neuro',
                    'ar': 'كلام غير واضح أو تلعثم أو تخليط في الكلام',
                    'en': 'Slurred speech or sounds confused'},
 'sudden_one_sided_weakness_numbness': {'type': 'bool',
                                        'kind': 'input',
                                        'group': 'neuro',
                                        'ar': 'ضعف أو تنميل مفاجئ في الوجه أو الذراع أو الرجل في جانب واحد',
                                        'en': 'Sudden weakness or numbness of face, arm or leg on one side'},
 'sudden_vision_loss': {'type': 'bool',
                        'kind': 'input',
                        'group': 'neuro',
                        'ar': 'فقدان أو زغللة مفاجئة في النظر',
                        'en': 'Sudden loss or blurring of vision'},
 'worst_headache_of_life': {'type': 'bool',
                            'kind': 'input',
                            'group': 'neuro',
                            'ar': 'أسوأ صداع في حياته وجه فجأة',
                            'en': "Sudden 'worst headache of my life'"},
 'swelling_lips_mouth_throat_tongue': {'type': 'bool',
                                       'kind': 'input',
                                       'group': 'allergy',
                                       'ar': 'ورم مفاجئ في الشفايف أو الفم أو الحلق أو اللسان',
                                       'en': 'Sudden swelling of lips, mouth, throat or tongue'},
 'throat_tight_difficulty_swallowing': {'type': 'bool',
                                        'kind': 'input',
                                        'group': 'allergy',
                                        'ar': 'ضيق في الحلق أو صعوبة في البلع',
                                        'en': 'Tight throat or difficulty swallowing'},
 'allergen_exposure_or_hives': {'type': 'bool',
                                'kind': 'input',
                                'group': 'allergy',
                                'ar': 'اتعرّض لمسبب حساسية (أكل/دواء/لدغة) أو ظهر طفح وهرش',
                                'en': 'Exposed to an allergen (food/medicine/sting) or has itchy raised rash '
                                      '(hives)'},
 'stiff_neck': {'type': 'bool', 'kind': 'input', 'group': 'infection', 'ar': 'تيبّس في الرقبة', 'en': 'Stiff neck'},
 'photophobia': {'type': 'bool',
                 'kind': 'input',
                 'group': 'infection',
                 'ar': 'مش قادر يبص للضوء القوي',
                 'en': 'Cannot look at bright lights'},
 'non_blanching_rash': {'type': 'bool',
                        'kind': 'input',
                        'group': 'infection',
                        'ar': 'طفح أو بقع حمراء/بنفسجية ما بتختفيش لما تضغط عليها بكوباية شفافة (Glass test)',
                        'en': 'Rash that does not fade when a clear glass is pressed on it (glass test)'},
 'fever_after_vaccination_48h': {'type': 'bool',
                                 'kind': 'input',
                                 'group': 'infection',
                                 'ar': 'الحرارة ظهرت خلال 48 ساعة بعد تطعيم',
                                 'en': 'Fever started within 48 hours after a vaccination'},
 'danger_zone_vitals': {'type': 'bool',
                        'kind': 'computed',
                        'ar': 'علامات حيوية خارج الحدود الآمنة للعمر (ESI)',
                        'en': 'Danger-zone vital signs for age (ESI)'},
 'any_fast_sign': {'type': 'bool', 'kind': 'derived', 'ar': 'علامة FAST', 'en': 'Any FAST sign'},
 'respiratory_failure_sign': {'type': 'bool',
                              'kind': 'derived',
                              'ar': 'علامة فشل تنفسي',
                              'en': 'Respiratory failure sign'},
 'meningitis_red_flag': {'type': 'bool',
                         'kind': 'derived',
                         'ar': 'علامة خطر التهاب سحائي/إنتان',
                         'en': 'Meningitis/sepsis red flag'},
 'acs_pattern': {'type': 'bool',
                 'kind': 'derived',
                 'ar': 'نمط ألم صدر مشتبه بالقلب',
                 'en': 'Heart-attack pattern chest pain'},
 'acs_associated': {'type': 'bool',
                    'kind': 'derived',
                    'ar': 'ألم صدر مع أعراض مصاحبة',
                    'en': 'Chest pain with associated symptoms'},
 'anaphylaxis_pattern': {'type': 'bool', 'kind': 'derived', 'ar': 'نمط صدمة تحسسية', 'en': 'Anaphylaxis pattern'}}

RULES = [{'id': 'D-FAST',
  'type': 'derive',
  'if_any': ['face_droop', 'arm_weakness', 'slurred_speech'],
  'then': {'fact': 'any_fast_sign'},
  'sources': ['NHS_FAST'],
  'reason_ar': 'أي علامة واحدة من FAST (الوجه/الذراع/الكلام) كافية لاشتباه السكتة الدماغية',
  'reason_en': 'Any single FAST sign (face, arms, speech) is enough to suspect a stroke'},
 {'id': 'D-RESP-FAIL',
  'type': 'derive',
  'if_any': [{'fact': 'spo2', 'op': '<', 'value': 90}, 'severe_respiratory_distress'],
  'then': {'fact': 'respiratory_failure_sign'},
  'sources': ['ESI_V4'],
  'reason_ar': 'تشبّع الأكسجين أقل من 90% أو ضيق تنفس شديد يعني احتياج لتدخل فوري للحفاظ على التنفس',
  'reason_en': 'SpO2 below 90% or severe respiratory distress needs immediate intervention to maintain oxygenation'},
 {'id': 'D-MENING-RASH',
  'type': 'derive',
  'if_all': ['non_blanching_rash'],
  'then': {'fact': 'meningitis_red_flag'},
  'sources': ['NHS_MENINGITIS'],
  'reason_ar': 'طفح لا يختفي بالضغط (اختبار الكوباية) قد يدل على تسمم دموي/التهاب سحائي',
  'reason_en': 'A rash that does not fade under a glass may indicate meningococcal septicaemia'},
 {'id': 'D-MENING-NECK',
  'type': 'derive',
  'if_all': ['stiff_neck', 'photophobia'],
  'then': {'fact': 'meningitis_red_flag'},
  'sources': ['NHS_MENINGITIS'],
  'reason_ar': 'تيبّس الرقبة مع عدم القدرة على النظر للضوء من علامات الالتهاب السحائي',
  'reason_en': 'Stiff neck with inability to look at bright lights is a meningitis warning sign'},
 {'id': 'D-ACS-PATTERN',
  'type': 'derive',
  'if_all': ['chest_pain'],
  'if_any': ['chest_pain_tight_pressure', 'chest_pain_spreads', 'chest_pain_over_15min'],
  'then': {'fact': 'acs_pattern'},
  'sources': ['NHS_HEART_ATTACK', 'NHS_CHEST_PAIN'],
  'reason_ar': 'ألم صدر ضاغط/معصور أو ينتشر للذراع/الرقبة/الفك أو يستمر أكتر من 15 دقيقة',
  'reason_en': 'Chest pain that is tight/squeezing, spreads to arms/neck/jaw, or lasts over 15 minutes'},
 {'id': 'D-ACS-ASSOC',
  'type': 'derive',
  'if_all': ['chest_pain'],
  'if_any': ['sweating', 'nausea_vomiting', 'lightheaded', 'shortness_of_breath'],
  'then': {'fact': 'acs_associated'},
  'sources': ['NHS_CHEST_PAIN'],
  'reason_ar': 'ألم صدر مصحوب بعرق أو غثيان أو دوخة أو ضيق نفس',
  'reason_en': 'Chest pain together with sweating, feeling sick, light-headedness or shortness of breath'},
 {'id': 'D-ANAPH',
  'type': 'derive',
  'if_all': ['allergen_exposure_or_hives'],
  'if_any': ['throat_tight_difficulty_swallowing', 'severe_respiratory_distress'],
  'then': {'fact': 'anaphylaxis_pattern'},
  'sources': ['NHS_ANAPHYLAXIS'],
  'reason_ar': 'تعرّض لمسبب حساسية أو طفح مع ضيق في الحلق/صعوبة بلع/صعوبة تنفس',
  'reason_en': 'Allergen exposure or hives together with throat tightness, difficulty swallowing or breathing'},
 {'id': 'R-ESI1-UNRESP',
  'type': 'conclude',
  'if_all': ['unresponsive'],
  'then': {'level': 1},
  'cf': 0.95,
  'sources': ['ESI_V4'],
  'reason_ar': 'المريض فاقد الوعي/لا يستجيب: بيحتاج تدخل منقذ للحياة فورًا (ESI مستوى 1)',
  'reason_en': 'Unresponsive patient needs immediate life-saving intervention (ESI level 1)'},
 {'id': 'R-ESI1-RESP',
  'type': 'conclude',
  'if_all': ['respiratory_failure_sign'],
  'then': {'level': 1},
  'cf': 0.9,
  'sources': ['ESI_V4'],
  'reason_ar': 'فشل تنفسي: SpO2 أقل من 90% أو ضيق تنفس شديد (ESI مستوى 1)',
  'reason_en': 'Respiratory failure: SpO2 below 90% or severe respiratory distress (ESI level 1)'},
 {'id': 'R-ESI1-CHEST-SHOCK',
  'type': 'conclude',
  'if_all': ['chest_pain', 'sweating', 'pale_blue_grey_skin'],
  'then': {'level': 1},
  'cf': 0.85,
  'sources': ['ESI_V4', 'NHS_HEART_ATTACK'],
  'reason_ar': 'ألم صدر مع شحوب وعرق: ESI يعتبره مستوى 1 لأنه قد يحتاج تدخل فوري',
  'reason_en': 'Chest pain with pallor and sweating meets ESI level-1 criteria'},
 {'id': 'R-ANAPH-SWELL',
  'type': 'conclude',
  'if_all': ['swelling_lips_mouth_throat_tongue'],
  'then': {'level': 1},
  'cf': 0.9,
  'sources': ['NHS_ANGIOEDEMA', 'NHS_ANAPHYLAXIS'],
  'reason_ar': 'ورم مفاجئ في الشفايف/الفم/الحلق/اللسان: NHS توصي بالاتصال بالإسعاف فورًا',
  'reason_en': 'Sudden swelling of lips, mouth, throat or tongue: NHS advises calling emergency services '
               'immediately'},
 {'id': 'R-ANAPH-PATTERN',
  'type': 'conclude',
  'if_all': ['anaphylaxis_pattern'],
  'then': {'level': 1},
  'cf': 0.9,
  'sources': ['NHS_ANAPHYLAXIS'],
  'reason_ar': 'أعراض صدمة تحسسية محتملة (anaphylaxis): حالة طوارئ طبية',
  'reason_en': 'Possible anaphylaxis: a medical emergency'},
 {'id': 'R-STROKE-FAST',
  'type': 'conclude',
  'if_all': ['any_fast_sign'],
  'then': {'level': 2},
  'cf': 0.9,
  'sources': ['NHS_FAST', 'ESI_V4'],
  'reason_ar': 'اشتباه سكتة دماغية (FAST): اتصل بالإسعاف فورًا حتى لو العرض بسيط',
  'reason_en': 'Suspected stroke (FAST): call emergency services immediately even if symptoms seem mild'},
 {'id': 'R-STROKE-SUDDEN',
  'type': 'conclude',
  'if_any': ['sudden_one_sided_weakness_numbness', 'sudden_vision_loss'],
  'then': {'level': 2},
  'cf': 0.8,
  'sources': ['NHS_STROKE_WALES'],
  'reason_ar': 'ضعف/تنميل مفاجئ في جانب واحد أو فقدان مفاجئ للنظر من أعراض السكتة',
  'reason_en': 'Sudden one-sided weakness/numbness or sudden vision loss are stroke symptoms'},
 {'id': 'R-ACS-PATTERN',
  'type': 'conclude',
  'if_all': ['acs_pattern'],
  'then': {'level': 2},
  'cf': 0.85,
  'sources': ['NHS_HEART_ATTACK', 'NHS_CHEST_PAIN', 'ESI_V4'],
  'reason_ar': 'نمط ألم صدر مشتبه بنوبة قلبية: ESI مستوى 2 (يحتاج رسم قلب خلال 10 دقائق)',
  'reason_en': 'Chest pain pattern suspicious for a heart attack: ESI level 2 (ECG within 10 minutes)'},
 {'id': 'R-ACS-ASSOC',
  'type': 'conclude',
  'if_all': ['acs_associated'],
  'then': {'level': 2},
  'cf': 0.85,
  'sources': ['NHS_CHEST_PAIN'],
  'reason_ar': 'ألم صدر مع أعراض مصاحبة (عرق/غثيان/دوخة/ضيق نفس): قد تكون نوبة قلبية',
  'reason_en': 'Chest pain with associated symptoms could be a heart attack'},
 {'id': 'R-MENING',
  'type': 'conclude',
  'if_all': ['meningitis_red_flag'],
  'then': {'level': 2},
  'cf': 0.85,
  'sources': ['NHS_MENINGITIS'],
  'reason_ar': 'علامات خطر التهاب سحائي/تسمم دموي: اطلب الإسعاف ولا تنتظر ظهور باقي الأعراض',
  'reason_en': 'Meningitis/septicaemia red flags: call emergency services; do not wait for other symptoms'},
 {'id': 'R-HEADACHE',
  'type': 'conclude',
  'if_all': ['worst_headache_of_life'],
  'then': {'level': 2},
  'cf': 0.8,
  'sources': ['ESI_V4'],
  'reason_ar': 'أسوأ صداع في الحياة بشكل مفاجئ: ESI يعتبره موقف عالي الخطورة (احتمال نزيف دماغي)',
  'reason_en': "Sudden 'worst headache of my life' is an ESI high-risk situation (possible brain bleed)"},
 {'id': 'R-CONFUSION',
  'type': 'conclude',
  'if_all': ['new_confusion'],
  'then': {'level': 2},
  'cf': 0.8,
  'sources': ['ESI_V4'],
  'reason_ar': 'تغيّر حاد في الوعي (تشوش/نعاس شديد): ESI مستوى 2',
  'reason_en': 'Acute change in mental status (confused/lethargic/disoriented): ESI level 2'},
 {'id': 'R-SEIZURE',
  'type': 'conclude',
  'if_all': ['seizure_first_time'],
  'then': {'level': 2},
  'cf': 0.7,
  'sources': ['NHS_MENINGITIS'],
  'reason_ar': 'تشنج لأول مرة ضمن العلامات التي توصي NHS فيها بالإسعاف',
  'reason_en': 'A first-ever seizure is among the signs for which NHS advises calling 999'},
 {'id': 'R-INFANT-FEVER',
  'type': 'conclude',
  'if_all': [{'fact': 'age_months', 'op': '<', 'value': 3},
             {'fact': 'temp_c', 'op': '>=', 'value': 38},
             {'fact': 'fever_after_vaccination_48h', 'op': '==', 'value': False}],
  'then': {'level': 2},
  'cf': 0.85,
  'sources': ['NOTTS_ICB_FEVER', 'ESI_V4'],
  'reason_ar': 'رضيع أقل من 3 شهور بحرارة 38 أو أكتر: يحتاج طوارئ فورًا (إلا لو الحرارة خلال 48 ساعة من تطعيم بدون '
               'علامات خطر أخرى)',
  'reason_en': 'Baby under 3 months with temperature of 38C or above needs urgent hospital care (unless fever within '
               '48h of vaccination with no other red features)'},
 {'id': 'R-VITALS-DZ',
  'type': 'conclude',
  'if_all': ['danger_zone_vitals'],
  'then': {'level': 2},
  'cf': 0.6,
  'sources': ['ESI_V4'],
  'reason_ar': 'العلامات الحيوية خارج الحدود الآمنة للعمر: ESI يوصي بالنظر في رفع الأولوية لمستوى 2',
  'reason_en': 'Vital signs outside the danger-zone limits for age: ESI advises considering upgrade to level 2'},
 {'id': 'R-BREATH-SUDDEN',
  'type': 'conclude',
  'if_all': ['sudden_more_breathless'],
  'then': {'level': 3},
  'cf': 0.7,
  'sources': ['NHS_HEART_ATTACK'],
  'reason_ar': 'ضيق نفس زاد فجأة عن المعتاد: محتاج مشورة طبية عاجلة',
  'reason_en': 'Suddenly more short of breath than usual: needs urgent medical advice'},
 {'id': 'R-CHEST-ANY',
  'type': 'conclude',
  'if_all': ['chest_pain'],
  'then': {'level': 3},
  'cf': 0.5,
  'sources': ['NHS_CHEST_PAIN'],
  'reason_ar': 'أي ألم في الصدر لازم يتقيّم طبيًا حتى لو غالبًا مش خطير',
  'reason_en': 'Any chest pain should get medical advice, even though most cases are not serious'},
 {'id': 'R-PAIN-SEVERE',
  'type': 'conclude',
  'if_all': [{'fact': 'pain_score', 'op': '>=', 'value': 7}],
  'then': {'level': 3},
  'cf': 0.6,
  'sources': ['ESI_V4'],
  'reason_ar': 'ألم شديد (7/10 أو أكتر): ESI يسمح للممرض بترفيعه لمستوى 2 حسب التقدير السريري',
  'reason_en': 'Severe pain (7/10 or more): ESI lets the triage nurse upgrade to level 2 by clinical judgment'}]

# ---- Triage levels. {call} = ambulance number of the selected region (see REGIONS) ----
LEVELS = {
    1: {
        "color": "#b71c1c",
        "name_ar": "طوارئ فورية (ESI 1)", "name_en": "Immediate - life threatening (ESI 1)",
        "advice_ar": "اتصل بالإسعاف فورًا: {call}. اتبع خطوات الإسعاف الأولي اللي تحت لحد ما الإسعاف يوصل، ومشغل الإسعاف هيوجّهك على التليفون.",
        "advice_en": "Call emergency services now: {call}. Follow the first-aid steps below until help arrives; the call handler will guide you on the phone.",
    },
    2: {
        "color": "#e65100",
        "name_ar": "طارئ عالي الخطورة (ESI 2)", "name_en": "Emergent - high risk (ESI 2)",
        "advice_ar": "اطلب الإسعاف فورًا أو روح الطوارئ: {call}. الحالة ما ينفعش تستنى. اتبع خطوات الإسعاف الأولي اللي تحت لحد ما الإسعاف يوصل.",
        "advice_en": "Call emergency services or go to the emergency department now: {call}. This should not wait. Follow the first-aid steps below until help arrives.",
    },
    3: {
        "color": "#f9a825",
        "name_ar": "عاجل - محتاج تقييم طبي النهارده", "name_en": "Urgent - needs medical assessment today",
        "advice_ar": "كلّم الطبيب أو روح عيادة/طوارئ النهارده. لو الأعراض زادت أو ظهرت علامات خطر اطلب الإسعاف: {call}.",
        "advice_en": "Speak to a doctor or visit a clinic/emergency department today. If symptoms worsen or red flags appear, call emergency services: {call}.",
    },
    4: {
        "color": "#2e7d32",
        "name_ar": "غير عاجل - لم تظهر علامات خطر", "name_en": "Non-urgent - no red flags found",
        "advice_ar": "النظام ما لقاش علامات خطر من قاعدة معرفته المحدودة. ده مش تأكيد إنك بخير: لو الأعراض استمرت أو زادت راجع طبيب، ولو ظهرت علامات خطر اتصل: {call}.",
        "advice_en": "No red flags were found in this system's limited knowledge base. This is not a guarantee you are well: see a doctor if symptoms persist or worsen, and call {call} if red flags appear.",
    },
}

DISCLAIMER_AR = "⚠️ هذا النظام مساعد فرز تعليمي وليس تشخيصًا ولا بديلًا عن الطبيب. في أي شك أو حالة طارئة اتصل بالإسعاف."
DISCLAIMER_EN = "⚠️ This is an educational triage-support tool, not a diagnosis and not a substitute for a doctor. If in doubt or in an emergency, call emergency services."
FIRST_AID_NOTE_AR = "خطوات الإسعاف الأولي دي لا تغني عن مكالمة الإسعاف ولا عن تدريب إسعافات أولية. لو مشغل الإسعاف قالك حاجة مختلفة، اتبع كلامه."
FIRST_AID_NOTE_EN = "These first-aid steps do not replace calling the ambulance or first-aid training. If the call handler tells you something different, follow the call handler."

# =====================================================================================
# 1b) EMERGENCY NUMBERS BY REGION  (ambulance number is shown big in the UI)
# Only numbers that were confirmed in the cited sources are included. 'OTHER' has no number on purpose.
# =====================================================================================

DEFAULT_REGION = "EG"

REGIONS = {
    "EG": {
        "flag": "🇪🇬", "name_ar": "مصر", "name_en": "Egypt",
        "ambulance": "123", "police": "122", "fire": "180",
        "note_ar": "123 هو رقم هيئة الإسعاف المصرية، متاح 24 ساعة، وحالات الطوارئ والحوادث بدون رسوم.",
        "note_en": "123 is the Egyptian Ambulance Organisation number: open 24 hours, emergencies and accidents carry no fees.",
        "sources": ["AUC_EGYPT_EMERGENCY", "THERAPYROUTE_EG", "WIKI_EG_PHONE"],
    },
    "GB": {
        "flag": "🇬🇧", "name_ar": "المملكة المتحدة", "name_en": "United Kingdom",
        "ambulance": "999", "police": None, "fire": None,
        "note_ar": "999 للإسعاف في بريطانيا (112 بيشتغل كمان).", "note_en": "999 for an ambulance in the UK (112 also works).",
        "sources": ["NHS_HEART_ATTACK", "SJA_HEART_ATTACK"],
    },
    "US": {
        "flag": "🇺🇸", "name_ar": "أمريكا / كندا", "name_en": "USA / Canada",
        "ambulance": "911", "police": None, "fire": None,
        "note_ar": "911 للطوارئ في أمريكا وكندا.", "note_en": "911 for emergencies in the USA and Canada.",
        "sources": ["REDCROSS_CA_FACTS", "MEDLINEPLUS_BREATHING"],
    },
    "AU": {
        "flag": "🇦🇺", "name_ar": "أستراليا", "name_en": "Australia",
        "ambulance": "000", "police": None, "fire": None,
        "note_ar": "000 (Triple Zero) للإسعاف في أستراليا.", "note_en": "000 (Triple Zero) for an ambulance in Australia.",
        "sources": ["STJOHN_AU_STROKE"],
    },
    "NZ": {
        "flag": "🇳🇿", "name_ar": "نيوزيلندا", "name_en": "New Zealand",
        "ambulance": "111", "police": None, "fire": None,
        "note_ar": "111 للطوارئ في نيوزيلندا.", "note_en": "111 for emergencies in New Zealand.",
        "sources": ["STJOHN_NZ_STROKE"],
    },
    "SG": {
        "flag": "🇸🇬", "name_ar": "سنغافورة", "name_en": "Singapore",
        "ambulance": "995", "police": None, "fire": None,
        "note_ar": "995 للإسعاف في سنغافورة.", "note_en": "995 for an ambulance in Singapore.",
        "sources": ["NHCS_STROKE"],
    },
    "OTHER": {
        "flag": "🌍", "name_ar": "دولة تانية", "name_en": "Other country",
        "ambulance": None, "police": None, "fire": None,
        "note_ar": "اتصل برقم الطوارئ المحلي في بلدك.", "note_en": "Call your local emergency number.",
        "sources": [],
    },
}

# =====================================================================================
# 1c) FIRST-AID KNOWLEDGE (pre-arrival instructions). Every protocol cites its sources.
# Triggered by the rules that fired at triage level 1-2 (see 'triggers').
# =====================================================================================

SOURCES.update({
    "AUC_EGYPT_EMERGENCY": {"title": "Emergencies: public emergency numbers (ambulance 123, police 122, civil defense 180)",
                            "org": "The American University in Cairo", "url": "https://aucegypt.edu/faculty-and-staff/housing/services/emergencies"},
    "THERAPYROUTE_EG": {"title": "Egypt emergency numbers (quotes the Egyptian Ambulance Organisation: 123, 24h, no fees for emergencies)",
                        "org": "TherapyRoute (secondary source)", "url": "https://www.therapyroute.com/article/suicide-hotlines-and-crisis-lines-in-egypt-by-therapyroute"},
    "WIKI_EG_PHONE": {"title": "Telephone numbers in Egypt", "org": "Wikipedia (secondary source)",
                      "url": "https://en.wikipedia.org/wiki/Telephone_numbers_in_Egypt"},
    "STJOHN_AU_STROKE": {"title": "First aid fact sheet: stroke (call Triple Zero 000)", "org": "St John Ambulance Australia",
                         "url": "https://stjohn.org.au/app/uploads/2025/08/Fact-sheets_stroke.pdf"},
    "STJOHN_NZ_STROKE": {"title": "First Aid Library: stroke (call 111)", "org": "St John New Zealand",
                         "url": "https://www.stjohn.org.nz/First-Aid/First-Aid-Library/Stroke"},
    "NHCS_STROKE": {"title": "Early signs of stroke: what to watch for (call ambulance 995, note the time symptoms started)",
                    "org": "National Heart Centre Singapore", "url": "https://www.myheart.org.sg/heart-news/early-signs-of-stroke-what-to-watch-for/"},
    "REDCROSS_CA_FACTS": {"title": "First aid facts over myths: what to do in an emergency", "org": "Canadian Red Cross",
                          "url": "https://www.redcross.ca/training-and-certification/first-aid-tips-and-resources/first-aid-tips/first-aid-safety/facts-over-myths"},
    "MEDLINEPLUS_BREATHING": {"title": "Breathing difficulties - first aid", "org": "MedlinePlus (U.S. National Library of Medicine)",
                              "url": "https://medlineplus.gov/ency/article/000007.htm"},
    "SJA_HEART_ATTACK": {"title": "Heart attack: first aid advice", "org": "St John Ambulance (UK)",
                         "url": "https://www.sja.org.uk/first-aid-advice/heart-attack/"},
    "SJA_CYMRU_GUIDE": {"title": "Bilingual First Aid Pocket Guide (2024)", "org": "St John Cymru Wales",
                        "url": "https://www.sjacymru.org.uk/image/documents/Bilingual%20First%20Aid%20Pocket%20Guide%20-%20Inside%20%28PRINT%29%202024_compressed.pdf"},
    "NWAS_LEAFLET": {"title": "First aid facts: what to do when...", "org": "North West Ambulance Service NHS Trust",
                     "url": "https://www.nwas.nhs.uk/content/uploads/2019/04/nwas-first-aid-facts-a5-leaflet.pdf"},
    "BHF_HEART_ATTACK": {"title": "Heart attack", "org": "British Heart Foundation",
                         "url": "https://www.bhf.org.uk/informationsupport/conditions/heart-attack"},
    "NIDIRECT_HEART_ATTACK": {"title": "Heart attack", "org": "NI Direct (Northern Ireland government health information)",
                              "url": "https://www.nidirect.gov.uk/conditions/heart-attack"},
    "SJA_STROKE": {"title": "Stroke: first aid advice", "org": "St John Ambulance (UK)",
                   "url": "https://www.sja.org.uk/get-advice/first-aid-advice/stroke"},
    "BRC_STROKE": {"title": "First aid for someone who may be having a stroke", "org": "British Red Cross",
                   "url": "https://redcross.org.uk/first-aid/learn-first-aid/stroke"},
    "ANAPHYLAXIS_UK": {"title": "What to do in an emergency (anaphylaxis)", "org": "Anaphylaxis UK",
                       "url": "https://www.anaphylaxis.org.uk/what-to-do-in-an-emergency/"},
    "NICE_QS119": {"title": "Quality statement 1: initial education in adrenaline auto-injector use", "org": "NICE (UK)",
                   "url": "https://www.nice.org.uk/guidance/qs119/chapter/quality-statement-1-initial-education-in-adrenaline-auto-injector-use"},
    "MHRA_AAI": {"title": "MHRA guidance on the use of adrenaline auto-injectors", "org": "MHRA (UK government)",
                 "url": "https://www.gov.uk/government/news/mhra-issues-new-guidance-on-the-use-of-life-saving-adrenaline-auto-injectors"},
    "STH_EPIPEN": {"title": "How to use an adrenaline auto-injector (EpiPen) leaflet", "org": "Sheffield Teaching Hospitals NHS Foundation Trust",
                   "url": "https://www.sth.nhs.uk/clientfiles/File/epipen.pdf"},
    "RCUK_BLS": {"title": "Adult Basic Life Support guidelines (2025)", "org": "Resuscitation Council UK",
                 "url": "https://www.resus.org.uk/print/pdf/node/36437"},
    "RCUK_ACTIVITY_BOOK": {"title": "Resuscitation Council UK: when an adult has stopped breathing normally (CPR)", "org": "Resuscitation Council UK",
                           "url": "https://www.resus.org.uk/sites/default/files/2023-10/RSAH_Activity%20Book%20v2.pdf"},
    "NHS_CPR": {"title": "How to do CPR", "org": "NHS (UK)", "url": "https://www.nhs.uk/conditions/first-aid/cpr/"},
    "EPILEPSY_ACTION": {"title": "When someone has a seizure: CARE", "org": "Epilepsy Action (UK)",
                        "url": "https://epilepsy.org.uk/when-someone-has-a-seizure-care"},
    "EPILEPSY_IE": {"title": "Seizure first aid", "org": "Epilepsy Ireland",
                    "url": "https://www.epilepsy.ie/sites/www.epilepsy.ie/files/Seizure%20First%20Aid.pdf"},
    "EPILEPSY_SCOTLAND": {"title": "First aid for seizures", "org": "Epilepsy Scotland",
                          "url": "https://www.epilepsyscotland.org.uk/about-epilepsy/first-aid/"},
    "BRC_MENINGITIS": {"title": "Meningitis: learn first aid", "org": "British Red Cross",
                       "url": "https://redcross.org.uk/first-aid/learn-first-aid/meningitis"},
    "STANDREWS_BOOKLET": {"title": "Adult first aid booklet (asthma, sepsis, heart attack)", "org": "St Andrew's First Aid (Scotland)",
                          "url": "https://www.firstaid.org.uk/wp-content/uploads/2025/06/Adult-CPR-Booklet-1-1.pdf"},
})

# What to do/say when calling the ambulance (shown in an expander; also read aloud with the instructions)
CALL_STEPS = {
    "steps": [
        {"ar": "اتصل فورًا ومتستناش تشوف الأعراض هتروح ولا لأ. ما تقلقش إنك تضيّع وقت المسعفين.",
         "en": "Call straight away; do not wait to see if symptoms pass. Do not worry about wasting the paramedics' time."},
        {"ar": "قول مكانك بالتحديد وإيه اللي حصل، وقول لو بتشك في نوبة قلبية أو سكتة دماغية أو حساسية شديدة (anaphylaxis) أو التهاب سحائي.",
         "en": "Give your exact location and what happened, and say if you suspect a heart attack, stroke, severe allergic reaction (anaphylaxis) or meningitis."},
        {"ar": "ابقى على الخط ومتقفلش لحد ما المشغل يقولك؛ هو هيوجّهك خطوة بخطوة.",
         "en": "Stay on the line until the call handler says otherwise; they will talk you through the next steps."},
        {"ar": "لو انت لوحدك مع حد فاقد الوعي: اتصل الأول وبعدين ارجع له. ومتسيبش المريض لوحده بعد كده، وراقب استجابته لحد ما الإسعاف يوصل.",
         "en": "If you are alone with an unresponsive person: call first, then return to them. Afterwards stay with them and keep monitoring their response until help arrives."},
    ],
    "sources": ["BHF_HEART_ATTACK", "SJA_HEART_ATTACK", "NWAS_LEAFLET", "NHS_HEART_ATTACK", "RCUK_BLS", "SJA_STROKE", "BRC_MENINGITIS", "ANAPHYLAXIS_UK"],
}

FIRST_AID_ORDER = ["unresponsive", "anaphylaxis", "breathing", "chest", "stroke", "seizure", "meningitis", "infant_fever"]

FIRST_AID = {
    "unresponsive": {
        "icon": "🆘", "triggers": ["R-ESI1-UNRESP"],
        "title_ar": "شخص فاقد الوعي / مش بيستجيب", "title_en": "Unresponsive person",
        "steps": [
            {"ar": "اطلب الإسعاف فورًا (أو خلي حد يتصل). لو انت لوحدك: اتصل الأول وبعدين ارجع للمريض.",
             "en": "Call the ambulance immediately (or ask someone to). If you are alone, call first, then return to the person."},
            {"ar": "افتح مجرى الهواء: اميّل الراس لورا بإيد وارفع الدقن بإصبعين من الإيد التانية.",
             "en": "Open the airway: tilt the head back with one hand and lift the chin with two fingers of the other hand."},
            {"ar": "بُص على الصدر واسمع وحِس بالنفس لحد 10 ثواني.",
             "en": "Look at the chest, and listen and feel for breathing for up to 10 seconds."},
            {"ar": "لو بيتنفس طبيعي: حطه في وضع الإفاقة (على جنبه) وكمّل مراقبة التنفس.",
             "en": "If breathing normally: place them in the recovery position (on their side) and keep watching their breathing."},
            {"ar": "لو مش بيتنفس طبيعي (أو بيشهق شهقات متقطعة): ابدأ ضغطات الصدر فورًا (CPR). كعب إيدك في نص الصدر، والإيد التانية فوقها، ودراعاتك مفرودة. اضغط بعمق 5 إلى 6 سم بمعدل 100 إلى 120 ضغطة في الدقيقة (حوالي ضغطتين في الثانية)، وسيب الصدر يرجع لوضعه بعد كل ضغطة.",
             "en": "If not breathing normally (or only gasping): start chest compressions now (CPR). Heel of one hand in the centre of the chest, other hand on top, arms straight. Press 5 to 6 cm deep at 100 to 120 compressions per minute (about two per second) and let the chest come back up after each press."},
            {"ar": "لو متدرب على الإنعاش بالتنفس الصناعي: بعد كل 30 ضغطة اعمل نفسين. لو مش متأكد، ضغطات الصدر بس أحسن من مفيش.",
             "en": "If trained in CPR with rescue breaths: give 2 breaths after every 30 compressions. If not confident, hands-only CPR is better than nothing."},
            {"ar": "لو فيه جهاز صدمات (AED) قريب: خلّي حد يجيبه واتبع تعليماته الصوتية. كمّل لحد ما الإسعاف يوصل.",
             "en": "If an AED (defibrillator) is nearby: ask someone to bring it and follow its voice prompts. Continue until the ambulance arrives."},
            {"ar": "الخطوات دي للبالغين. للأطفال والرضع طريقة الإنعاش بتختلف: خلّي مشغل الإسعاف يوجّهك.",
             "en": "These steps are for adults. CPR for children and infants differs: let the call handler guide you."},
        ],
        "dont": [
            {"ar": "متوقفش الضغطات لحد ما الإسعاف يوصل أو الشخص يبدأ يتنفس طبيعي.",
             "en": "Do not stop compressions until the ambulance arrives or the person starts breathing normally."},
        ],
        "sources": ["RCUK_BLS", "RCUK_ACTIVITY_BOOK", "NHS_CPR", "SJA_CYMRU_GUIDE", "REDCROSS_CA_FACTS", "NWAS_LEAFLET"],
    },
    "anaphylaxis": {
        "icon": "💉", "triggers": ["R-ANAPH-SWELL", "R-ANAPH-PATTERN"],
        "title_ar": "حساسية شديدة (Anaphylaxis)", "title_en": "Severe allergic reaction (anaphylaxis)",
        "steps": [
            {"ar": "اتصل بالإسعاف فورًا وقول كلمة: anaphylaxis (حساسية شديدة).",
             "en": "Call the ambulance immediately and say the word: anaphylaxis."},
            {"ar": "لو معاه حقنة أدرينالين جاهزة (EpiPen أو Jext أو غيرها): استخدمها فورًا في جانب الفخذ واتبع التعليمات المكتوبة على الجهاز، وسجّل الوقت.",
             "en": "If they have an adrenaline auto-injector (EpiPen, Jext or similar): use it straight away in the side of the thigh, follow the instructions on the device, and note the time."},
            {"ar": "مدّده على ضهره ورفّع رجليه. متخليهوش يقف أو يمشي حتى لو حس إنه أحسن.",
             "en": "Lie them flat and raise their legs. Do not let them stand or walk, even if they feel better."},
            {"ar": "لو بيتنفس بصعوبة: خليه يقعد بشكل مسنود ورجليه ممدودة من غير حركة مفاجئة، ويرجع يتمدد أول ما يقدر. لو حامل: على جنبه الشمال. لو فاقد الوعي: وضع الإفاقة.",
             "en": "If struggling to breathe: let them sit propped up with legs stretched out, without sudden movement, and lie down again as soon as they can. If pregnant: lie on the left side. If unconscious: recovery position."},
            {"ar": "لو مفيش تحسن بعد 5 دقايق ومعاك حقنة تانية: استخدمها.",
             "en": "If there is no improvement after 5 minutes and you have a second injector: use it."},
            {"ar": "ابقى معاه لحد ما الإسعاف يوصل. لو فقد الوعي وبطل يتنفس طبيعي: ابدأ الإنعاش (CPR).",
             "en": "Stay with them until the ambulance arrives. If they become unresponsive and stop breathing normally: start CPR."},
        ],
        "dont": [
            {"ar": "متخليهوش يقف أو يمشي، حتى لو حس إنه كويس.", "en": "Do not let them stand or walk, even if they feel well."},
        ],
        "sources": ["ANAPHYLAXIS_UK", "NHS_ANAPHYLAXIS", "NICE_QS119", "MHRA_AAI", "STH_EPIPEN", "RCUK_BLS"],
    },
    "breathing": {
        "icon": "🫁", "triggers": ["R-ESI1-RESP"], "suppress_if_active": ["anaphylaxis"],
        "title_ar": "صعوبة تنفس شديدة", "title_en": "Severe breathing difficulty",
        "steps": [
            {"ar": "اتصل بالإسعاف فورًا.", "en": "Call the ambulance right away."},
            {"ar": "خليه في الوضع اللي بيرتاح فيه في التنفس، غالبًا قاعد معتدل ومسنود (ممكن يميل لقدام شوية).",
             "en": "Let them take the position that makes breathing easiest, usually sitting upright and supported (they may lean slightly forward)."},
            {"ar": "فُك أي ملابس ضيقة.", "en": "Loosen any tight clothing."},
            {"ar": "لو عنده بخاخة (انهيلر) أو خطة علاج للربو، ساعده يستخدمها.",
             "en": "If they have an inhaler or an asthma plan, help them use it."},
            {"ar": "طمّنه وخليه هادي، وراقب تنفسه باستمرار.", "en": "Keep them calm and reassured, and keep watching their breathing."},
            {"ar": "لو ظهر ورم في الوش أو الشفايف أو اللسان أو طفح: اتبع خطوات الحساسية الشديدة.",
             "en": "If swelling of the face, lips or tongue, or a rash appears: follow the severe allergic reaction steps."},
            {"ar": "لو التنفس وقف أو فقد الوعي: ابدأ الإنعاش (CPR).", "en": "If breathing stops or they become unresponsive: start CPR."},
        ],
        "dont": [],
        "sources": ["MEDLINEPLUS_BREATHING", "STANDREWS_BOOKLET", "RCUK_BLS"],
    },
    "chest": {
        "icon": "❤️", "triggers": ["R-ESI1-CHEST-SHOCK", "R-ACS-PATTERN", "R-ACS-ASSOC"],
        "title_ar": "ألم صدر مشتبه بنوبة قلبية", "title_en": "Chest pain: suspected heart attack",
        "steps": [
            {"ar": "اتصل بالإسعاف فورًا وقول إنك بتشك في نوبة قلبية.",
             "en": "Call the ambulance immediately and say you suspect a heart attack."},
            {"ar": "اقعّد المريض في وضع مريح: أفضل وضع نص جلوس، على الأرض أو كرسي، ركبه مثنية وراسه وكتافه مسنودين بوسايد.",
             "en": "Sit them in a comfortable position: best is half-sitting, on the floor or a chair, knees bent, head and shoulders supported with cushions."},
            {"ar": "فُك أي ملابس ضيقة (أزرار، حزام، رباط عنق).",
             "en": "Loosen tight clothing (buttons, belts, ties)."},
            {"ar": "طمّنه وخليه هادي وساكن، ومايمشيش ولا يتحرك، علشان ما يتعبش القلب.",
             "en": "Keep them calm and still; do not let them walk around, to avoid straining the heart."},
            {"ar": "لو متاح، وهو فوق 16 سنة وملوش حساسية من الأسبرين: قرص أسبرين 300 مجم يمضغه ببطء. لو مش متأكد، اسأل مشغل الإسعاف الأول.",
             "en": "If available, and they are over 16 and not allergic to aspirin: one 300 mg aspirin tablet, chewed slowly. If unsure, ask the call handler first.",
             "skip_if_active": ["stroke"]},
            {"ar": "لو معاه دوا الذبحة الصدرية بتاعه، ساعده ياخده.",
             "en": "If they have their own angina medication, help them take it."},
            {"ar": "راقب استجابته. لو فقد الوعي وبطل يتنفس طبيعي: ابدأ الإنعاش (CPR).",
             "en": "Keep monitoring their response. If they become unresponsive and stop breathing normally: start CPR."},
        ],
        "dont": [
            {"ar": "متديهوش أكل ولا شرب.", "en": "Do not give anything to eat or drink."},
            {"ar": "متوصّلوش بعربيتك بنفسك للمستشفى: الإسعاف أسرع وبيبدأ العلاج في الطريق.",
             "en": "Do not drive them or yourself to hospital: the ambulance is faster and starts care on the way."},
            {"ar": "متستناش تشوف الألم هيروح ولا لأ.", "en": "Do not wait to see if the pain goes away."},
        ],
        "sources": ["SJA_HEART_ATTACK", "SJA_CYMRU_GUIDE", "NWAS_LEAFLET", "NHS_HEART_ATTACK", "BHF_HEART_ATTACK", "NIDIRECT_HEART_ATTACK"],
    },
    "stroke": {
        "icon": "🧠", "triggers": ["R-STROKE-FAST", "R-STROKE-SUDDEN"],
        "title_ar": "اشتباه سكتة دماغية", "title_en": "Suspected stroke",
        "steps": [
            {"ar": "اتصل بالإسعاف فورًا وقول إنك بتشك في سكتة دماغية.",
             "en": "Call the ambulance immediately and say you suspect a stroke."},
            {"ar": "سجّل الوقت اللي ظهرت فيه الأعراض لأول مرة وقوله للإسعاف: بيأثر على قرار العلاج.",
             "en": "Note the time the symptoms first started and tell the ambulance crew: it affects treatment decisions."},
            {"ar": "ساعده يقعد أو يتمدد في وضع مريح ومسنود.",
             "en": "Help them sit or lie down in a comfortable, supported position."},
            {"ar": "طمّنه وخليك معاه؛ ممكن يبقى قلقان ومش قادر يتكلم بوضوح.",
             "en": "Reassure them and stay with them; they may be anxious and unable to speak clearly."},
            {"ar": "راقب استجابته. لو فقد الوعي: افحص التنفس، وحطه في وضع الإفاقة لو بيتنفس، أو ابدأ الإنعاش لو مش بيتنفس طبيعي.",
             "en": "Keep monitoring their response. If they become unresponsive: check breathing; recovery position if breathing, CPR if not breathing normally."},
        ],
        "dont": [
            {"ar": "متديهوش أكل ولا شرب لأن البلع ممكن يبقى صعب.", "en": "Do not give food or drink; swallowing may be difficult."},
            {"ar": "متستناش تشوف الأعراض هتتحسن: اتعامل على إنها سكتة.", "en": "Do not wait to see if it improves: act as if it is a stroke."},
        ],
        "sources": ["SJA_STROKE", "BRC_STROKE", "NHCS_STROKE", "SJA_CYMRU_GUIDE", "NHS_FAST"],
    },
    "seizure": {
        "icon": "⚡", "triggers": ["R-SEIZURE"],
        "title_ar": "تشنجات لأول مرة", "title_en": "First-ever seizure",
        "steps": [
            {"ar": "سجّل وقت بداية التشنج وراقب مدته.", "en": "Note when the seizure started and time how long it lasts."},
            {"ar": "شيل أي حاجة خطرة حواليه، واحمي راسه بحاجة ناعمة (جاكت أو مخدة).",
             "en": "Remove anything harmful nearby and cushion their head with something soft (jacket or cushion)."},
            {"ar": "فُك الملابس الضيقة حوالين الرقبة.", "en": "Loosen tight clothing around the neck."},
            {"ar": "لما التشنج يخلص: حطه في وضع الإفاقة (على جنبه)، وخليك معاه وطمّنه لحد ما يفوق.",
             "en": "When the jerking stops: place them in the recovery position (on their side), stay with them and reassure them as they come round."},
            {"ar": "اتصل بالإسعاف: ده أول تشنج ليه. وكمان لو دام أكتر من 5 دقايق أو اتكرر من غير ما يفوق أو اتصاب.",
             "en": "Call the ambulance: this is their first seizure. Also if it lasts over 5 minutes, repeats without recovery, or they are injured."},
        ],
        "dont": [
            {"ar": "متمسكوش بالقوة ومتحطش أي حاجة في بقه.", "en": "Do not restrain them and do not put anything in their mouth."},
        ],
        "sources": ["EPILEPSY_ACTION", "EPILEPSY_IE", "EPILEPSY_SCOTLAND"],
    },
    "meningitis": {
        "icon": "🌡️", "triggers": ["R-MENING"],
        "title_ar": "اشتباه التهاب سحائي / تسمم دموي", "title_en": "Suspected meningitis / septicaemia",
        "steps": [
            {"ar": "اتصل بالإسعاف فورًا؛ متستناش ظهور كل الأعراض أو الطفح.",
             "en": "Call the ambulance immediately; do not wait for all symptoms or a rash to appear."},
            {"ar": "قول للمشغل إنك بتشك في التهاب سحائي أو تسمم دموي (sepsis).",
             "en": "Tell the call handler you suspect meningitis or sepsis."},
            {"ar": "افحص الجلد: اضغط جنب كوباية شفافة على البقع. لو لسه باينة من الكوباية يبقى مش بتختفي بالضغط. لو البشرة غامقة افحص كف الإيد وباطن الجفون.",
             "en": "Check the skin: press the side of a clear glass on the rash. If you can still see it through the glass it does not fade. On darker skin check the palms and inside the eyelids."},
            {"ar": "طمّنه باستمرار لحد ما الإسعاف يوصل.", "en": "Keep reassuring them until the ambulance arrives."},
        ],
        "dont": [
            {"ar": "متستناش ظهور الطفح علشان تتصل.", "en": "Do not wait for a rash before calling."},
        ],
        "sources": ["BRC_MENINGITIS", "NHS_MENINGITIS"],
    },
    "infant_fever": {
        "icon": "👶", "triggers": ["R-INFANT-FEVER"],
        "title_ar": "رضيع أقل من 3 شهور بحرارة", "title_en": "Baby under 3 months with a fever",
        "steps": [
            {"ar": "خد الرضيع لأقرب طوارئ فورًا أو اتصل بالإسعاف.",
             "en": "Take the baby to the nearest emergency department immediately or call the ambulance."},
            {"ar": "قول للدكتور لو الحرارة ظهرت خلال 48 ساعة بعد تطعيم.",
             "en": "Tell the doctor if the fever started within 48 hours after a vaccination."},
        ],
        "dont": [],
        "sources": ["NOTTS_ICB_FEVER"],
    },
    "general": {
        "icon": "🚑", "triggers": [],
        "title_ar": "خطوات عامة لحد ما الإسعاف يوصل", "title_en": "General steps until help arrives",
        "steps": [
            {"ar": "اتصل بالإسعاف فورًا واتبع تعليمات المشغل.", "en": "Call the ambulance now and follow the call handler's instructions."},
            {"ar": "خليك مع المريض، طمّنه، وخليه في وضع مريح.", "en": "Stay with the person, reassure them and keep them comfortable."},
            {"ar": "راقب استجابته وتنفسه. لو فقد الوعي وبطل يتنفس طبيعي: ابدأ الإنعاش (CPR).",
             "en": "Keep monitoring their response and breathing. If they become unresponsive and stop breathing normally: start CPR."},
        ],
        "dont": [],
        "sources": ["NWAS_LEAFLET", "SJA_CYMRU_GUIDE", "RCUK_BLS"],
    },
}

# =====================================================================================
# 2) INFERENCE ENGINE
# =====================================================================================

OPS = {"==": operator.eq, ">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le}
DEFAULT_CF = 0.30


def cf_combine(cf1, cf2):
    """MYCIN-style combination of positive evidence: CF = CF1 + CF2 * (1 - CF1)."""
    return cf1 + cf2 * (1 - cf1)


def cf_combine_all(cfs):
    total = 0.0
    for cf in cfs:
        total = cf_combine(total, cf)
    return total


def esi_danger_zone(age_months, hr, rr, spo2):
    """ESI v4 (AHRQ) Fig. 3-5, decision point D. Returns (is_danger_zone, details). None = unknown.
        <3 months: HR>180, RR>50 | 3 m-3 y: >160/>40 | 3-8 y: >140/>30 | >8 y: >100/>20 | SpO2<92% any age"""
    details = []
    if spo2 is not None and spo2 < 92:
        details.append(f"SpO2 {spo2} < 92")
    if age_months is not None:
        if age_months < 3:
            hr_lim, rr_lim, band = 180, 50, "<3 months"
        elif age_months < 36:
            hr_lim, rr_lim, band = 160, 40, "3 months-3 years"
        elif age_months <= 96:
            hr_lim, rr_lim, band = 140, 30, "3-8 years"
        else:
            hr_lim, rr_lim, band = 100, 20, ">8 years"
        if hr is not None and hr > hr_lim:
            details.append(f"HR {hr} > {hr_lim} ({band})")
        if rr is not None and rr > rr_lim:
            details.append(f"RR {rr} > {rr_lim} ({band})")
    return (len(details) > 0, details)


class NeedAnswer(Exception):
    """Raised by an 'ask' callback when an answer is not available yet (used by the web UI)."""

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
    """Rule kinds:  derive = assert an intermediate fact | conclude = conclude a triage level with a CF.
    Policy (safety-first): the most severe level supported by any fired rule wins."""

    def __init__(self, rules=RULES, catalog=FACTS_CATALOG):
        self.rules = rules
        self.catalog = catalog
        self.derive_rules = [r for r in rules if r["type"] == "derive"]
        self.conclude_rules = [r for r in rules if r["type"] == "conclude"]
        self.derived_facts = {r["then"]["fact"] for r in self.derive_rules}

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
            return {"level": 4, "cf": DEFAULT_CF, "fired": fired, "default": True,
                    "level_cfs": {}, "danger_details": danger_details or []}
        winners = [r for r in fired if r["type"] == "conclude" and r["then"]["level"] == level]
        cf = cf_combine_all(r["cf"] for r in winners)
        return {"level": level, "cf": cf, "fired": fired, "default": False,
                "level_cfs": level_cfs or {level: cf}, "danger_details": danger_details or []}

    # ---- Forward chaining: all data known, fire rules until nothing new fires ----
    def forward(self, answers):
        wm = {f: self._default(f) for f, s in self.catalog.items() if s.get("kind") == "input"}
        wm.update(answers)
        flag, details = esi_danger_zone(wm.get("age_months"), wm.get("hr"), wm.get("rr"), wm.get("spo2"))
        wm["danger_zone_vitals"] = flag
        getter = lambda f: wm.get(f, self._default(f))
        fired, fired_ids, changed = [], set(), True
        while changed:
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
        level_cfs = {lvl: cf_combine_all(cfs) for lvl, cfs in by_level.items()}
        level = min(level_cfs)
        return self._result(level, fired, danger_details=details if flag else [], level_cfs=level_cfs)

    # ---- Backward chaining: goal = prove level 1, then 2, then 3; ask only what a rule needs ----
    def backward(self, answers, ask):
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


# =====================================================================================
# 3) EXPLANATION FACILITY
# =====================================================================================

def explain(result, lang="ar", region=DEFAULT_REGION):
    key = "reason_" + lang
    lines = []
    for r in result["fired"]:
        lines.append({
            "id": r["id"], "kind": r["type"], "text": r[key],
            "cf": r.get("cf"),
            "sources": [dict(SOURCES[s], id=s) for s in r.get("sources", [])],
        })
    unique = {}
    for ln in lines:
        for s in ln["sources"]:
            unique[s["id"]] = s
    if result.get("default"):
        text = ("لم تنطبق أي قاعدة خطر. هذه النتيجة الافتراضية للنظام وليست تأكيدًا على سلامة الحالة."
                if lang == "ar" else
                "No red-flag rule fired. This is the system default, not a guarantee that the case is safe.")
        lines.append({"id": "DEFAULT", "kind": "default", "text": text, "cf": result["cf"],
                      "sources": [dict(SOURCES["SYSTEM_DEFAULT"], id="SYSTEM_DEFAULT")]})
    return {"level_info": LEVELS[result["level"]], "advice": level_advice(result["level"], lang, region), "lines": lines, "sources": list(unique.values()),
            "danger_details": result.get("danger_details", [])}


def format_text(result, lang="ar", region=DEFAULT_REGION):
    info = LEVELS[result["level"]]
    ex = explain(result, lang, region)
    out = [f"== {info['name_' + lang]} | CF = {result['cf']:.2f} ==", ex["advice"], ""]
    for ln in ex["lines"]:
        cf = f" (CF {ln['cf']:.2f})" if ln["cf"] is not None and ln["kind"] == "conclude" else ""
        out.append(f"- [{ln['id']}] {ln['text']}{cf}")
    if ex["danger_details"]:
        out.append("- ESI danger-zone: " + "; ".join(ex["danger_details"]))
    if ex["sources"]:
        out += ["", "Sources:"]
        out += [f"  * {s['org']} - {s['title']} {s['url']}".rstrip() for s in ex["sources"]]
    plan = first_aid_plan(result, lang, region)
    if plan:
        out += ["", format_first_aid_text(plan, lang)]
    return "\n".join(out)


# =====================================================================================
# 3b) EMERGENCY GUIDANCE + PRE-ARRIVAL FIRST AID
# =====================================================================================

AR_DIGITS = {"0": "صفر", "1": "واحد", "2": "اثنين", "3": "ثلاثة", "4": "أربعة",
             "5": "خمسة", "6": "ستة", "7": "سبعة", "8": "ثمانية", "9": "تسعة"}
EN_DIGITS = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
             "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"}


def speak_number(number, lang="ar"):
    """'123' -> 'واحد، اثنين، ثلاثة' / 'one, two, three' (digit by digit, so text-to-speech never reads 123 as a quantity)."""
    words = AR_DIGITS if lang == "ar" else EN_DIGITS
    return ("، " if lang == "ar" else ", ").join(words[d] for d in str(number) if d in words)


def get_region(code):
    return REGIONS.get(code, REGIONS["OTHER"])


def call_label(region_code, lang="ar", spoken=False):
    """Text for the ambulance number of a region, e.g. '123 (مصر)' or, spoken, 'واحد، اثنين، ثلاثة'."""
    reg = get_region(region_code)
    if not reg["ambulance"]:
        return "رقم الطوارئ المحلي" if lang == "ar" else "your local emergency number"
    if spoken:
        return speak_number(reg["ambulance"], lang)
    return f"{reg['ambulance']} ({reg['name_' + lang]})"


def level_advice(level, lang="ar", region=DEFAULT_REGION, spoken=False):
    return LEVELS[level]["advice_" + lang].format(call=call_label(region, lang, spoken))


def emergency_numbers(region=DEFAULT_REGION, lang="ar"):
    """[(label, number), ...] - ambulance first. Only numbers present in REGIONS (i.e. sourced) are returned."""
    reg = get_region(region)
    labels = {"ambulance": ("🚑 الإسعاف", "🚑 Ambulance"), "police": ("🚓 الشرطة", "🚓 Police"),
              "fire": ("🚒 الإطفاء / الدفاع المدني", "🚒 Fire / civil defence")}
    idx = 0 if lang == "ar" else 1
    return [(labels[k][idx], reg[k]) for k in ("ambulance", "police", "fire") if reg.get(k)]


def active_protocols(result):
    """First-aid protocols for a triage result. Only for levels 1-2; chosen by the rules that fired."""
    if result["level"] > 2:
        return []
    fired = {r["id"] for r in result["fired"]}
    active = [p for p in FIRST_AID_ORDER if fired & set(FIRST_AID[p]["triggers"])]
    active = [p for p in active if not (set(FIRST_AID[p].get("suppress_if_active", [])) & set(active))]
    return active or ["general"]


def first_aid_plan(result, lang="ar", region=DEFAULT_REGION):
    """Structured plan for the UI / CLI / voice. Returns None when no first aid applies (level 3-4)."""
    names = active_protocols(result)
    if not names:
        return None
    reg = get_region(region)
    protocols = []
    for name in names:
        p = FIRST_AID[name]
        steps = [s[lang] for s in p["steps"] if not (set(s.get("skip_if_active", [])) & set(names))]
        protocols.append({
            "id": name, "icon": p["icon"], "title": p["title_" + lang], "steps": steps,
            "dont": [d[lang] for d in p["dont"]],
            "sources": [dict(SOURCES[s], id=s) for s in p["sources"]],
        })
    return {
        "region": region, "region_info": reg, "call": call_label(region, lang),
        "numbers": emergency_numbers(region, lang), "note": reg["note_" + lang],
        "protocols": protocols,
        "call_steps": [s[lang] for s in CALL_STEPS["steps"]],
        "call_sources": [dict(SOURCES[s], id=s) for s in CALL_STEPS["sources"]],
        "region_sources": [dict(SOURCES[s], id=s) for s in reg["sources"]],
        "disclaimer": FIRST_AID_NOTE_AR if lang == "ar" else FIRST_AID_NOTE_EN,
    }


def format_first_aid_text(plan, lang="ar"):
    out = []
    head = "رقم الإسعاف" if lang == "ar" else "Emergency number"
    out.append(f"## {head}: {plan['call']}")
    out.append("   " + " | ".join(f"{lbl}: {num}" for lbl, num in plan["numbers"]) if plan["numbers"] else "")
    out.append("   " + plan["note"])
    for p in plan["protocols"]:
        out += ["", f"## {p['icon']} {p['title']}"]
        out += [f"  {i}. {s}" for i, s in enumerate(p["steps"], 1)]
        out += [f"  ✗ {d}" for d in p["dont"]]
        out.append("  Sources: " + "; ".join(s["org"] for s in p["sources"]))
    out += ["", plan["disclaimer"]]
    return "\n".join(line for line in out if line is not None)


# =====================================================================================
# 3c) VOICE: text-to-speech script, browser speech widget, gTTS audio, speech-to-text answers
# =====================================================================================

_AR_SPOKEN_FIXES = [
    ("CPR", "الإنعاش القلبي الرئوي"), ("AED", "جهاز الصدمات الكهربائية"), ("EpiPen", "إيبي بين"),
    ("Jext", "جِكست"), ("anaphylaxis", "أنافيلاكسس"), ("sepsis", "سيبسيس"), ("300 مجم", "ثلاثمائة ملّيجرام"),
    ("5 إلى 6 سم", "خمسة إلى ستة سنتيمتر"),
]
_EN_SPOKEN_FIXES = [("300 mg", "three hundred milligrams"), ("5 to 6 cm", "five to six centimetres"), ("AED", "A E D"),
                    ("CPR", "C P R")]


def speechify(text, lang="ar"):
    """Make text friendlier for text-to-speech: drop symbols/emoji and spell out Latin abbreviations."""
    import re
    text = re.sub(r"\((?:ESI \d)\)", "", text)
    for old, new in (_AR_SPOKEN_FIXES if lang == "ar" else _EN_SPOKEN_FIXES):
        text = text.replace(old, new)
    text = text.replace("–", " - ").replace("✗", "").replace("⚠️", "").replace("•", "")
    text = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def build_spoken_script(result, lang="ar", region=DEFAULT_REGION, include_steps=True):
    """Everything a person needs to HEAR in an emergency: result, ambulance number (spelled digit by digit), steps."""
    info = LEVELS[result["level"]]
    num = call_label(region, lang, spoken=True)
    parts = []
    if lang == "ar":
        parts.append(f"نتيجة التقييم: {info['name_ar']}.")
        if result["level"] <= 2:
            parts.append(f"رقم الإسعاف: {num}. أكرر: {num}.")
        parts.append(level_advice(result["level"], lang, region, spoken=True))
    else:
        parts.append(f"Assessment result: {info['name_en']}.")
        if result["level"] <= 2:
            parts.append(f"Ambulance number: {num}. I repeat: {num}.")
        parts.append(level_advice(result["level"], lang, region, spoken=True))
    plan = first_aid_plan(result, lang, region) if include_steps else None
    if plan:
        for p in plan["protocols"]:
            parts.append(p["title"] + ".")
            for i, s in enumerate(p["steps"], 1):
                parts.append((f"الخطوة {i}: " if lang == "ar" else f"Step {i}: ") + s)
            for d in p["dont"]:
                parts.append(("ممنوع: " if lang == "ar" else "Do not: ") + d)
        parts.append(f"تذكير: رقم الإسعاف {num}. اتصل الآن." if lang == "ar"
                     else f"Reminder: ambulance number {num}. Call now.")
    parts.append("هذا النظام للإرشاد فقط وليس بديلًا عن الطبيب." if lang == "ar"
                 else "This tool is guidance only and not a substitute for a doctor.")
    return speechify(" ".join(parts), lang)


def build_number_script(region=DEFAULT_REGION, lang="ar"):
    num = call_label(region, lang, spoken=True)
    if lang == "ar":
        return speechify(f"رقم الإسعاف: {num}. أكرر: {num}. اتصل الآن.", lang)
    return speechify(f"Ambulance number: {num}. I repeat: {num}. Call now.", lang)


def browser_tts_html(text, lang="ar", labels=None, voice_lang=None):
    """Self-contained HTML/JS widget (Web Speech API): big buttons that read `text` aloud in the browser.
    No Python dependency and no internet needed if the device has an Arabic voice installed."""
    import json
    labels = labels or {}
    vlang = voice_lang or ("ar-EG" if lang == "ar" else "en-US")
    payload = json.dumps({"text": text, "lang": vlang, "novoice": labels.get("novoice", "")}, ensure_ascii=False)
    payload = payload.replace("</", "<\\/")
    play = labels.get("play", "🔊 Listen")
    stop = labels.get("stop", "⏹ Stop")
    direction = "rtl" if lang == "ar" else "ltr"
    return f"""
<div dir="{direction}" style="font-family:system-ui,Segoe UI,Tahoma,sans-serif">
  <div style="display:flex;gap:10px;flex-wrap:wrap">
    <button id="play" style="flex:1;min-width:200px;min-height:56px;font-size:20px;font-weight:700;border:0;border-radius:12px;background:#1565c0;color:#fff;cursor:pointer">{play}</button>
    <button id="stop" style="min-height:56px;font-size:18px;border:2px solid #888;border-radius:12px;background:transparent;color:#888;cursor:pointer;padding:0 18px">{stop}</button>
  </div>
  <div id="msg" style="margin-top:8px;font-size:14px;color:#c62828"></div>
</div>
<script>
const CFG = {payload};
const synth = window.speechSynthesis;
function pickVoice() {{
  const voices = synth ? synth.getVoices() : [];
  return voices.find(v => v.lang === CFG.lang) || voices.find(v => v.lang.toLowerCase().startsWith(CFG.lang.slice(0,2))) || null;
}}
document.getElementById('play').onclick = () => {{
  const msg = document.getElementById('msg'); msg.textContent = '';
  if (!synth) {{ msg.textContent = CFG.novoice; return; }}
  synth.cancel();
  const u = new SpeechSynthesisUtterance(CFG.text);
  u.lang = CFG.lang; u.rate = 0.9;
  const v = pickVoice();
  if (v) {{ u.voice = v; }} else if (CFG.novoice) {{ msg.textContent = CFG.novoice; }}
  synth.speak(u);
}};
document.getElementById('stop').onclick = () => {{ if (synth) synth.cancel(); }};
if (synth) {{ synth.getVoices(); }}
</script>
"""


def gtts_audio_bytes(text, lang="ar"):
    """MP3 bytes via gTTS (pip install gTTS). Needs internet (it calls Google's TTS service)."""
    try:
        from gtts import gTTS
    except ImportError:
        raise RuntimeError("gTTS is not installed: pip install gTTS" if lang != "ar" else "مكتبة gTTS مش متسطبة: pip install gTTS")
    import io
    try:
        buf = io.BytesIO()
        gTTS(text=text, lang="ar" if lang == "ar" else "en", slow=False).write_to_fp(buf)
        return buf.getvalue()
    except Exception as exc:  # network problems etc.
        raise RuntimeError(("gTTS needs an internet connection: " if lang != "ar" else "gTTS محتاج اتصال إنترنت: ") + str(exc))


def transcribe_wav(wav_bytes, lang="ar"):
    """Speech-to-text for a short WAV recording (pip install SpeechRecognition; uses Google's free web API => internet)."""
    try:
        import speech_recognition as sr
    except ImportError:
        raise RuntimeError("SpeechRecognition is not installed: pip install SpeechRecognition" if lang != "ar"
                           else "مكتبة SpeechRecognition مش متسطبة: pip install SpeechRecognition")
    import io
    rec = sr.Recognizer()
    try:
        with sr.AudioFile(io.BytesIO(wav_bytes)) as src:
            audio = rec.record(src)
        return rec.recognize_google(audio, language="ar-EG" if lang == "ar" else "en-US")
    except sr.UnknownValueError:
        return ""
    except Exception as exc:
        raise RuntimeError(("Speech recognition failed (needs internet): " if lang != "ar" else "التعرف على الصوت فشل (محتاج إنترنت): ") + str(exc))


def _norm_ar(text):
    import re
    text = text.lower()
    text = re.sub(r"[\u064B-\u065F\u0640]", "", text)  # diacritics + tatweel
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ى", "ي"), ("ة", "ه")):
        text = text.replace(a, b)
    return re.sub(r"[^\w\s]", " ", text)


_YES = {_norm_ar(w) for w in ("نعم", "ايوه", "أيوة", "ايوا", "ايو", "اه", "آه", "أجل", "صح", "فعلا", "اكيد", "yes", "yeah", "yep", "yup", "sure", "correct")}
_NO = {_norm_ar(w) for w in ("لا", "لأ", "لاء", "مش", "مفيش", "لسه", "no", "nope", "nah")}
_UNSURE = {_norm_ar(w) for w in ("عارف", "عارفه", "متاكد", "متأكد", "متاكده", "know", "unsure")}


def parse_yes_no(text):
    """Map a spoken answer to True / False / None (None = unclear -> ask again or use the buttons)."""
    words = set(_norm_ar(text or "").split())
    if words & _UNSURE:
        return None
    y, n = bool(words & _YES), bool(words & _NO)
    if y and not n:
        return True
    if n and not y:
        return False
    return None


# =====================================================================================
# 4a) COMMAND-LINE INTERFACE
# =====================================================================================

DEMO_CASES = {
    "Stroke signs (face droop + slurred speech)": {"age_months": 62 * 12, "face_droop": True, "slurred_speech": True},
    "Chest squeezing pain + sweating": {"age_months": 55 * 12, "chest_pain": True, "chest_pain_tight_pressure": True, "sweating": True},
    "Sprained ankle, pain 8/10 (ESI: not automatically level 2)": {"age_months": 25 * 12, "pain_score": 8},
    "Baby 2 months, temp 38.6": {"age_months": 2, "temp_c": 38.6},
    "No symptoms": {"age_months": 30 * 12},
}


def _ask_cli(lang):
    def ask(fact):
        spec = FACTS_CATALOG[fact]
        label = spec[lang]
        if spec["type"] == "bool":
            while True:
                a = input(f"{label}? (y/n): ").strip().lower()
                if a in ("y", "yes", "ن", "نعم"):
                    return True
                if a in ("n", "no", "ل", "لا", ""):
                    return False
        a = input(f"{label} (Enter = unknown): ").strip()
        return float(a) if a else None
    return ask


def cli_demo(lang, region=DEFAULT_REGION):
    engine = InferenceEngine()
    for name, case in DEMO_CASES.items():
        print(f"\n### {name}")
        print(format_text(engine.forward(case), lang, region))


def cli_interview(lang, region=DEFAULT_REGION):
    engine = InferenceEngine()
    age = float(input("Age (years) / العمر بالسنين: "))
    base = {"age_months": age * 12}
    for f, label in (("temp_c", "Temperature C"), ("hr", "Heart rate"), ("rr", "Resp rate"), ("spo2", "SpO2")):
        v = input(f"{label} (Enter = unknown): ").strip()
        base[f] = float(v) if v else None
    base["pain_score"] = float(input("Pain 0-10 (Enter = 0): ") or 0)
    print()
    print(format_text(engine.backward(base, _ask_cli(lang)), lang, region))


def cli_ui():
    try:
        import streamlit  # noqa: F401
    except ImportError:
        print("Streamlit is not installed. Run:  pip install streamlit   then:  python triage.py ui")
        return
    subprocess.run([sys.executable, "-m", "streamlit", "run", __file__])


def run_selftests():
    import unittest
    engine = InferenceEngine()
    adult = 30 * 12

    def fwd(**facts):
        facts.setdefault("age_months", adult)
        return engine.forward(facts)

    class T(unittest.TestCase):
        def test_kb_consistency(self):
            ids = [r["id"] for r in RULES]
            self.assertEqual(len(ids), len(set(ids)))
            for r in RULES:
                self.assertTrue(r["sources"] and r["reason_ar"] and r["reason_en"], r["id"])
                for s in r["sources"]:
                    self.assertIn(s, SOURCES)

        def test_levels(self):
            self.assertEqual(fwd(unresponsive=True)["level"], 1)
            self.assertEqual(fwd(spo2=85)["level"], 1)
            self.assertEqual(fwd(face_droop=True)["level"], 2)
            self.assertEqual(fwd(chest_pain=True, chest_pain_tight_pressure=True)["level"], 2)
            self.assertEqual(fwd(chest_pain=True)["level"], 3)
            self.assertEqual(fwd(pain_score=8)["level"], 3)
            self.assertEqual(fwd()["level"], 4)
            self.assertEqual(fwd(non_blanching_rash=True)["level"], 2)
            self.assertEqual(fwd(swelling_lips_mouth_throat_tongue=True)["level"], 1)
            self.assertEqual(fwd(unresponsive=True, pain_score=9, chest_pain=True)["level"], 1)

        def test_infant_fever(self):
            self.assertEqual(engine.forward({"age_months": 2, "temp_c": 38.5})["level"], 2)
            self.assertEqual(engine.forward({"age_months": 2, "temp_c": 38.5,
                                             "fever_after_vaccination_48h": True})["level"], 4)

        def test_danger_zone_by_age(self):
            self.assertEqual(fwd(hr=110)["level"], 2)
            self.assertEqual(engine.forward({"age_months": 60, "hr": 110})["level"], 4)

        def test_cf(self):
            r = fwd(chest_pain=True, chest_pain_tight_pressure=True, sweating=True)
            self.assertAlmostEqual(r["cf"], 0.85 + 0.85 * 0.15, places=4)

        def test_forward_equals_backward(self):
            rng = random.Random(7)
            bools = [f for f, s in FACTS_CATALOG.items() if s["kind"] == "input" and s["type"] == "bool"]
            for _ in range(500):
                w = {f: rng.random() < 0.12 for f in bools}
                w.update(age_months=rng.choice([1, 2, 6, 24, 60, 120, 400]),
                         temp_c=rng.choice([None, 36.6, 38.2, 39.5]), hr=rng.choice([None, 70, 105, 150, 190]),
                         rr=rng.choice([None, 16, 25, 45]), spo2=rng.choice([None, 98, 91, 85]),
                         pain_score=rng.choice([0, 3, 7, 9]))
                f = engine.forward(w)
                b = engine.backward({k: v for k, v in w.items() if FACTS_CATALOG[k]["type"] == "number"},
                                    lambda fact: w[fact])
                self.assertEqual(f["level"], b["level"], w)
                self.assertAlmostEqual(f["cf"], b["cf"], places=6)

        # ---------- emergency numbers, first aid, voice ----------
        def test_regions_and_numbers(self):
            self.assertEqual(REGIONS["EG"]["ambulance"], "123")
            self.assertEqual(emergency_numbers("EG", "en")[0][1], "123")
            self.assertIn("123", level_advice(1, "ar", "EG"))
            self.assertIn("123", level_advice(1, "en", "EG"))
            self.assertIn("999", level_advice(1, "en", "GB"))
            self.assertNotIn("123", level_advice(1, "en", "OTHER"))  # no number guessed for unknown regions
            for reg in REGIONS.values():
                for s in reg["sources"]:
                    self.assertIn(s, SOURCES)

        def test_first_aid_knowledge_is_complete_and_sourced(self):
            rule_ids = {r["id"] for r in RULES}
            for name, p in FIRST_AID.items():
                self.assertTrue(p["steps"], name)
                for t in p["triggers"]:
                    self.assertIn(t, rule_ids)
                for item in p["steps"] + p["dont"]:
                    self.assertTrue(item["ar"] and item["en"], name)
                for s in p["sources"]:
                    self.assertIn(s, SOURCES)
                    self.assertTrue(SOURCES[s]["url"].startswith("http"), s)
            self.assertEqual(set(FIRST_AID_ORDER) | {"general"}, set(FIRST_AID))

        def test_first_aid_chest_pain(self):
            plan = first_aid_plan(fwd(chest_pain=True, chest_pain_tight_pressure=True), "ar", "EG")
            self.assertEqual([p["id"] for p in plan["protocols"]], ["chest"])
            text = " ".join(plan["protocols"][0]["steps"])
            self.assertIn("نص جلوس", text)       # semi-seated position
            self.assertIn("ملابس ضيقة", text)    # loosen tight clothing
            self.assertIn("طمّنه", text)         # keep calm
            self.assertIn("300", text)           # aspirin step present
            self.assertEqual(plan["numbers"][0][1], "123")

        def test_aspirin_step_removed_when_stroke_signs_present(self):
            plan = first_aid_plan(fwd(chest_pain=True, chest_pain_tight_pressure=True, face_droop=True), "en", "EG")
            ids = [p["id"] for p in plan["protocols"]]
            self.assertIn("stroke", ids)
            self.assertNotIn("300 mg", " ".join(" ".join(p["steps"]) for p in plan["protocols"]))

        def test_first_aid_per_condition(self):
            self.assertEqual(active_protocols(fwd(unresponsive=True)), ["unresponsive"])
            self.assertEqual(active_protocols(fwd(face_droop=True)), ["stroke"])
            self.assertEqual(active_protocols(fwd(seizure_first_time=True)), ["seizure"])
            self.assertEqual(active_protocols(fwd(non_blanching_rash=True)), ["meningitis"])
            self.assertEqual(active_protocols(engine.forward({"age_months": 2, "temp_c": 38.5})), ["infant_fever"])
            self.assertEqual(active_protocols(fwd(worst_headache_of_life=True)), ["general"])
            cpr = " ".join(s["en"] for s in FIRST_AID["unresponsive"]["steps"])
            self.assertIn("100 to 120", cpr)
            self.assertIn("5 to 6 cm", cpr)

        def test_anaphylaxis_hides_sit_up_breathing_advice(self):
            r = fwd(swelling_lips_mouth_throat_tongue=True, severe_respiratory_distress=True)
            self.assertEqual(r["level"], 1)
            self.assertEqual(active_protocols(r), ["anaphylaxis"])

        def test_no_first_aid_for_level_3_and_4(self):
            self.assertEqual(active_protocols(fwd(pain_score=8)), [])
            self.assertEqual(active_protocols(fwd()), [])
            self.assertIsNone(first_aid_plan(fwd(), "ar", "EG"))

        def test_voice_script_reads_number_digit_by_digit(self):
            r = fwd(chest_pain=True, chest_pain_tight_pressure=True)
            ar = build_spoken_script(r, "ar", "EG")
            en = build_spoken_script(r, "en", "EG")
            self.assertIn("واحد، اثنين، ثلاثة", ar)
            self.assertNotIn("123", ar)
            self.assertIn("one, two, three", en)
            self.assertNotIn("123", en)
            self.assertNotIn("(ESI", ar)
            self.assertEqual(speak_number("999", "en"), "nine, nine, nine")
            self.assertIn("واحد، اثنين، ثلاثة", build_number_script("EG", "ar"))

        def test_browser_tts_widget_is_safe(self):
            html = browser_tts_html('hello </script><b>x</b>', "en", {"play": "Play", "stop": "Stop"})
            self.assertEqual(html.count("</script>"), 1)  # text cannot close the script tag
            self.assertIn("speechSynthesis", html)

        def test_yes_no_parser(self):
            for w in ("أيوه", "ايوة", "نعم", "yes", "Yes!"):
                self.assertIs(parse_yes_no(w), True, w)
            for w in ("لأ", "لا", "no", "No."):
                self.assertIs(parse_yes_no(w), False, w)
            for w in ("", "مش عارف", "نعم لا", "maybe"):
                self.assertIsNone(parse_yes_no(w), w)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(T)
    return unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()


def cli_main():
    args = sys.argv[1:]
    lang = "en" if "--lang" in args and args[args.index("--lang") + 1:][:1] == ["en"] else "ar"
    region = args[args.index("--region") + 1].upper() if "--region" in args and args[args.index("--region") + 1:] else DEFAULT_REGION
    if region not in REGIONS:
        region = "OTHER"
    mode = args[0] if args and not args[0].startswith("--") else None
    if mode is None:
        print("1) demo   2) interview   3) web UI   4) tests")
        mode = {"1": "demo", "2": "interview", "3": "ui", "4": "test"}.get(input("> ").strip(), "demo")
    if mode == "demo":
        cli_demo(lang, region)
    elif mode == "interview":
        cli_interview(lang, region)
    elif mode == "ui":
        cli_ui()
        return
    elif mode == "test":
        sys.exit(0 if run_selftests() else 1)
    else:
        print(__doc__)
        return
    print("\n" + (DISCLAIMER_AR if lang == "ar" else DISCLAIMER_EN))


# =====================================================================================
# 4b) STREAMLIT WEB UI  (quick assessment = forward chaining, smart interview = backward chaining)
# =====================================================================================

def run_ui():
    import streamlit as st
    import streamlit.components.v1 as components

    st.set_page_config(page_title="Medical Triage Expert System", page_icon="🩺", layout="wide")
    engine = InferenceEngine()
    catalog = FACTS_CATALOG

    TXT = {
        "ar": {
            "title": "🩺 نظام خبير للفرز الطبي الأولي",
            "sub": "مساعد فرز تعليمي مبني على قواعد من مصادر طبية رسمية (ESI / NHS) - مش تشخيص",
            "intake": "البيانات الأساسية", "age": "العمر", "unit": "الوحدة", "units": ["سنة", "شهر"],
            "unknown_hint": "اتركه 0 لو مش معروف", "pain": "شدة الألم (0-10)",
            "tab1": "📝 تقييم سريع", "tab2": "💬 مقابلة ذكية (صوت + أزرار)", "assess": "قيّم الحالة",
            "yes": "نعم", "no": "لا", "reset": "ابدأ من جديد", "q": "سؤال",
            "why": "ليه وصلنا للنتيجة دي؟", "sources": "المصادر", "conf": "نسبة الثقة",
            "interview_hint": "هسألك أسئلة بالترتيب، وبس عن اللي محتاجه. تقدر تسمع السؤال وتجاوب بصوتك أو بالأزرار.",
            "groups": {"consciousness": "الوعي", "breathing": "التنفس", "chest": "الصدر والقلب",
                       "neuro": "الأعصاب والسكتة", "allergy": "الحساسية", "infection": "عدوى وحرارة"},
            "disclaimer": DISCLAIMER_AR, "dir": "rtl",
            "region": "المنطقة (لرقم الطوارئ)", "emergency_call": "اتصل بالإسعاف", "tap_to_call": "على الموبايل: اضغط على الرقم للاتصال",
            "voice_mode": "🔊 مساعدة صوتية", "voice_title": "اسمع النتيجة والتعليمات",
            "voice_hint": "لو القراءة صعبة: اضغط الزر وهتسمع النتيجة ورقم الإسعاف وخطوات الإسعاف بصوت عالي.",
            "listen_all": "🔊 اسمع النتيجة والخطوات", "listen_number": "📞 اسمع رقم الإسعاف", "stop": "⏹ إيقاف",
            "novoice": "جهازك مفيهوش صوت عربي. جرّب زر الملف الصوتي (gTTS) تحت أو متصفح تاني.",
            "gtts_btn": "🎧 ملف صوتي (gTTS - محتاج إنترنت)", "read_question": "🔊 اسمع السؤال",
            "speak_answer": "🎙️ أو جاوب بصوتك (قول: أيوه / لا)", "heard": "سمعتك بتقول",
            "not_understood": "ما فهمتش الإجابة. قول «أيوه» أو «لا»، أو اضغط على الزر.",
            "stt_unavailable": "الإجابة بالصوت محتاجة نسخة Streamlit أحدث. استخدم الأزرار.",
            "stt_note": "التعرف على الصوت محتاج إنترنت ومش دقيق 100%: راجع اللي اتسمع.",
            "firstaid_title": "إسعافات أولية لحد ما الإسعاف يوصل", "dont_title": "ممنوع:",
            "call_steps_title": "لما تتصل بالإسعاف: قول إيه؟", "region_sources": "مصادر أرقام الطوارئ",
            "data_changed": "البيانات اتغيّرت بعد آخر تقييم. اضغط «قيّم الحالة» من جديد.",
            "if_worse": "لو الحالة زادت اتصل بالإسعاف",
        },
        "en": {
            "title": "🩺 Medical Triage Expert System",
            "sub": "Educational triage-support tool using rules from official medical sources (ESI / NHS) - not a diagnosis",
            "intake": "Basic information", "age": "Age", "unit": "Unit", "units": ["years", "months"],
            "unknown_hint": "Leave 0 if unknown", "pain": "Pain score (0-10)",
            "tab1": "📝 Quick assessment", "tab2": "💬 Smart interview (voice + buttons)", "assess": "Assess",
            "yes": "Yes", "no": "No", "reset": "Start over", "q": "Question",
            "why": "Why this result?", "sources": "Sources", "conf": "Confidence",
            "interview_hint": "I'll ask only what is needed, in order. You can listen to each question and answer by voice or buttons.",
            "groups": {"consciousness": "Consciousness", "breathing": "Breathing", "chest": "Chest / heart",
                       "neuro": "Neurological / stroke", "allergy": "Allergy", "infection": "Infection / fever"},
            "disclaimer": DISCLAIMER_EN, "dir": "ltr",
            "region": "Region (emergency number)", "emergency_call": "Call the ambulance", "tap_to_call": "On a phone: tap the number to call",
            "voice_mode": "🔊 Voice assistance", "voice_title": "Listen to the result and instructions",
            "voice_hint": "If reading is hard: press the button to hear the result, the ambulance number and the first-aid steps aloud.",
            "listen_all": "🔊 Listen to result and steps", "listen_number": "📞 Listen to ambulance number", "stop": "⏹ Stop",
            "novoice": "No voice for this language was found on your device. Try the audio-file button (gTTS) below or another browser.",
            "gtts_btn": "🎧 Audio file (gTTS - needs internet)", "read_question": "🔊 Listen to the question",
            "speak_answer": "🎙️ Or answer by voice (say: yes / no)", "heard": "I heard",
            "not_understood": "I did not understand. Say 'yes' or 'no', or press a button.",
            "stt_unavailable": "Voice answers need a newer Streamlit version. Use the buttons.",
            "stt_note": "Speech recognition needs internet and is not 100% accurate: check what was heard.",
            "firstaid_title": "First aid until the ambulance arrives", "dont_title": "Do not:",
            "call_steps_title": "When you call the ambulance: what to say", "region_sources": "Emergency-number sources",
            "data_changed": "Inputs changed since the last assessment. Press 'Assess' again.",
            "if_worse": "If it gets worse, call the ambulance",
        },
    }

    @st.cache_data(show_spinner=False)
    def cached_tts(text, language):
        return gtts_audio_bytes(text, language)

    with st.sidebar:
        lang = "ar" if st.radio("Language / اللغة", ["العربية", "English"]) == "العربية" else "en"
        T = TXT[lang]
        region = st.selectbox(T["region"], list(REGIONS), index=0,
                              format_func=lambda k: f"{REGIONS[k]['flag']} {REGIONS[k]['name_' + lang]}")
        st.error(f"📞 {T['emergency_call']}: **{call_label(region, lang)}**")
        voice_on = st.toggle(T["voice_mode"], value=True)
        st.header(T["intake"])
        age_val = st.number_input(T["age"], min_value=0.0, max_value=120.0, value=30.0, step=1.0)
        unit = st.selectbox(T["unit"], T["units"])
        temp = st.number_input(catalog["temp_c"][lang], min_value=0.0, max_value=45.0, value=0.0, step=0.1, help=T["unknown_hint"])
        hr = st.number_input(catalog["hr"][lang], min_value=0, max_value=300, value=0, help=T["unknown_hint"])
        rr = st.number_input(catalog["rr"][lang], min_value=0, max_value=100, value=0, help=T["unknown_hint"])
        spo2 = st.number_input(catalog["spo2"][lang], min_value=0, max_value=100, value=0, help=T["unknown_hint"])
        pain = st.slider(T["pain"], 0, 10, 0)
        st.warning(T["disclaimer"])

    if T["dir"] == "rtl":
        st.markdown("<style>.main, [data-testid='stSidebar']{direction:rtl;text-align:right;}</style>",
                    unsafe_allow_html=True)

    base = {
        "age_months": age_val if unit == T["units"][1] else age_val * 12,
        "temp_c": temp or None, "hr": hr or None, "rr": rr or None, "spo2": spo2 or None,
        "pain_score": float(pain),
    }

    # ---------- building blocks (all colours work in light and dark themes) ----------
    def render_call_banner(plan):
        amb = plan["region_info"]["ambulance"]
        others = " &nbsp;·&nbsp; ".join(f"{lbl}: <b dir='ltr'>{num}</b>" for lbl, num in plan["numbers"][1:])
        if amb:
            big = (f"<a href='tel:{amb}' style='color:#fff;text-decoration:none'>"
                   f"<div style='font-size:3.6rem;font-weight:800;letter-spacing:8px;direction:ltr;unicode-bidi:isolate;line-height:1.1'>{amb}</div></a>"
                   f"<div style='font-size:.85rem;opacity:.9'>{T['tap_to_call']}</div>")
        else:
            big = f"<div style='font-size:1.8rem;font-weight:800'>{call_label(plan['region'], lang)}</div>"
        st.markdown(
            "<div style='background:#b71c1c;color:#fff;border-radius:14px;padding:16px;text-align:center;margin:10px 0'>"
            f"<div style='font-size:1.1rem'>📞 {T['emergency_call']}</div>{big}"
            f"<div style='font-size:.95rem;margin-top:6px'>{others}</div>"
            f"<div style='font-size:.9rem;margin-top:6px;opacity:.95'>{plan['note']}</div></div>",
            unsafe_allow_html=True)

    def render_voice(result, prefix):
        script = build_spoken_script(result, lang, region)
        labels = {"stop": T["stop"], "novoice": T["novoice"]}
        with st.container(border=True):
            st.markdown(f"#### 🔊 {T['voice_title']}")
            st.caption(T["voice_hint"])
            c1, c2 = st.columns(2)
            with c1:
                components.html(browser_tts_html(script, lang, dict(labels, play=T["listen_all"])), height=125)
            with c2:
                components.html(browser_tts_html(build_number_script(region, lang), lang, dict(labels, play=T["listen_number"])), height=125)
            if st.button(T["gtts_btn"], key=f"{prefix}_gtts"):
                try:
                    audio = cached_tts(script, lang)
                except RuntimeError as exc:
                    st.info(str(exc))
                else:
                    st.audio(audio, format="audio/mp3")

    def render_first_aid(plan):
        st.markdown(f"### 🩹 {T['firstaid_title']}")
        st.caption(plan["disclaimer"])
        for p in plan["protocols"]:
            with st.container(border=True):
                st.markdown(f"#### {p['icon']} {p['title']}")
                st.markdown("\n".join(f"{i}. {s}" for i, s in enumerate(p["steps"], 1)))
                if p["dont"]:
                    st.markdown(f"**{T['dont_title']}**\n\n" + "\n".join(f"- ❌ {d}" for d in p["dont"]))
                st.caption(T["sources"] + ": " + " | ".join(f"[{s['org']}]({s['url']})" for s in p["sources"]))
        with st.expander(f"📞 {T['call_steps_title']}"):
            st.markdown("\n".join(f"{i}. {s}" for i, s in enumerate(plan["call_steps"], 1)))
            st.caption(T["sources"] + ": " + " | ".join(f"[{s['org']}]({s['url']})" for s in plan["call_sources"]))
        if plan["region_sources"]:
            with st.expander(T["region_sources"]):
                for s in plan["region_sources"]:
                    st.markdown(f"- {s['org']} — [{s['title']}]({s['url']})")

    def render_result(result, prefix):
        ex = explain(result, lang, region)
        info = ex["level_info"]
        plan = first_aid_plan(result, lang, region)
        # 1) result card
        st.markdown(
            f"<div style='background:{info['color']};color:white;padding:18px;border-radius:12px;font-size:1.3rem'>"
            f"<b>{info['name_' + lang]}</b><br><span style='font-size:1rem'>{ex['advice']}</span></div>",
            unsafe_allow_html=True)
        # 2) emergency number, big, right below the card
        if plan:
            render_call_banner(plan)
        else:
            st.caption(f"📞 {T['if_worse']}: **{call_label(region, lang)}**")
        # 3) voice + 4) first aid
        if voice_on:
            render_voice(result, prefix)
        if plan:
            render_first_aid(plan)
        # 5) confidence, explanation, sources
        st.progress(min(result["cf"], 1.0), text=f"{T['conf']}: {result['cf']:.0%}")
        with st.expander(T["why"], expanded=not plan):
            for ln in ex["lines"]:
                cf = f" — CF {ln['cf']:.2f}" if ln["cf"] is not None and ln["kind"] == "conclude" else ""
                src = " | ".join(f"[{s['org']}]({s['url']})" if s["url"] else s["org"] for s in ln["sources"])
                st.markdown(f"**{ln['id']}**{cf}  \n{ln['text']}  \n<small>{src}</small>", unsafe_allow_html=True)
            if ex["danger_details"]:
                st.caption("ESI danger-zone: " + "; ".join(ex["danger_details"]))
        if ex["sources"]:
            with st.expander(T["sources"]):
                for s in ex["sources"]:
                    if s["url"]:
                        st.markdown(f"- {s['org']} — [{s['title']}]({s['url']})")
        st.error(T["disclaimer"])

    st.title(T["title"])
    st.caption(T["sub"])
    tab1, tab2 = st.tabs([T["tab1"], T["tab2"]])

    with tab1:
        answers = dict(base)
        groups = {}
        for fid, spec in catalog.items():
            if spec["kind"] == "input" and spec["type"] == "bool":
                groups.setdefault(spec["group"], []).append(fid)
        cols = st.columns(2)
        for i, (g, fids) in enumerate(groups.items()):
            with cols[i % 2].expander(T["groups"][g], expanded=(i < 2)):
                for fid in fids:
                    if st.checkbox(catalog[fid][lang], key=f"cb_{fid}"):
                        answers[fid] = True
        if st.button(T["assess"], type="primary"):
            st.session_state["t1"] = {"result": engine.forward(answers), "inputs": dict(answers)}
        saved = st.session_state.get("t1")  # kept in session so audio buttons do not make the result disappear
        if saved:
            if saved["inputs"] != answers:
                st.warning(T["data_changed"])
            render_result(saved["result"], "t1")

    with tab2:
        st.info(T["interview_hint"])
        if "iv" not in st.session_state:
            st.session_state.iv = {}
        if st.button(T["reset"]):
            st.session_state.iv = {}
            st.rerun()

        def ask(fact):
            if fact in st.session_state.iv:
                return st.session_state.iv[fact]
            raise NeedAnswer(fact)

        try:
            result = engine.backward({**base, **st.session_state.iv}, ask)
        except NeedAnswer as need:
            fact = need.fact
            question = catalog[fact][lang] + ("؟" if lang == "ar" else "?")
            st.subheader(f"{T['q']} {len(st.session_state.iv) + 1}")
            st.markdown(f"### {question}")
            if voice_on:
                components.html(browser_tts_html(speechify(question, lang), lang,
                                                 {"play": T["read_question"], "stop": T["stop"], "novoice": T["novoice"]}),
                                height=125)
            c1, c2 = st.columns(2)
            if c1.button(T["yes"], key=f"y_{fact}", use_container_width=True, type="primary"):
                st.session_state.iv[fact] = True
                st.rerun()
            if c2.button(T["no"], key=f"n_{fact}", use_container_width=True):
                st.session_state.iv[fact] = False
                st.rerun()
            if voice_on:
                if hasattr(st, "audio_input"):
                    audio = st.audio_input(T["speak_answer"], key=f"aud_{fact}")
                    st.caption(T["stt_note"])
                    if audio is not None:
                        try:
                            heard = transcribe_wav(audio.getvalue(), lang)
                        except RuntimeError as exc:
                            st.info(str(exc))
                        else:
                            st.caption(f"🎙️ {T['heard']}: «{heard}»")
                            answer = parse_yes_no(heard)
                            if answer is None:
                                st.warning(T["not_understood"])
                            else:
                                st.session_state.iv[fact] = answer
                                st.rerun()
                else:
                    st.caption(T["stt_unavailable"])
        else:
            render_result(result, "t2")


# =====================================================================================
# ENTRY POINT:  `streamlit run triage.py` -> web UI | `python triage.py ...` -> CLI
# =====================================================================================

def _running_in_streamlit():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        try:
            return get_script_run_ctx(suppress_warning=True) is not None
        except TypeError:
            return get_script_run_ctx() is not None
    except Exception:
        return False


if _running_in_streamlit():
    run_ui()
elif __name__ == "__main__":
    cli_main()
