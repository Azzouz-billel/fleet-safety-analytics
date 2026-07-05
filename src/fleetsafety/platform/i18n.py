"""French + Arabic labels (guide: bilingual from the start).

Rendered as "français · العربية" so one template serves both audiences;
a per-user language switch can replace `label` later without touching
templates.
"""

LABELS = {
    "app_title": ("Sécurité de flotte", "سلامة الأسطول"),
    "tagline": ("Accompagnement, pas surveillance", "مرافقة، وليس مراقبة"),
    "fleet_overview": ("Vue d'ensemble de la flotte", "نظرة عامة على الأسطول"),
    "driver": ("Conducteur", "السائق"),
    "drivers": ("Conducteurs", "السائقون"),
    "safety_score": ("Score de sécurité", "درجة السلامة"),
    "score_trend": ("Évolution du score", "تطور الدرجة"),
    "weekly_scores": ("Scores hebdomadaires", "الدرجات الأسبوعية"),
    "trips": ("Trajets", "الرحلات"),
    "worst_trips": ("Trajets à améliorer", "رحلات للتحسين"),
    "distance": ("Distance", "المسافة"),
    "duration": ("Durée", "المدة"),
    "events": ("Événements", "الأحداث"),
    "event_type": ("Type d'événement", "نوع الحدث"),
    "severity": ("Gravité", "الخطورة"),
    "risk_map": ("Carte des risques", "خريطة المخاطر"),
    "risk_map_hint": (
        "Zones où les événements se répètent — priorités de sensibilisation",
        "مناطق تتكرر فيها الأحداث — أولويات التوعية",
    ),
    "date": ("Date", "التاريخ"),
    "time": ("Heure", "الوقت"),
    "week_of": ("Semaine du", "أسبوع"),
    "no_data": ("Pas encore de données", "لا توجد بيانات بعد"),
    "speeding": ("Excès de vitesse", "تجاوز السرعة"),
    "harsh_braking": ("Freinage brusque", "فرملة مفاجئة"),
    "harsh_accel": ("Accélération brusque", "تسارع مفاجئ"),
    "tailgating": ("Distance de sécurité", "مسافة الأمان"),
    "coaching_note": (
        "Les scores servent à accompagner les conducteurs, pas à les sanctionner.",
        "الدرجات وسيلة لمرافقة السائقين، لا لمعاقبتهم.",
    ),
}


def label(key: str) -> str:
    fr, ar = LABELS.get(key, (key, key))
    return f"{fr} · {ar}"


def label_fr(key: str) -> str:
    return LABELS.get(key, (key, key))[0]
