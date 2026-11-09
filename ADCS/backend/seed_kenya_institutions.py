"""
Idempotent seed: Kenyan higher-education & TVET institutions for ADCS.
- Safe: inserts only missing institutions (matched by code). Never deletes or overwrites existing records.
- Uses the app's configured primary database (MySQL/MariaDB via DATABASE_URL/.env).
Run:  cd ADCS/backend && .\\.venv\\Scripts\\python.exe seed_kenya_institutions.py
"""
from __future__ import annotations

from sqlalchemy import func
from app.core.database import SessionLocal
from app.models.institution import Institution

# (name, code, type) — type: university | college | tvet | polytechnic
# Codes are stable identifiers for idempotent upserts.
KENYA_INSTITUTIONS: list[tuple[str, str, str]] = [
    # Chartered Public Universities
    ("University of Nairobi", "UON", "university"),
    ("Kenyatta University", "KU", "university"),
    ("Moi University", "MU", "university"),
    ("Egerton University", "EU", "university"),
    ("Jomo Kenyatta University of Agriculture and Technology", "JKUAT", "university"),
    ("Maseno University", "MASENO", "university"),
    ("Masinde Muliro University of Science and Technology", "MMUST", "university"),
    ("Dedan Kimathi University of Technology", "DKUT", "university"),
    ("Chuka University", "CHUKA", "university"),
    ("Technical University of Kenya", "TUK", "university"),
    ("Technical University of Mombasa", "TUM", "university"),
    ("Pwani University", "PWANI", "university"),
    ("Kisii University", "KISII", "university"),
    ("University of Eldoret", "UOE", "university"),
    ("Maasai Mara University", "MMARAU", "university"),
    ("Jaramogi Oginga Odinga University of Science and Technology", "JOOUST", "university"),
    ("Laikipia University", "LAIKIPIA", "university"),
    ("South Eastern Kenya University", "SEKU", "university"),
    ("Meru University of Science and Technology", "MUST", "university"),
    ("Multimedia University of Kenya", "MMU", "university"),
    ("University of Kabianga", "UOK", "university"),
    ("Karatina University", "KARU", "university"),
    ("Kibabii University", "KIBU", "university"),
    ("Rongo University", "RONGO", "university"),
    ("Co-operative University of Kenya", "CUK", "university"),
    ("Taita Taveta University", "TTU", "university"),
    ("Murang'a University of Technology", "MUT", "university"),
    ("University of Embu", "UOEM", "university"),
    ("Machakos University", "MKS", "university"),
    ("Kirinyaga University", "KYU", "university"),
    ("Garissa University", "GARISSA", "university"),
    ("Alupe University", "AU", "university"),
    ("Kaimosi Friends University", "KAFU", "university"),
    ("Tom Mboya University", "TMU", "university"),
    ("Tharaka University", "THARAKA", "university"),
    ("National Defence University-Kenya", "NDUK", "university"),
    ("Open University of Kenya", "OUK", "university"),
    ("Bomet University College", "BUC", "college"),
    ("Turkana University College", "TUC", "college"),
    ("Koitalel Samoei University College", "KSUC", "college"),
    ("Kenya Advanced Institute of Science and Technology", "KAIST", "university"),
    # Chartered Private Universities
    ("University of Eastern Africa, Baraton", "UEAB", "university"),
    ("Catholic University of Eastern Africa", "CUEA", "university"),
    ("Daystar University", "DAYSTAR", "university"),
    ("Scott Christian University", "SCOTT", "university"),
    ("United States International University-Africa", "USIU", "university"),
    ("Africa Nazarene University", "ANU", "university"),
    ("Kenya Methodist University", "KEMU", "university"),
    ("St. Paul's University", "SPU", "university"),
    ("Pan Africa Christian University", "PACU", "university"),
    ("Strathmore University", "STRATHMORE", "university"),
    ("Kabarak University", "KABARAK", "university"),
    ("Mount Kenya University", "MKU", "university"),
    ("Africa International University", "AIU", "university"),
    ("Kenya Highlands Evangelical University", "KHEU", "university"),
    ("Great Lakes University of Kisumu", "GLUK", "university"),
    ("KCA University", "KCA", "university"),
    ("Adventist University of Africa", "AUA", "university"),
    ("KAG EAST University", "KAGEAST", "university"),
    ("Umma University", "UMMA", "university"),
    ("Presbyterian University of East Africa", "PUEA", "university"),
    ("Aga Khan University", "AKU", "university"),
    ("Kiriri Women's University of Science and Technology", "KWUST", "university"),
    ("The East African University", "TEAU", "university"),
    ("Zetech University", "ZETECH", "university"),
    ("Lukenya University", "LUKENYA", "university"),
    ("Management University of Africa", "MUA", "university"),
    ("Tangaza University", "TANGAZA", "university"),
    ("Islamic University of Kenya", "IUK", "university"),
    ("Riara University", "RIARA", "university"),
    ("Pioneer International University", "PIU", "university"),
    ("International Leadership University", "ILU", "university"),
    ("Amref International University", "AMIU", "university"),
    ("Uzima University", "UZIMA", "university"),
    # National Polytechnics
    ("The Kabete National Polytechnic", "KABETE-NP", "polytechnic"),
    ("The Kisumu National Polytechnic", "KISUMU-NP", "polytechnic"),
    ("The Eldoret National Polytechnic", "ELDORET-NP", "polytechnic"),
    ("The Meru National Polytechnic", "MERU-NP", "polytechnic"),
    ("The Sigalagala National Polytechnic", "SIGALAGALA-NP", "polytechnic"),
    ("The Nyeri National Polytechnic", "NYERI-NP", "polytechnic"),
    ("The Coast National Polytechnic", "COAST-NP", "polytechnic"),
    ("The Kitale National Polytechnic", "KITALE-NP", "polytechnic"),
    ("The Kisii National Polytechnic", "KISII-NP", "polytechnic"),
    ("The North Eastern National Polytechnic", "NENP", "polytechnic"),
    ("The Bungoma National Polytechnic", "BUNGOMA-NP", "polytechnic"),
    # TVET / Technical & Vocational Colleges (representative national network)
    ("Nairobi Technical Training Institute", "NAIROBI-TTI", "tvet"),
    ("Kiambu Institute of Science and Technology", "KIST", "tvet"),
    ("Thika Technical Training Institute", "THIKA-TTI", "tvet"),
    ("PC Kinyanjui Technical Training Institute", "PCK-TTI", "tvet"),
    ("Ramogi Institute of Advanced Technology", "RIAT", "tvet"),
    ("Ol'lessos Technical Training Institute", "OLLESSOS-TTI", "tvet"),
    ("Rift Valley Institute of Science and Technology", "RVIST", "tvet"),
    ("Machakos Technical Institute for the Blind", "MTIB", "tvet"),
    ("Kaiboi Technical Training Institute", "KAIBOI-TTI", "tvet"),
    ("Bumbe Technical Training Institute", "BUMBE-TTI", "tvet"),
    ("Sang'alo Institute of Science and Technology", "SANGALO-IST", "tvet"),
    ("Michuki Technical Training Institute", "MICHUKI-TTI", "tvet"),
    ("Mitunguu Technical Training Institute", "MITUNGUU-TTI", "tvet"),
    ("Mawego Technical Training Institute", "MAWEGO-TTI", "tvet"),
    ("Siaya Institute of Technology", "SIAYA-IT", "tvet"),
    ("Wote Technical Training Institute", "WOTE-TTI", "tvet"),
    ("Nkabune Technical Training Institute", "NKABUNE-TTI", "tvet"),
    ("Eldoret Technical Training Institute", "ELDORET-TTI", "tvet"),
    ("Keroka Technical Training Institute", "KEROKA-TTI", "tvet"),
    ("Kitale Technical Training Institute", "KITALE-TTI", "tvet"),
    ("Mathenge Technical Training Institute", "MATHENGE-TTI", "tvet"),
    ("Nyandarua National Polytechnic (TVET)", "NYANDARUA-TVC", "tvet"),
    ("Kiirua Technical Training Institute", "KIIRUA-TTI", "tvet"),
    ("Bushiangala Technical Training Institute", "BUSHIANGALA-TTI", "tvet"),
    ("Bureti Technical Vocational College", "BURETI-TVC", "tvet"),
    ("Karen Technical Training Institute for the Deaf", "KAREN-TTID", "tvet"),
    ("Baringo Technical College", "BARINGO-TC", "tvet"),
    ("Ahero Technical Training Institute", "AHERO-TTI", "tvet"),
    ("Borabu Technical Training Institute", "BORABU-TTI", "tvet"),
    ("Gatundu South Technical and Vocational College", "GATUNDU-TVC", "tvet"),
    ("Runyenjes Technical and Vocational College", "RUNYENJES-TVC", "tvet"),
    ("Weru Technical and Vocational College", "WERU-TVC", "tvet"),
    ("Kieni Technical and Vocational College", "KIENI-TVC", "tvet"),
    ("Mukurweini Technical and Vocational College", "MUKURWEINI-TVC", "tvet"),
    ("Tetu Technical and Vocational College", "TETU-TVC", "tvet"),
]


def seed() -> dict[str, int]:
    db = SessionLocal()
    added = 0
    skipped = 0
    try:
        for name, code, inst_type in KENYA_INSTITUTIONS:
            exists = db.query(Institution.id).filter(func.lower(Institution.code) == code.lower()).first()
            if exists:
                skipped += 1
                continue
            # Also guard by name to avoid duplicates from prior imports
            by_name = db.query(Institution.id).filter(func.lower(Institution.name) == name.lower()).first()
            if by_name:
                skipped += 1
                continue
            db.add(Institution(name=name, code=code, type=inst_type, country="Kenya", is_active=True))
            added += 1
        db.commit()
        total = db.query(func.count(Institution.id)).scalar() or 0
    finally:
        db.close()
    return {"added": added, "skipped": skipped, "total": total}


if __name__ == "__main__":
    result = seed()
    print(f"Kenya institutions seed complete: added={result['added']} skipped={result['skipped']} total={result['total']}")