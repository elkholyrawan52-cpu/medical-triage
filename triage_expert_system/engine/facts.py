"""Computed facts that are not simple rules: ESI 'danger zone vitals' by age.

Source: ESI v4 Handbook (AHRQ), Figure 3-5 - Decision point D.
  Age            HR      RR
  < 3 months     > 180   > 50
  3 m - 3 y      > 160   > 40
  3 - 8 y        > 140   > 30
  > 8 y          > 100   > 20
  SpO2 < 92% at any age.
"""


def esi_danger_zone(age_months, hr, rr, spo2):
    """Return (is_danger_zone: bool, details: list[str]). Unknown values (None) are ignored."""
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
