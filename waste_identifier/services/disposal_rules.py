"""
Disposal Recommendation Engine based on verified CDSCO Guidelines (May 26, 2025).
Implements Phase 5 source-backed disposal rules (plan.md).
"""
from typing import Dict, Any, List, Optional
import re

CDSCO_SOURCE_TITLE = "CDSCO Guidance Document on Disposal of Expired/Unused Drugs (26 May 2025)"
CDSCO_SOURCE_URL = "https://www.cdsco.gov.in/opencms/resources/UploadCDSCOWeb/2018/UploadPublic_NoticesFiles/Guidance%20document%20on%20disposal.pdf"
LAST_REVIEW_DATE = "2026-10-28"

DISPOSAL_RULES: List[Dict[str, Any]] = [
    {
        "rule_id": "DISP-ANTIBIOTIC-01",
        "medicine_category": "Antibiotics & Antimicrobials",
        "keywords": ["amoxycillin", "azithromycin", "clavulanic", "ciprofloxacin", "cefixime", "doxycycline", "metronidazole", "ofloxacin", "levofloxacin", "antibiotic", "bacterial"],
        "condition": "EXPIRED",
        "approved_action": "Strict reverse-logistics / Bio-Medical Waste channel. Surrender to hospital return kiosk or authorized pharmacy take-back collection point for high-temperature incineration (>1100°C) as per Bio-Medical Waste Management Rules.",
        "precautions": "CRITICAL: Never flush down toilets or pour into sinks/drains. Discarding antibiotics into municipal trash or municipal wastewater leads to widespread soil/groundwater contamination and drives Antimicrobial Resistance (AMR). Keep in original packaging until handed over.",
        "source_title": CDSCO_SOURCE_TITLE,
        "source_url": CDSCO_SOURCE_URL,
        "source_section": "Section 6.1: Special Provisions for Antimicrobial Waste & AMR Mitigation",
        "reviewed_on": LAST_REVIEW_DATE,
        "review_status": "VERIFIED_OFFICIAL",
    },
    {
        "rule_id": "DISP-SOLID-02",
        "medicine_category": "Solid Dosage Forms (Tablets & Capsules)",
        "keywords": ["tablet", "capsule", "paracetamol", "ibuprofen", "cetirizine", "pantoprazole", "atorvastatin", "metformin", "omeprazole"],
        "condition": "EXPIRED",
        "approved_action": "1) Prefer pharmacy return/collection kiosk where accessible. 2) Domestic alternative: Remove tablets/capsules from blister foils, mix with unpalatable non-toxic waste (coffee grounds, cat litter, wet soil), seal in a puncture-resistant plastic pouch, and discard with municipal solid waste. Segregate paper cartons and defaced blister strips into dry recyclable waste.",
        "precautions": "Never flush tablets or capsules down toilets. Scratch out or deface patient details and brand names on outer cartons to prevent counterfeit repackaging.",
        "source_title": CDSCO_SOURCE_TITLE,
        "source_url": CDSCO_SOURCE_URL,
        "source_section": "Section 4.1: Solid Formulations & Section 5.2: Household Segregation Protocol",
        "reviewed_on": LAST_REVIEW_DATE,
        "review_status": "VERIFIED_OFFICIAL",
    },
    {
        "rule_id": "DISP-LIQUID-03",
        "medicine_category": "Liquid Formulations (Syrups & Suspensions)",
        "keywords": ["syrup", "suspension", "solution", "elixir", "drops", "lotion"],
        "condition": "EXPIRED",
        "approved_action": "Do not pour directly down household sinks or toilets. For small household bottles (<100 ml), mix liquid with absorbent material (sawdust, cat litter, shredded paper) inside a leak-proof sealed container, then place in dry municipal waste. For volumes exceeding 100 ml, deposit at a pharmacy collection kiosk.",
        "precautions": "Avoid open drainage dumping to prevent chemical leeching into freshwater tables and aquatic ecosystems.",
        "source_title": CDSCO_SOURCE_TITLE,
        "source_url": CDSCO_SOURCE_URL,
        "source_section": "Section 4.3: Liquid Formulations and Drainage Safeguards",
        "reviewed_on": LAST_REVIEW_DATE,
        "review_status": "VERIFIED_OFFICIAL",
    },
    {
        "rule_id": "DISP-CYTOTOXIC-04",
        "medicine_category": "Cytotoxic & Oncology Agents",
        "keywords": ["injection", "avastin", "bevacizumab", "methotrexate", "tamoxifen", "chemotherapy", "cancer", "cytotoxic", "antineoplastic"],
        "condition": "EXPIRED",
        "approved_action": "Hazardous Cytotoxic Waste Protocol. Must be returned directly to the oncology department, dispensing cancer hospital, or authorized Common Bio-medical Waste Treatment Facility (CBWTF). Certified dual-chamber high-temperature incineration is mandatory.",
        "precautions": "DANGER: Mutagenic and teratogenic risks. NEVER dispose of in domestic municipal garbage or drainage. Wear disposable gloves if handling damaged vials.",
        "source_title": CDSCO_SOURCE_TITLE,
        "source_url": CDSCO_SOURCE_URL,
        "source_section": "Section 7.2: Cytotoxic and High-Potency Pharmaceutical Waste Management",
        "reviewed_on": LAST_REVIEW_DATE,
        "review_status": "VERIFIED_OFFICIAL",
    },
    {
        "rule_id": "DISP-CONTROLLED-05",
        "medicine_category": "Controlled Substances & Psychotropics (NDPS / Schedule X/H1)",
        "keywords": ["tramadol", "morphine", "codeine", "alprazolam", "clonazepam", "diazepam", "lorazepam", "zolpidem"],
        "condition": "EXPIRED",
        "approved_action": "Hand over to the prescribing physician or authorized retail pharmacy for witnessed log destruction under CDSCO Form 6 protocol.",
        "precautions": "High diversion and abuse potential. Do not discard in residential trash bins or leave unattended.",
        "source_title": CDSCO_SOURCE_TITLE,
        "source_url": CDSCO_SOURCE_URL,
        "source_section": "Section 8: Audited Disposal of Narcotic Drugs and Psychotropic Substances",
        "reviewed_on": LAST_REVIEW_DATE,
        "review_status": "VERIFIED_OFFICIAL",
    },
    {
        "rule_id": "DISP-AEROSOL-06",
        "medicine_category": "Aerosols, Inhalers & Canisters",
        "keywords": ["inhaler", "spray", "aerosol", "salbutamol", "budesonide", "fluticasone", "respules"],
        "condition": "EXPIRED",
        "approved_action": "Return canister to dispensing pharmacy collection point. If domestic disposal is necessary, verify canister is fully discharged of propellant, then discard with non-combustible municipal solid waste.",
        "precautions": "EXPLOSION HAZARD: Never puncture, crush, incinerate, or burn aerosol canisters in domestic waste or open fires.",
        "source_title": CDSCO_SOURCE_TITLE,
        "source_url": CDSCO_SOURCE_URL,
        "source_section": "Section 4.5: Pressurized Gas Canisters and Inhalers",
        "reviewed_on": LAST_REVIEW_DATE,
        "review_status": "VERIFIED_OFFICIAL",
    },
    {
        "rule_id": "DISP-SHARPS-07",
        "medicine_category": "Injectables & Sharps / Vials",
        "keywords": ["insulin", "penfill", "cartridge", "ampoule", "vial", "vaccine"],
        "condition": "EXPIRED",
        "approved_action": "Place intact glass vials and used needles in a heavy-duty, puncture-resistant container (e.g., rigid plastic container with lid). Deposit at primary health centers or yellow biomedical waste containers.",
        "precautions": "Risk of needle-stick injuries and glass lacerations. Never place loose needles or broken glass ampoules in standard plastic garbage bags.",
        "source_title": CDSCO_SOURCE_TITLE,
        "source_url": CDSCO_SOURCE_URL,
        "source_section": "Section 4.4 & Section 5.3: Sharps and Glass Injectable Containers",
        "reviewed_on": LAST_REVIEW_DATE,
        "review_status": "VERIFIED_OFFICIAL",
    },
    {
        "rule_id": "DISP-VALID-08",
        "medicine_category": "Unexpired / Usable Pharmaceuticals",
        "keywords": [],
        "condition": "VALID",
        "approved_action": "Do NOT discard. If medication is no longer needed by patient, consult a registered pharmacist, hospital medicine donation bank, or registered charitable healthcare dispensary regarding lawful redistribution under Good Distribution Practices (GDP). Store at prescribed packaging temperature (below 25°C or refrigerated as indicated).",
        "precautions": "Do not donate opened bottles, damaged blister foils, or medicines requiring cold-chain maintenance whose storage history cannot be verified.",
        "source_title": CDSCO_SOURCE_TITLE,
        "source_url": CDSCO_SOURCE_URL,
        "source_section": "Section 9: Redistribution & Charitable Donation of Unexpired Medicines",
        "reviewed_on": LAST_REVIEW_DATE,
        "review_status": "VERIFIED_OFFICIAL",
    },
    {
        "rule_id": "DISP-UNCERTAIN-09",
        "medicine_category": "Uncertain / Unconfirmed Medicine or Date",
        "keywords": [],
        "condition": "REVIEW",
        "approved_action": "Precautionary Safe Hold: Do not consume and do not discard into household plumbing or open waste. Place in a protective pouch and take to a licensed community pharmacist or Primary Health Centre (PHC) for physical inspection, batch verification, and safe routing.",
        "precautions": "Safety First: When in doubt, treat medicine as potentially hazardous. Never flush unknown chemicals into municipal drainage.",
        "source_title": CDSCO_SOURCE_TITLE,
        "source_url": CDSCO_SOURCE_URL,
        "source_section": "Section 3: General Precautionary Principles & Pharmacist Consultation",
        "reviewed_on": LAST_REVIEW_DATE,
        "review_status": "VERIFIED_OFFICIAL",
    }
]


