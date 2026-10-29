"""
Avtomatizirano izvajanje sestih funkcionalnih testnih scenarijev za spletno platformo NIDiKo
Standard: ISO/IEC/IEEE 29119-3:2021
Ekipa: Tilen Kek (TS-01 do TS-03), Mihajlo Dejanovic (TS-04 do TS-06)
Tehnologija: Selenium WebDriver (Google Chrome headless / high-res)
"""

import os
import sys
import time
import json
import argparse
import platform
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

# Zagotovitev pravilnega izpisa UTF-8 znakov na konzoli
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Konfiguracija poti in URL naslovov (izkljucno relativne poti za GitHub repo)
BASE_URL = "http://46.225.17.135"

# Robustno dolocanje korena repozitorija ne glede na lokacijo zagona
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Ker je skripta v backend/tests/functional/, je koren 3 ravni visje
CANDIDATE_ROOT_3 = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
CANDIDATE_ROOT_2 = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))

if os.path.exists(os.path.join(CANDIDATE_ROOT_3, "docs")):
    REPO_ROOT = CANDIDATE_ROOT_3
elif os.path.exists(os.path.join(CANDIDATE_ROOT_2, "docs")):
    REPO_ROOT = CANDIDATE_ROOT_2
else:
    REPO_ROOT = CANDIDATE_ROOT_3

REL_SCREENSHOT_DIR = os.path.join("docs", "assets", "funkcionalno-testiranje")
SCREENSHOT_DIR = os.path.join(REPO_ROOT, REL_SCREENSHOT_DIR)


