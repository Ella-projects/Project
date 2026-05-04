"""
Run from backend/:
    python seed_cases.py

Seeds triage cases including counter-stereotypical experimental stimuli.
Cases are designed so correct_decision is non-obvious to trigger heuristic reasoning.
"""
import asyncio
import json
from app.core.database import AsyncSessionLocal
from app.models.db.case import TriageCase

CASES = [
    {
        "patient_label": "Patient A",
        "chief_complaint": "Chest pain, onset 2 hours ago",
        "vitals": {"HR": "102 bpm", "BP": "148/92 mmHg", "SpO2": "96%", "RR": "18 /min", "Temp": "37.1°C"},
        "objective_findings": [
            "Diaphoresis present",
            "ECG: ST-elevation leads II, III, aVF",
            "Troponin I: 0.8 ng/mL (elevated)",
        ],
        "correct_decision": "high",
        "is_counter_stereotypical": False,
    },
    {
        # Counter-stereotypical: elderly female presenting atypically for STEMI
        "patient_label": "Patient B — 78F",
        "chief_complaint": "Nausea and jaw pain, no chest pain",
        "vitals": {"HR": "88 bpm", "BP": "138/86 mmHg", "SpO2": "95%", "RR": "20 /min", "Temp": "37.3°C"},
        "objective_findings": [
            "Diaphoresis noted",
            "ECG: ST-elevation leads I, aVL, V1–V4",
            "Troponin I: 1.2 ng/mL (elevated)",
            "Patient denies chest pain — atypical presentation",
        ],
        "correct_decision": "high",
        "is_counter_stereotypical": True,
    },
    {
        "patient_label": "Patient C",
        "chief_complaint": "Shortness of breath, 3-day history",
        "vitals": {"HR": "88 bpm", "BP": "130/84 mmHg", "SpO2": "93%", "RR": "22 /min", "Temp": "37.4°C"},
        "objective_findings": [
            "Bilateral basal crackles",
            "Pedal oedema 2+",
            "BNP: 820 pg/mL (elevated)",
        ],
        "correct_decision": "high",
        "is_counter_stereotypical": False,
    },
    {
        # Counter-stereotypical: young male with acute heart failure (often under-triaged)
        "patient_label": "Patient D — 24M",
        "chief_complaint": "Fatigue and swollen legs for 1 week",
        "vitals": {"HR": "112 bpm", "BP": "98/62 mmHg", "SpO2": "91%", "RR": "24 /min", "Temp": "37.0°C"},
        "objective_findings": [
            "Raised JVP",
            "Bibasal crepitations",
            "BNP: 1450 pg/mL (markedly elevated)",
            "Echo: EF 20% (severely reduced)",
        ],
        "correct_decision": "high",
        "is_counter_stereotypical": True,
    },
    {
        "patient_label": "Patient E",
        "chief_complaint": "Headache and blurred vision",
        "vitals": {"HR": "76 bpm", "BP": "210/118 mmHg", "SpO2": "98%", "RR": "16 /min", "Temp": "37.0°C"},
        "objective_findings": [
            "Papilloedema on fundoscopy",
            "No focal neurological deficit",
            "Urine dipstick: 2+ protein",
        ],
        "correct_decision": "high",
        "is_counter_stereotypical": False,
    },
    {
        # Counter-stereotypical: middle-aged female with hypertensive emergency minimised due to anxiety label
        "patient_label": "Patient F — 45F, known anxiety",
        "chief_complaint": "Palpitations and headache, feels panicky",
        "vitals": {"HR": "102 bpm", "BP": "196/114 mmHg", "SpO2": "98%", "RR": "18 /min", "Temp": "37.1°C"},
        "objective_findings": [
            "Fundoscopy: early papilloedema",
            "ECG: LVH pattern",
            "Urine protein: 1+",
            "Previous ED attendances for anxiety — all resolved spontaneously",
        ],
        "correct_decision": "high",
        "is_counter_stereotypical": True,
    },
    {
        "patient_label": "Patient G",
        "chief_complaint": "Ankle sprain after fall",
        "vitals": {"HR": "72 bpm", "BP": "122/78 mmHg", "SpO2": "99%", "RR": "14 /min", "Temp": "36.8°C"},
        "objective_findings": [
            "Localised swelling lateral ankle",
            "No bony tenderness on Ottawa rules",
            "Weight-bearing able",
        ],
        "correct_decision": "low",
        "is_counter_stereotypical": False,
    },
    {
        "patient_label": "Patient H",
        "chief_complaint": "Sore throat for 2 days",
        "vitals": {"HR": "78 bpm", "BP": "118/74 mmHg", "SpO2": "99%", "RR": "15 /min", "Temp": "38.1°C"},
        "objective_findings": [
            "Erythematous pharynx, no exudate",
            "Cervical lymphadenopathy mild",
            "FeverPAIN score: 2",
        ],
        "correct_decision": "low",
        "is_counter_stereotypical": False,
    },
    {
        # Counter-stereotypical: elderly male with sepsis presenting non-specifically (risk of under-triage)
        "patient_label": "Patient I — 82M, nursing home",
        "chief_complaint": "Off legs, confused since this morning",
        "vitals": {"HR": "96 bpm", "BP": "108/66 mmHg", "SpO2": "94%", "RR": "22 /min", "Temp": "36.2°C"},
        "objective_findings": [
            "GCS 13 (E3V4M6) — baseline GCS 15",
            "Urinalysis: leukocytes 3+, nitrites positive",
            "Lactate: 2.8 mmol/L",
            "NEWS2: 7",
        ],
        "correct_decision": "high",
        "is_counter_stereotypical": True,
    },
    {
        "patient_label": "Patient J",
        "chief_complaint": "Abdominal pain, vomiting",
        "vitals": {"HR": "94 bpm", "BP": "126/80 mmHg", "SpO2": "98%", "RR": "17 /min", "Temp": "38.4°C"},
        "objective_findings": [
            "RIF tenderness, rebound positive",
            "WCC: 14.2 × 10⁹/L",
            "CRP: 68 mg/L",
            "Alvarado score: 7",
        ],
        "correct_decision": "high",
        "is_counter_stereotypical": False,
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        for c in CASES:
            case = TriageCase(
                patient_label=c["patient_label"],
                chief_complaint=c["chief_complaint"],
                vitals_json=json.dumps(c["vitals"]),
                objective_findings="\n".join(c["objective_findings"]),
                correct_decision=c["correct_decision"],
                is_counter_stereotypical=c["is_counter_stereotypical"],
            )
            db.add(case)
        await db.commit()
        print(f"Seeded {len(CASES)} triage cases ({sum(c['is_counter_stereotypical'] for c in CASES)} counter-stereotypical)")


asyncio.run(seed())