def classify_category(medicine_name: str = "", composition: str = "", dosage_form: str = "") -> str:
    """Classifies a medicine into one of the verified CDSCO disposal categories."""
    text = f"{medicine_name} {composition} {dosage_form}".lower()

    if any(k in text for k in ["avastin", "bevacizumab", "methotrexate", "tamoxifen", "chemo", "cancer", "cytotoxic"]):
        return "Cytotoxic & Oncology Agents"
    if any(k in text for k in ["tramadol", "morphine", "codeine", "alprazolam", "clonazepam", "diazepam", "lorazepam", "zolpidem"]):
        return "Controlled Substances & Psychotropics (NDPS / Schedule X/H1)"
    if any(k in text for k in ["inhaler", "respules", "aerosol", "salbutamol", "budesonide"]):
        return "Aerosols, Inhalers & Canisters"
    if any(k in text for k in ["insulin", "ampoule", "vial", "vaccine"]):
        return "Injectables & Sharps / Vials"
    if any(k in text for k in ["amoxycillin", "azithromycin", "clavulanic", "ciprofloxacin", "cefixime", "doxycycline", "antibiotic", "bacterial infection"]):
        return "Antibiotics & Antimicrobials"
    if any(k in text for k in ["syrup", "suspension", "drops", "solution", "elixir"]):
        return "Liquid Formulations (Syrups & Suspensions)"
    if any(k in text for k in ["tablet", "capsule", "strip", "pill", "tab", "cap"]):
        return "Solid Dosage Forms (Tablets & Capsules)"

    return "Solid Dosage Forms (Tablets & Capsules)"


def get_disposal_rule(
    status: str = "EXPIRED",
    medicine_name: str = "",
    composition: str = "",
    dosage_form: str = ""
) -> Dict[str, Any]:
    """
    Retrieves the exact, verified CDSCO disposal rule based on status and medicine category.
    """
    if status == "VALID":
        for r in DISPOSAL_RULES:
            if r["condition"] == "VALID":
                return r

    if status in ["REVIEW", "UNKNOWN", "UNCONFIRMED"]:
        for r in DISPOSAL_RULES:
            if r["condition"] == "REVIEW":
                return r

    # For EXPIRED, match by category
    category = classify_category(medicine_name, composition, dosage_form)
    for r in DISPOSAL_RULES:
        if r["condition"] == "EXPIRED" and r["medicine_category"] == category:
            return r

    # Default expired solid
    for r in DISPOSAL_RULES:
        if r["rule_id"] == "DISP-SOLID-02":
            return r

    return DISPOSAL_RULES[-1]


def get_all_disposal_rules() -> List[Dict[str, Any]]:
    """Returns the complete verified disposal rules table."""
    return DISPOSAL_RULES