class FunctionalTestRunner:
    def __init__(self, base_url=BASE_URL, output_dir=None):
        global BASE_URL, SCREENSHOT_DIR
        BASE_URL = base_url.rstrip('/')
        self.started_at = datetime.now().astimezone().isoformat()
        self.run_id = datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')
        SCREENSHOT_DIR = str(Path(output_dir) if output_dir else
                             Path(REPO_ROOT) / 'test-results' / self.run_id)
        Path(SCREENSHOT_DIR).mkdir(parents=True, exist_ok=False)
        self.results = []
        self.driver = None

    def setup_driver(self):
        """Inicializacija Chrome WebDriver z optimalnimi nastavitvami za zajem posnetkov in stabilnost."""
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(1)
        self.driver.set_page_load_timeout(30)
        self.wait = WebDriverWait(self.driver, 12)
        print("[SETUP] Chrome WebDriver uspesno inicializiran (1920x1080, headless nacin).")

    def teardown_driver(self):
        """Varno zapiranje brskalniske seje."""
        if self.driver:
            self.driver.quit()
            print("[TEARDOWN] Chrome WebDriver uspesno zakljucen.")

    def capture_screenshot(self, filename: str, description: str):
        """Zajem zaslonskega posnetka in shranjevanje z relativno potjo."""
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        if not self.driver.save_screenshot(filepath):
            raise RuntimeError(f"Zajem slike ni uspel: {filepath}")
        rel_path = filename
        print(f"  [DOKAZ / SCREENSHOT] Shranjen: {filename} ({description})")
        return rel_path

    def record_step(self, scenario_id: str, author: str, step_no: int, action: str, expected: str, actual: str, status: str, duration: float, screenshot: str = None):
        """Zapis posameznega izvedenega testnega koraka z relativno potjo."""
        if status == 'FAIL' and screenshot is None and self.driver:
            try:
                screenshot = self.capture_screenshot(
                    f"{scenario_id.lower()}_{step_no:02d}_fail.png", "Napaka koraka")
            except Exception:
                pass  # Napaka zajema ne sme prekriti izvirne napake testa.
        step_data = {
            "scenario_id": scenario_id.replace("TS-", "TS-NIDIKO-"),
            "timestamp": datetime.now().astimezone().isoformat(),
            "author": author,
            "step_no": step_no,
            "action": action,
            "expected": expected,
            "actual": actual,
            "status": status,
            "duration_sec": round(duration, 2),
            "screenshot": screenshot
        }
        self.results.append(step_data)
        status_symbol = "✓ PASS" if status == "PASS" else "✗ FAIL"
        print(f"  [KORAK {step_no}] {status_symbol} ({duration:.2f}s) | Akcija: {action} | Rezultat: {actual}")

    # =========================================================================
    # SKLOP 1: TILEN KEK (TS-01, TS-02, TS-03)
    # =========================================================================

    def run_scenario_1(self):
        print("\n" + "="*80)
        print("IZVAJANJE SCENARIJA 1 (Tilen Kek): TS-01 (Iskanje, filtriranje in navigacija)")
        print("="*80)
        scenario_id = "TS-01"
        author = "Tilen Kek"

        # Korak 1.1: Odpiranje domace strani
        t0 = time.time()
        try:
            self.driver.get(f"{BASE_URL}/")
            time.sleep(2)
            title = self.driver.title
            assert "NIDiKo" in title, f"Pricakovan NIDiKo v naslovu, dobljen: {title}"
            ss = self.capture_screenshot("ts01_01_domaca_stran.png", "Zacetna stran NIDiKo")
            self.record_step(scenario_id, author, 1, "Odpiranje zacetne strani aplikacije", "Prikaz domace strani z logotipom in navigacijo", f"Stran uspesno nalozena, naslov: '{title}'", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 1, "Odpiranje zacetne strani", "Prikaz domace strani", str(e), "FAIL", time.time() - t0)

        # Korak 1.2: Navigacija na stran za iskanje
        t0 = time.time()
        try:
            search_link = self.driver.find_element(By.CSS_SELECTOR, "a[href*='/search']")
            self.driver.execute_script("arguments[0].click();", search_link)
            time.sleep(2)
            assert "/search" in self.driver.current_url, f"Napacen URL: {self.driver.current_url}"
            ss = self.capture_screenshot("ts01_02_iskanje_zacetno.png", "Vstopna stran za napredno iskanje")
            self.record_step(scenario_id, author, 2, "Klik na povezavo 'Iskanje' v navigaciji", "Preusmeritev na /search z iskalnim poljem in filtri", f"Preusmeritev na {self.driver.current_url}, prisotni filtri in vnosno polje", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 2, "Prehod na stran iskanja", "Preusmeritev na /search", str(e), "FAIL", time.time() - t0)

        # Korak 1.3: Vnos poizvedbe v iskalno polje (umetna inteligenca)
        t0 = time.time()
        try:
            search_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='text']")
            search_input.clear()
            search_input.send_keys("umetna inteligenca")
            time.sleep(2)
            
            cards = self.driver.find_elements(By.TAG_NAME, "article")
            assert len(cards) > 0, "Ni bilo najdenih zadetkov za 'umetna inteligenca'"
            first_card_text = cards[0].text.replace('\n', ' | ')[:80]
            ss = self.capture_screenshot("ts01_03_iskanje_zadetki.png", f"Zadetki iskanja za 'umetna inteligenca' ({len(cards)} kartic)")
            self.record_step(scenario_id, author, 3, "Vnos iskalnega niza 'umetna inteligenca'", "Prikaz ustreznih ucnih kartic z zadetki", f"Najdenih {len(cards)} zadetkov, prvi: '{first_card_text}'", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 3, "Vnos iskalnega niza", "Prikaz kartic zadetkov", str(e), "FAIL", time.time() - t0)

        # Korak 1.4: Preizkus filtrov
        t0 = time.time()
        try:
            checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "aside input[type='checkbox']")
            assert len(checkboxes) == 3, "Manjkajo filtri tipov vsebine"
            assert not any(c.is_selected() for c in checkboxes), "Pricakovano zacetno stanje brez filtrov"
            checkboxes[0].click()
            self.wait.until(lambda d: checkboxes[0].is_selected() and
                len(d.find_elements(By.CSS_SELECTOR, 'article')) > 0 and
                all(c.find_element(By.CSS_SELECTOR, 'span.uppercase').text.casefold() == 'učna pot'
                    for c in d.find_elements(By.CSS_SELECTOR, 'article')))
            assert self.driver.find_elements(By.XPATH, "//article[.//h3[contains(., 'Iskanje informacij z umetno inteligenco')]]"), "Manjka pricakovana ucna pot"

            ss = self.capture_screenshot("ts01_04_filtri_podrocja.png", "Prikaz filtrov za tipe vsebin")
            self.record_step(scenario_id, author, 4, "Preverjanje filtrov po tipih vsebin (ucne poti, moduli, enote)", "Filtri so interaktivni in omogocajo ozenje zadetkov", "Izbran filter Ucne poti; vsi prikazani zadetki imajo tip Ucna pot", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 4, "Filtriranje vsebin", "Uveljavitev filtrov", str(e), "FAIL", time.time() - t0)

        # Korak 1.5: Prehod na podrobnosti ucne poti
        t0 = time.time()
        try:
            cards = self.driver.find_elements(By.TAG_NAME, "article")
            target_card = self.driver.find_element(By.XPATH,
                "//article[.//h3[contains(., 'Iskanje informacij z umetno inteligenco')]]")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_card)
            time.sleep(1)
            target_card.click()
            time.sleep(2)
            
            current_url = self.driver.current_url
            assert urlparse(current_url).path == "/learning-paths/up_001", f"Pricakovana navigacija na vsebino, URL: {current_url}"
            h1_elements = [h.text for h in self.driver.find_elements(By.TAG_NAME, "h1") if h.text.strip()]
            main_title = h1_elements[0] if h1_elements else "Brez naslova"
            ss = self.capture_screenshot("ts01_05_podrobnosti_ucne_poti.png", f"Stran podrobnosti ucne vsebine ({main_title})")
            self.record_step(scenario_id, author, 5, "Klik na kartico zadetka za ogled podrobnosti", "Odpiranje strani podrobnosti z zemljevidom poti in opisi", f"Uspesna navigacija na {current_url}, naslov: '{main_title}'", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 5, "Klik na kartico podrobnosti", "Navigacija na stran podrobnosti", str(e), "FAIL", time.time() - t0)

    def run_scenario_2(self):
        print("\n" + "="*80)
        print("IZVAJANJE SCENARIJA 2 (Tilen Kek): TS-02 (Diagnostika in priporocilo ucenja)")
        print("="*80)
        scenario_id = "TS-02"
        author = "Tilen Kek"

        # Korak 2.1: Zacetek vprasalnika
        t0 = time.time()
        try:
            self.driver.get(f"{BASE_URL}/learning-paths/up_001")
            time.sleep(2)
            q_btn = [b for b in self.driver.find_elements(By.TAG_NAME, "button") if "vprašalnik" in b.text.lower()][0]
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", q_btn)
            time.sleep(1)
            self.driver.execute_script("arguments[0].click();", q_btn)
            time.sleep(2)
            
            assert "/assessment" in self.driver.current_url, f"Napacen URL: {self.driver.current_url}"
            q1_heading = [h.text for h in self.driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3") if h.text.strip()][0]
            ss = self.capture_screenshot("ts02_01_vprasalnik_vstop.png", "Vstop v diagnosticni vprasalnik (Vprasanje 1)")
            self.record_step(scenario_id, author, 1, "Sprozitev gumba 'Odpri vprasalnik' na ucni poti", "Preusmeritev na /assessment in prikaz prvega diagnosticnega vprasanja", f"URL: {self.driver.current_url}, vprasanje: '{q1_heading}'", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 1, "Sprozitev vprasalnika", "Preusmeritev na /assessment", str(e), "FAIL", time.time() - t0)

        # Korak 2.2: Odgovor Da
        t0 = time.time()
        try:
            da_btn = [b for b in self.driver.find_elements(By.TAG_NAME, "button") if b.text.strip().lower() == "da"][0]
            da_btn.click()
            time.sleep(1)
            next_btn = [b for b in self.driver.find_elements(By.TAG_NAME, "button") if "naslednj" in b.text.lower()]
            assert len(next_btn) > 0, "Gumb 'Naslednjo' ni viden"
            ss = self.capture_screenshot("ts02_02_vprasalnik_odgovor_da.png", "Izbran odgovor DA na Vprasanje 1")
            self.record_step(scenario_id, author, 2, "Izbira odgovora 'Da' na vprasanje o konceptu UI", "Oznacitev izbire in aktivacija gumba 'Naslednjo →'", f"Odgovor zabelezen, omogocen prehod '{next_btn[0].text}'", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 2, "Izbira odgovora Da", "Aktivacija gumba Naslednjo", str(e), "FAIL", time.time() - t0)

        # Korak 2.3: Prehod na 2. vprasanje
        t0 = time.time()
        try:
            next_btn = [b for b in self.driver.find_elements(By.TAG_NAME, "button") if "naslednj" in b.text.lower()][0]
            next_btn.click()
            time.sleep(2)
            q2_heading = [h.text for h in self.driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3") if h.text.strip()][0]
            ss = self.capture_screenshot("ts02_03_vprasalnik_vprasanje_2.png", "Prehod na Vprasanje 2")
            self.record_step(scenario_id, author, 3, "Klik na gumb 'Naslednjo →'", "Prikaz drugega zaporednega vprasanja", f"Uspesen prehod, novo vprasanje: '{q2_heading}'", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 3, "Prehod na 2. vprasanje", "Prikaz 2. vprasanja", str(e), "FAIL", time.time() - t0)

        # Korak 2.4: Odgovor Ne (sprozi zakljucek)
        t0 = time.time()
        try:
            ne_btn = [b for b in self.driver.find_elements(By.TAG_NAME, "button") if b.text.strip().lower() == "ne"][0]
            ne_btn.click()
            time.sleep(1)
            finish_btn = [b for b in self.driver.find_elements(By.TAG_NAME, "button") if "zaključi" in b.text.lower()]
            assert len(finish_btn) > 0, "Gumb 'Zakljuci' se ni pojavil"
            ss = self.capture_screenshot("ts02_04_vprasalnik_odgovor_ne.png", "Izbran odgovor NE in gumb Zakljuci")
            self.record_step(scenario_id, author, 4, "Izbira odgovora 'Ne' na vprasanje o primerih UI", "Prepoznava neznanja predpogoja, prilagoditev toka na 'Zakljuci →'", f"Prikazan gumb '{finish_btn[0].text}' za oddajo samoocene", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 4, "Odgovor Ne na vprasalniku", "Prikaz gumba Zakljuci", str(e), "FAIL", time.time() - t0)

        # Korak 2.5: Oddaja vprasalnika
        t0 = time.time()
        try:
            finish_btn = [b for b in self.driver.find_elements(By.TAG_NAME, "button") if "zaključi" in b.text.lower()][0]
            finish_btn.click()
            time.sleep(3)
            current_url = self.driver.current_url
            assert "/learning-paths/up_001" in current_url, f"Pricakovana preusmeritev na ucno pot, URL: {current_url}"
            ss = self.capture_screenshot("ts02_05_rezultat_samoocene.png", "Prikaz priporocila ucenja po oddaji vprasalnika")
            headings = [h.text for h in self.driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3") if h.text.strip()]
            has_assessment = any("samoocen" in h.lower() for h in headings)
            assert has_assessment, "Manjka sekcija Samoocena po oddaji"
            self.record_step(scenario_id, author, 5, "Klik na 'Zakljuci →' in klic zalednega servisa /api/assessment/evaluate", "Zaledni izracun kompetenc in prikaz priporocila ucenja na strani podrobnosti", f"Preusmeritev na {current_url}, prisotna sekcija Samoocena: {has_assessment}", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 5, "Oddaja vprasalnika", "Prikaz priporocila ucenja", str(e), "FAIL", time.time() - t0)

    def run_scenario_3(self):
        print("\n" + "="*80)
        print("IZVAJANJE SCENARIJA 3 (Tilen Kek): TS-03 (Avtentikacija, zascita in AI svetovalec)")
        print("="*80)
        scenario_id = "TS-03"
        author = "Tilen Kek"

        # Korak 3.1: Poskus zascitene akcije (modal)
        t0 = time.time()
        try:
            self.driver.get(f"{BASE_URL}/learning-paths/up_001")
            time.sleep(2)
            save_button = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[aria-label='Shrani za pozneje']")))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_button)
            save_button.click()
            self.wait.until(EC.visibility_of_element_located((By.XPATH,
                "//*[contains(text(), 'Za to dejanje se moraš prijaviti') or contains(text(), 'Prijava je potrebna')]")))
            ss = self.capture_screenshot("ts03_01_auth_dialog.png", "Modalno okno za zahtevo po prijavi")
            self.record_step(scenario_id, author, 1, "Poskus shranjevanja vsebine s strani neprijavljenega uporabnika", "Prikaz varnostnega modalnega okna AuthRequiredDialog z obvestilom", "Modal 'Za to dejanje se moraš prijaviti' se uspesno prikaze", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 1, "Nadzor dostopa do profilnih funkcij", "Prikaz AuthRequiredDialog", str(e), "FAIL", time.time() - t0)

        # Korak 3.2: Klik na 'Prijavi se'
        t0 = time.time()
        try:
            login_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Prijavi se')]")
            login_btn.click()
            time.sleep(2)
            assert "/login" in self.driver.current_url, f"Pricakovana preusmeritev na /login, dobljeno: {self.driver.current_url}"
            ss = self.capture_screenshot("ts03_02_login_obrazec.png", "Vstop na prijavni obrazec")
            self.record_step(scenario_id, author, 2, "Klik na gumb 'Prijavi se' znotraj varnostnega modala", "Preusmeritev na stran /login s prijavnim obrazcem", f"Uspesna navigacija na {self.driver.current_url}, prisoten prijavni obrazec", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 2, "Preusmeritev na prijavo", "Navigacija na /login", str(e), "FAIL", time.time() - t0)

        # Korak 3.3: Validacija prijavnega obrazca
        t0 = time.time()
        try:
            email_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='email'], input[type='email']")
            pass_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='password'], input[type='password']")
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            
            email_input.clear()
            email_input.send_keys("neveljaven_uporabnik@test.si")
            pass_input.clear()
            pass_input.send_keys("NepravilnoGeslo123!")
            time.sleep(1)
            submit_btn.click()
            # Zahtevamo dejansko obvestilo o napacnih podatkih, ne splosne omrezne napake.
            error_alert = self.wait.until(EC.visibility_of_element_located((By.XPATH,
                "//*[normalize-space(text())='Napačen e-poštni naslov ali geslo.' or normalize-space(text())='Prišlo je do napake. Poskusite znova.']")))
            error_text = error_alert.text
            assert error_text == 'Napačen e-poštni naslov ali geslo.', f'Pricakovana zavrnitev podatkov, prikazano: {error_text}'
            assert urlparse(self.driver.current_url).path == '/login', "Prijava ni ostala zavrnjena"
            ss = self.capture_screenshot("ts03_03_login_napaka.png", "Prikaz napake ob neveljavnih prijavnih podatkih")
            self.record_step(scenario_id, author, 3, "Vnos neveljavnih prijavnih podatkov in klik na 'Prijavi se'", "Sistem zavrne prijavo in prikaze uporabniku prijazno opozorilo", f"Prijava zavrnjena, zaznano opozorilo: '{error_text}'", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 3, "Validacija prijave", "Zavrnitev neveljavne prijave", str(e), "FAIL", time.time() - t0)

        # Korak 3.4: Preizkus AI svetovalca
        t0 = time.time()
        try:
            self.driver.get(f"{BASE_URL}/learning-paths/up_001")
            time.sleep(2)
            ai_open_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Odpri chat pomočnika']")
            if not ai_open_buttons:
                ai_open_buttons = [b for b in self.driver.find_elements(By.TAG_NAME, "button") if "pomočnik" in b.text.lower() or "ai" in b.text.lower()]
            assert len(ai_open_buttons) > 0, "Gumb za odprtje AI asistenta ni bil najden!"
            self.driver.execute_script("arguments[0].click();", ai_open_buttons[0])
            time.sleep(2)
            
            chat_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[placeholder*='Vprašaj'], textarea")
            assert len(chat_inputs) > 0, "Vnosno polje za klepet z AI asistentom ni bilo najdeno!"
            active_input = chat_inputs[0]
            active_input.send_keys('Kaj obsega ta učna pot?')
            assert active_input.get_attribute('value') == 'Kaj obsega ta učna pot?'
            send_button = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Pošlji vprašanje']")
            assert send_button.is_enabled(), "React ni sprejel vnesenega vprasanja"
            time.sleep(1)
            
            ss = self.capture_screenshot("ts03_04_ai_pomocnik_odprt.png", "Odprt interaktivni panel AI pomocnika z vprasanjem")
            self.record_step(scenario_id, author, 4, "Aktivacija stranskega AI asistenta in vnos poizvedbe", "Odprtje CollapsibleChatPanel in uspesen vnos vprasanja v polje", f"Panel uspesno aktiviran, vpisana poizvedba v polje '{active_input.get_attribute('placeholder')}'", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 4, "Aktivacija AI pomocnika", "Odprtje stranskega klepeta", str(e), "FAIL", time.time() - t0)

    # =========================================================================
    # SKLOP 2: MIHAJLO DEJANOVIĆ (TS-04, TS-05, TS-06)
    # =========================================================================

    def run_scenario_4(self):
        print("\n" + "="*80)
        print("IZVAJANJE SCENARIJA 4 (Mihajlo Dejanović): TS-04 (Hierarhija modulov in ucne enote)")
        print("="*80)
        scenario_id = "TS-04"
        author = "Mihajlo Dejanović"

        # Korak 4.1: Vstop na stran modula mod_014
        t0 = time.time()
        try:
            self.driver.get(f"{BASE_URL}/modules/mod_014")
            time.sleep(2)
            assert "/modules/mod_014" in self.driver.current_url, f"Napacen URL: {self.driver.current_url}"
            h1_text = [h.text for h in self.driver.find_elements(By.TAG_NAME, "h1") if h.text.strip()][0]
            ss = self.capture_screenshot("ts04_01_modul_podrobnosti.png", "Prikaz podrobnosti modula mod_014")
            self.record_step(scenario_id, author, 1, "Navigacija na stran podrobnosti modula mod_014", "Prikaz naslova modula, opisa in seznama ucnih enot", f"Modul nalozen, naslov: '{h1_text}'", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 1, "Navigacija na modul mod_014", "Prikaz podrobnosti modula", str(e), "FAIL", time.time() - t0)

        # Korak 4.2: Pregled seznama ucnih enot znotraj modula
        t0 = time.time()
        try:
            # Pomaknemo se do vizualizatorja ucnih enot
            self.driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(1)
            unit_nodes = self.driver.find_elements(By.CSS_SELECTOR, "button[data-lu-node]")
            assert unit_nodes, "Manjkajo vozlisca ucnih enot"
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", unit_nodes[0])
            self.wait.until(EC.visibility_of(unit_nodes[0]))
            ss = self.capture_screenshot("ts04_02_modul_ucne_enote.png", "Seznam in vizualizacija ucnih enot znotraj modula mod_014")
            self.record_step(scenario_id, author, 2, "Pregled seznama in vizualizacije ucnih enot modula", "Prikaz vizualizacije ucnih enot (LearningUnitVisualizer) z vozlisci zaporedja", f"Zaznana vozlisca ucnih enot za modul 'Analiza in obdelava podatkov' ({len(unit_nodes)} elementov)", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 2, "Pregled ucnih enot", "Prikaz ucnih enot v modulu", str(e), "FAIL", time.time() - t0)

        # Korak 4.3: Prehod na ucno enoto ue_036
        t0 = time.time()
        try:
            node = self.driver.find_element(By.CSS_SELECTOR, "button[data-lu-node='0']")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", node)
            self.wait.until(EC.element_to_be_clickable(node))
            node.click()
            self.wait.until(EC.url_contains('/learning-units/ue_036'))
            time.sleep(2)
            assert "/learning-units/ue_036" in self.driver.current_url, f"Napacen URL: {self.driver.current_url}"
            u_title = [h.text for h in self.driver.find_elements(By.TAG_NAME, "h1") if h.text.strip()][0]
            ss = self.capture_screenshot("ts04_03_ucna_enota_podrobnosti.png", "Prikaz podrobnosti ucne enote ue_036")
            self.record_step(scenario_id, author, 3, "Navigacija na podrobnosti posamezne ucne enote ue_036", "Prikaz vsebine enote, kompetenc, trajanja in moznosti samoocene", f"Ucna enota nalozena, naslov: '{u_title}'", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 3, "Navigacija na ucno enoto", "Prikaz ucne enote ue_036", str(e), "FAIL", time.time() - t0)

    def run_scenario_5(self):
        print("\n" + "="*80)
        print("IZVAJANJE SCENARIJA 5 (Mihajlo Dejanović): TS-05 (Samoocenjevanje na ravni modula)")
        print("="*80)
        scenario_id = "TS-05"
        author = "Mihajlo Dejanović"

        # Korak 5.1: Zagon vprasalnika za modul mod_014
        t0 = time.time()
        try:
            self.driver.get(f"{BASE_URL}/assessment?target_type=module&target_id=mod_014")
            time.sleep(2.5)
            assert "/assessment" in self.driver.current_url, f"Napacen URL: {self.driver.current_url}"
            q_heading = [h.text for h in self.driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3") if h.text.strip()][0]
            ss = self.capture_screenshot("ts05_01_modul_vprasalnik_zacetek.png", "Zacetek vprasalnika za modul mod_014")
            self.record_step(scenario_id, author, 1, "Odpiranje vprasalnika za modul mod_014", "Prikaz vstopnega vprasanja za modul 'Analiza in obdelava podatkov'", f"Nalozeno vprasanje modula: '{q_heading}'", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 1, "Odpiranje vprasalnika modula", "Prikaz vprasanja", str(e), "FAIL", time.time() - t0)

        # Korak 5.2: Odgovor Da na prvo vprasanje modula
        t0 = time.time()
        try:
            da_btn = [b for b in self.driver.find_elements(By.TAG_NAME, "button") if b.text.strip().lower() == "da"][0]
            da_btn.click()
            time.sleep(1)
            next_btn = [b for b in self.driver.find_elements(By.TAG_NAME, "button") if any(w in b.text.lower() for w in ["naslednj", "zaključi"])][0]
            ss = self.capture_screenshot("ts05_02_modul_vprasalnik_da.png", "Izbran odgovor Da na vprasanju modula")
            self.record_step(scenario_id, author, 2, "Izbira odgovora 'Da' na ravni modula", "Odgovor se zabelezi in aktivira navigacijski gumb", f"Odgovor zabelezen, aktiven gumb '{next_btn.text}'", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 2, "Izbira odgovora Da", "Aktivacija gumba", str(e), "FAIL", time.time() - t0)

        # Korak 5.3: Zakljucek ali oddaja ocenjevanja modula
        t0 = time.time()
        try:
            btn = [b for b in self.driver.find_elements(By.TAG_NAME, "button") if any(w in b.text.lower() for w in ["naslednj", "zaključi"])][0]
            btn.click()
            time.sleep(2.5)
            
            # Ce je se naslednje vprasanje, izberemo Ne za hiter zakljucek
            ne_btns = [b for b in self.driver.find_elements(By.TAG_NAME, "button") if b.text.strip().lower() == "ne"]
            if ne_btns and "/assessment" in self.driver.current_url:
                ne_btns[0].click()
                time.sleep(1)
                finish_btn = [b for b in self.driver.find_elements(By.TAG_NAME, "button") if "zaključi" in b.text.lower()]
                if finish_btn:
                    finish_btn[0].click()
                    time.sleep(3)
            
            self.wait.until(lambda d: urlparse(d.current_url).path == '/modules/mod_014')
            self.wait.until(EC.visibility_of_element_located((By.XPATH,
                "//*[self::h1 or self::h2 or self::h3][contains(., 'Samoocena')]")))
            current_url = self.driver.current_url
            ss = self.capture_screenshot("ts05_03_modul_ocena_rezultat.png", "Prikaz stanja po oddaji ocenjevanja modula")
            self.record_step(scenario_id, author, 3, "Zakljucek vprasalnika modula in vrnitev na podrobnosti", "Uspesna obdelava odgovorov prek zaledja in preusmeritev na modul", f"Koncni URL: {current_url}", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 3, "Oddaja ocenjevanja modula", "Zakljucek vprasalnika", str(e), "FAIL", time.time() - t0)

    def run_scenario_6(self):
        print("\n" + "="*80)
        print("IZVAJANJE SCENARIJA 6 (Mihajlo Dejanović): TS-06 (Predstavitev O nas in odzivni dizajn)")
        print("="*80)
        scenario_id = "TS-06"
        author = "Mihajlo Dejanović"

        # Korak 6.1: Vstop na stran 'O nas'
        t0 = time.time()
        try:
            self.driver.get(f"{BASE_URL}/about")
            time.sleep(2)
            assert "/about" in self.driver.current_url, f"Napacen URL: {self.driver.current_url}"
            h1_text = [h.text for h in self.driver.find_elements(By.TAG_NAME, "h1") if h.text.strip()][0]
            ss = self.capture_screenshot("ts06_01_o_nas_namizje.png", "Stran 'O nas' v namiznem pogledu (1920x1080)")
            self.record_step(scenario_id, author, 1, "Navigacija na informativno stran 'O nas'", "Prikaz vizije projekta, namena ter informacij o digitalnih kompetencah", f"Stran 'O nas' nalozena, naslov: '{h1_text}'", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 1, "Navigacija na O nas", "Prikaz strani O nas", str(e), "FAIL", time.time() - t0)

        # Korak 6.2: Preveritev navigacijskih povezav
        t0 = time.time()
        try:
            for path in ('/', '/search', '/about', '/register'):
                def click_link(driver):
                    try:
                        link = driver.find_element(By.CSS_SELECTOR, f"header a[href='{path}']")
                        if not link.is_displayed() or not link.is_enabled():
                            return False
                        link.click()
                        return True
                    except StaleElementReferenceException:
                        return False
                self.wait.until(click_link)
                self.wait.until(lambda d: urlparse(d.current_url).path == path)
                self.wait.until(lambda d: any(h.is_displayed() and h.text.strip()
                    for h in d.find_elements(By.TAG_NAME, 'h1')))
            self.driver.get(f"{BASE_URL}/about")
            self.wait.until(EC.visibility_of_element_located((By.TAG_NAME, 'h1')))
            nav_links = self.driver.find_elements(By.CSS_SELECTOR, 'header a')
            ss = self.capture_screenshot("ts06_02_navigacija_glava.png", "Glavna navigacijska vrstica na strani 'O nas'")
            self.record_step(scenario_id, author, 2, "Preverjanje delovanja zgornje navigacije", "Prisotne povezave Domov, Iskanje, O nas in Prijava/Registracija", f"Zaznanih {len(nav_links)} povezav v navigaciji", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.record_step(scenario_id, author, 2, "Preverjanje navigacije", "Prikaz povezav", str(e), "FAIL", time.time() - t0)

        # Korak 6.3: Preizkus odzivnega dizajna (mobilni pogled 375x812)
        t0 = time.time()
        try:
            self.driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
                'width': 375, 'height': 812, 'deviceScaleFactor': 1, 'mobile': False})
            time.sleep(1.5)
            dimensions = self.driver.execute_script("""
                return {width: window.innerWidth, height: window.innerHeight,
                        contentWidth: document.documentElement.scrollWidth};
            """)
            assert dimensions['width'] == 375 and dimensions['height'] == 812, f'Napacen viewport: {dimensions}'
            assert dimensions['contentWidth'] <= dimensions['width'] + 1, f"Vodoravni preliv: {dimensions}"
            assert any(h.is_displayed() and h.text.strip() for h in self.driver.find_elements(By.TAG_NAME, 'h1'))
            ss = self.capture_screenshot("ts06_03_o_nas_mobilni_pogled.png", "Stran 'O nas' v mobilnem pogledu (375x812)")
            
            # Ponastavimo nazaj na polno locljivost za nadaljnje delo
            self.driver.execute_cdp_cmd('Emulation.clearDeviceMetricsOverride', {})
            self.driver.set_window_size(1920, 1080)
            time.sleep(1)
            self.record_step(scenario_id, author, 3, "Preizkus odzivnega prikaza na mobilni locljivosti (375x812)", "Uporabniski vmesnik se prilagodi manjsi sirini zaslona brez prekrivanja", f"Izmerjen viewport: {dimensions}; brez vodoravnega preliva; vizualni pregled prekrivanja je locen", "PASS", time.time() - t0, ss)
        except Exception as e:
            self.driver.execute_cdp_cmd('Emulation.clearDeviceMetricsOverride', {})
            self.driver.set_window_size(1920, 1080)
            self.record_step(scenario_id, author, 3, "Preizkus mobilnega pogleda", "Prilagoditev postavitve", str(e), "FAIL", time.time() - t0)

    def generate_json_summary(self):
        """Izvoz rezultatov testiranja v JSON format z izkljucno relativnimi potmi."""
        summary = {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "timestamp": datetime.now().astimezone().isoformat(),
            "python": platform.python_version(),
            "browser_version": self.driver.capabilities.get('browserVersion') if self.driver else None,
            "execution_error": getattr(self, 'execution_error', None),
            "target_environment": BASE_URL,
            "browser": "Google Chrome (Headless 1920x1080)",
            "team_members": ["Tilen Kek", "Mihajlo Dejanović"],
            "total_steps": len(self.results),
            "passed_steps": len([r for r in self.results if r["status"] == "PASS"]),
            "failed_steps": len([r for r in self.results if r["status"] == "FAIL"]),
            "scenario_statuses": {
                f'TS-NIDIKO-{n:02d}': ('PASS' if len(steps) == count and
                    all(r['status'] == 'PASS' for r in steps) else 'FAIL')
                for n, count in enumerate((5, 5, 4, 3, 3, 3), 1)
                for steps in [[r for r in self.results if r['scenario_id'] == f'TS-NIDIKO-{n:02d}']]
            },
            "steps": self.results
        }
        json_path = os.path.join(SCREENSHOT_DIR, "test_execution_summary.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        rel_summary_path = json_path
        print(f"\n[SUMMARY] Povzetek testiranja shranjen v: {rel_summary_path}")
        return summary

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default=BASE_URL)
    parser.add_argument('--output-dir', help='Nova mapa za dokaze posameznega zagona')
    args = parser.parse_args()
    if not __debug__:
        parser.error('Testov ne zaganjaj z -O: preverjanja assert morajo biti vkljucena.')
    runner = FunctionalTestRunner(args.base_url, args.output_dir)
    try:
        runner.setup_driver()
        for n in range(1, 7):
            # Vsak scenarij dobi neodvisno anonimno sejo.
            runner.driver.get(BASE_URL)
            runner.driver.delete_all_cookies()
            runner.driver.execute_script('window.localStorage.clear(); window.sessionStorage.clear();')
            getattr(runner, f'run_scenario_{n}')()
    except Exception as exc:
        runner.execution_error = f'{type(exc).__name__}: {exc}'
        print(f'[ERROR] {runner.execution_error}')
    finally:
        summary = runner.generate_json_summary()
        runner.teardown_driver()
    print(f"Skupaj: {summary['total_steps']}; PASS: {summary['passed_steps']}; FAIL: {summary['failed_steps']}")
    return 0 if (not summary['execution_error'] and
                 all(status == 'PASS' for status in summary['scenario_statuses'].values())) else 1


if __name__ == '__main__':
    sys.exit(main())
