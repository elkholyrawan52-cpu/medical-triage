"""Triage levels (modelled on the 5-level ESI idea, simplified to 4 outputs)."""

EMERGENCY_NUMBER_EG = "123"  # Egypt ambulance number - verify locally before deployment

LEVELS = {
    1: {
        "key": "immediate", "color": "#b71c1c",
        "name_ar": "طوارئ فورية (ESI 1)", "name_en": "Immediate - life threatening (ESI 1)",
        "advice_ar": f"اتصل بالإسعاف فورًا ({EMERGENCY_NUMBER_EG} في مصر). متسوقش بنفسك للمستشفى. ابدأ الإسعافات الأولية لو تعرف.",
        "advice_en": f"Call emergency services now ({EMERGENCY_NUMBER_EG} in Egypt). Do not drive yourself. Start first aid if you know how.",
    },
    2: {
        "key": "emergent", "color": "#e65100",
        "name_ar": "طارئ عالي الخطورة (ESI 2)", "name_en": "Emergent - high risk (ESI 2)",
        "advice_ar": f"اطلب الإسعاف أو روح الطوارئ فورًا ({EMERGENCY_NUMBER_EG} في مصر). الحالة ما ينفعش تستنى.",
        "advice_en": f"Call emergency services or go to the emergency department now ({EMERGENCY_NUMBER_EG} in Egypt). This should not wait.",
    },
    3: {
        "key": "urgent", "color": "#f9a825",
        "name_ar": "عاجل - محتاج تقييم طبي النهارده", "name_en": "Urgent - needs medical assessment today",
        "advice_ar": "كلّم الطبيب أو روح عيادة/طوارئ النهارده. لو الأعراض زادت أو ظهرت علامات خطر اطلب الإسعاف.",
        "advice_en": "Speak to a doctor or visit a clinic/emergency department today. If symptoms worsen or red flags appear, call emergency services.",
    },
    4: {
        "key": "non_urgent", "color": "#2e7d32",
        "name_ar": "غير عاجل - لم تظهر علامات خطر", "name_en": "Non-urgent - no red flags found",
        "advice_ar": "النظام ما لقاش علامات خطر من قاعدة معرفته المحدودة. ده مش تأكيد إنك بخير: لو الأعراض استمرت أو زادت راجع طبيب.",
        "advice_en": "No red flags were found in this system's limited knowledge base. This is not a guarantee you are well: see a doctor if symptoms persist or worsen.",
    },
}

DISCLAIMER_AR = "⚠️ هذا النظام مساعد فرز تعليمي وليس تشخيصًا ولا بديلًا عن الطبيب. في أي شك أو حالة طارئة اتصل بالإسعاف."
DISCLAIMER_EN = "⚠️ This is an educational triage-support tool, not a diagnosis and not a substitute for a doctor. If in doubt or in an emergency, call emergency services."
