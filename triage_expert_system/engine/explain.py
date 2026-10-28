"""Explanation facility: turns an inference result into human-readable, source-cited lines."""
from .levels import LEVELS


def explain(result, sources, lang="ar"):
    key = "reason_" + lang
    lines = []
    for r in result["fired"]:
        lines.append({
            "id": r["id"],
            "kind": r["type"],
            "text": r[key],
            "level": r.get("then", {}).get("level"),
            "cf": r.get("cf"),
            "sources": [dict(sources[s], id=s) for s in r.get("sources", [])],
        })
    unique = {}
    for ln in lines:
        for s in ln["sources"]:
            unique[s["id"]] = s
    if result.get("default"):
        text = ("لم تنطبق أي قاعدة خطر. هذا النتيجة الافتراضية للنظام وليست تأكيدًا على سلامة الحالة."
                if lang == "ar" else
                "No red-flag rule fired. This is the system default, not a guarantee that the case is safe.")
        lines.append({"id": "DEFAULT", "kind": "default", "text": text, "level": 4, "cf": result["cf"],
                      "sources": [dict(sources["SYSTEM_DEFAULT"], id="SYSTEM_DEFAULT")]})
    return {
        "level_info": LEVELS[result["level"]],
        "lines": lines,
        "sources": list(unique.values()),
        "danger_details": result.get("danger_details", []),
    }


def format_text(result, sources, lang="ar"):
    info = LEVELS[result["level"]]
    ex = explain(result, sources, lang)
    out = [f"== {info['name_' + lang]} | CF = {result['cf']:.2f} ==", info["advice_" + lang], ""]
    for ln in ex["lines"]:
        cf = f" (CF {ln['cf']:.2f})" if ln["cf"] is not None and ln["kind"] == "conclude" else ""
        out.append(f"- [{ln['id']}] {ln['text']}{cf}")
    if ex["danger_details"]:
        out.append("- ESI danger-zone: " + "; ".join(ex["danger_details"]))
    if ex["sources"]:
        out.append("")
        out.append("Sources:")
        for s in ex["sources"]:
            out.append(f"  * {s['org']} - {s['title']} {s['url']}")
    return "\n".join(out)
