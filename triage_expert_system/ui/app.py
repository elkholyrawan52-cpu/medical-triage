"""Streamlit UI - run with:  streamlit run ui/app.py
Two modes: quick assessment (forward chaining) and smart interview (backward chaining).
No patient data is stored or logged."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from engine.explain import explain  # noqa: E402
from engine.inference import InferenceEngine, NeedAnswer  # noqa: E402
from engine.kb import load_catalog, load_rules, load_sources  # noqa: E402
from engine.levels import DISCLAIMER_AR, DISCLAIMER_EN  # noqa: E402

st.set_page_config(page_title="Medical Triage Expert System", page_icon="🩺", layout="wide")


@st.cache_resource
def get_engine():
    return InferenceEngine(load_rules(), load_catalog()), load_catalog(), load_sources()


engine, catalog, sources = get_engine()

TXT = {
    "ar": {
        "title": "🩺 نظام خبير للفرز الطبي الأولي",
        "sub": "مساعد فرز تعليمي مبني على قواعد من مصادر طبية رسمية (ESI / NHS) - مش تشخيص",
        "lang": "اللغة", "intake": "البيانات الأساسية", "age": "العمر", "unit": "الوحدة",
        "units": ["سنة", "شهر"], "unknown_hint": "اتركه 0 لو مش معروف",
        "pain": "شدة الألم (0-10)", "tab1": "📝 تقييم سريع", "tab2": "💬 مقابلة ذكية",
        "assess": "قيّم الحالة", "yes": "نعم", "no": "لا", "reset": "ابدأ من جديد",
        "q": "سؤال", "why": "ليه وصلنا للنتيجة دي؟", "sources": "المصادر", "conf": "نسبة الثقة",
        "rules_fired": "القواعد اللي اتفعّلت", "interview_hint": "هسألك أسئلة بالترتيب، وبس عن اللي محتاجه.",
        "groups": {"consciousness": "الوعي", "breathing": "التنفس", "chest": "الصدر والقلب", "neuro": "الأعصاب والسكتة",
                   "allergy": "الحساسية", "infection": "عدوى وحرارة"},
        "disclaimer": DISCLAIMER_AR, "dir": "rtl",
    },
    "en": {
        "title": "🩺 Medical Triage Expert System",
        "sub": "Educational triage-support tool using rules from official medical sources (ESI / NHS) - not a diagnosis",
        "lang": "Language", "intake": "Basic information", "age": "Age", "unit": "Unit",
        "units": ["years", "months"], "unknown_hint": "Leave 0 if unknown",
        "pain": "Pain score (0-10)", "tab1": "📝 Quick assessment", "tab2": "💬 Smart interview",
        "assess": "Assess", "yes": "Yes", "no": "No", "reset": "Start over",
        "q": "Question", "why": "Why this result?", "sources": "Sources", "conf": "Confidence",
        "rules_fired": "Rules that fired", "interview_hint": "I'll ask only what is needed, in order.",
        "groups": {"consciousness": "Consciousness", "breathing": "Breathing", "chest": "Chest / heart", "neuro": "Neurological / stroke",
                   "allergy": "Allergy", "infection": "Infection / fever"},
        "disclaimer": DISCLAIMER_EN, "dir": "ltr",
    },
}

with st.sidebar:
    lang = "ar" if st.radio("Language / اللغة", ["العربية", "English"]) == "العربية" else "en"
    T = TXT[lang]
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
    st.markdown("<style>.main, [data-testid='stSidebar']{direction:rtl;text-align:right;}</style>", unsafe_allow_html=True)

base = {
    "age_months": age_val if unit == T["units"][1] else age_val * 12,
    "temp_c": temp or None, "hr": hr or None, "rr": rr or None, "spo2": spo2 or None,
    "pain_score": float(pain),
}


def render_result(result):
    ex = explain(result, sources, lang)
    info = ex["level_info"]
    st.markdown(
        f"<div style='background:{info['color']};color:white;padding:18px;border-radius:12px;font-size:1.3rem'>"
        f"<b>{info['name_' + lang]}</b><br><span style='font-size:1rem'>{info['advice_' + lang]}</span></div>",
        unsafe_allow_html=True)
    st.write("")
    st.progress(min(result["cf"], 1.0), text=f"{T['conf']}: {result['cf']:.0%}")
    with st.expander(T["why"], expanded=True):
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
        render_result(engine.forward(answers))

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
        st.subheader(f"{T['q']} {len(st.session_state.iv) + 1}")
        st.markdown(f"### {catalog[fact][lang]}؟" if lang == "ar" else f"### {catalog[fact][lang]}?")
        c1, c2 = st.columns(2)
        if c1.button(T["yes"], key=f"y_{fact}", use_container_width=True):
            st.session_state.iv[fact] = True
            st.rerun()
        if c2.button(T["no"], key=f"n_{fact}", use_container_width=True):
            st.session_state.iv[fact] = False
            st.rerun()
    else:
        render_result(result)
