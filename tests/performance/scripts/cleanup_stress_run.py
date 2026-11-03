"""Po arhiviranju rezultatov stresnega testa odstrani podatke testnega sklopa.

Skript poskrbi za čiščenje začasnih podatkov, ustvarjenih med izvajanjem večstopenjskega
stresnega testa. Ločeno obravnava:
1. Zbirko 'psi_up' (produkcijsko/primarno bazo), kjer so se med klici AI pomočnika
   preko staging kontejnerja ustvarile seje in sporočila za sintetične testne profile.
   Skript odstrani izključno te testne seje in zagotovi, da 29 originalnih uporabnikov
   in njihovi zgodovinski podatki ostanejo popolnoma nedotaknjeni.
2. Namensko bazo za stresni test ('psi_up_staging_perf_stress_20261103'), kjer so bili
   shranjeni sintetični profili (5.000 uporabnikov).
"""
import json
import sys
from pathlib import Path
from pymongo import MongoClient

# Prilagoditev kodiranja standardnega izhoda na UTF-8 za varno delovanje na Windows sistemih (preprečevanje cp1252 napak)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def get_uri():
    """Prebere povezovalni niz MongoDB URI iz lokalne konfiguracijske datoteke backend/.env."""
    with open('backend/.env', encoding='utf-8') as f:
        for line in f:
            if line.startswith('MONGODB_URI='):
                return line.split('=', 1)[1].strip().strip('\"\'')
    raise ValueError("MONGODB_URI not found v backend/.env")

def main():
    """Glavna izvedbena funkcija za varno in selektivno čiščenje testnih zapisov."""
    uri = get_uri()
    client = MongoClient(uri)
    pool_file = Path('test-results/performance/stress_pool.json')
    if not pool_file.exists():
        print("Evidenca sintetičnih profilov (stress_pool.json) ne obstaja.")
        return

    # Naložimo evidenco generiranih ID-jev, da brišemo izključno tiste profile, ki so pripadali temu testu
    data = json.loads(pool_file.read_text(encoding='utf-8'))
    pool_id = data['pool_id']
    uids = data['user_ids']
    print(f"=== ČIŠČENJE PODATKOV STRESNEGA TESTA ===")
    print(f"Pool ID: {pool_id}, Število profilov v evidenci: {len(uids)}")

    # 1. Korak: Čiščenje AI sej in sporočil v primarni bazi 'psi_up'
    # Med izvajanjem testa je staging kontejner usmerjen na bazo 'psi_up', zato so se klici
    # AI asistenta zabeležili v zbirki assessment_assistant_sessions in assessment_assistant_messages.
    db_psi_up = client['psi_up']
    sessions = list(db_psi_up.assessment_assistant_sessions.find({"user_id": {"$in": uids}}))
    sids = [s["session_id"] for s in sessions]
    
    # Izbrišemo vsa sporočila, ki se nanašajo na najdene seje sintetičnih uporabnikov
    del_msg = db_psi_up.assessment_assistant_messages.delete_many({"session_id": {"$in": sids}})
    # Izbrišemo seje sintetičnih uporabnikov
    del_sess = db_psi_up.assessment_assistant_sessions.delete_many({"user_id": {"$in": uids}})
    
    # Preverjanje celovitosti produkcijskih podatkov: 29 prvotnih uporabnikov mora ostati nespremenjenih
    total_users_psi_up = db_psi_up.users.count_documents({})
    remaining_sess_psi_up = db_psi_up.assessment_assistant_sessions.count_documents({"user_id": {"$in": uids}})
    print(f"psi_up: izbrisanih {del_sess.deleted_count} sej in {del_msg.deleted_count} sporočil.")
    print(f"psi_up: preostalo testnih sej: {remaining_sess_psi_up}, prvotnih uporabnikov: {total_users_psi_up} (pričakovano 29)")

    # 2. Korak: Čiščenje sintetičnih profilov v namenski testni bazi
    # Zaščita z dvojnim preverjanjem: brišemo samo tiste uporabnike, katerih ID se ujema z evidenco in nosi ustrezen pool_id
    stress_db_name = data['database']
    db_stress = client[stress_db_name]
    del_users = db_stress.users.delete_many({"_id": {"$in": uids}, "performance_pool_id": pool_id})
    remaining_users_stress = db_stress.users.count_documents({})
    print(f"{stress_db_name}: izbrisanih {del_users.deleted_count} sintetičnih profilov.")
    print(f"{stress_db_name}: preostalih profilov: {remaining_users_stress}")

    client.close()
    print("Čiščenje uspešno zaključeno.")

if __name__ == '__main__':
    main()
