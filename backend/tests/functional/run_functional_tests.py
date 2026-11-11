"""Selenium: six NIDiKo functional scenarios, JSON, JUnit and screenshots.

Exit 0 requires every expected step to pass. Use without Python's -O flag.
"""
import argparse
import json
import os
import platform
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import selenium
from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException, StaleElementReferenceException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = 'http://46.225.17.135'
REPO_ROOT = Path(__file__).resolve().parents[3]
STEP_COUNTS = {1: 5, 2: 5, 3: 4, 4: 3, 5: 3, 6: 3}
QUESTION = (By.CSS_SELECTOR, '.assessment-intro h1')
NEXT = (By.CSS_SELECTOR, '.assessment-actions .primary-button')


class FunctionalTestRunner:
    def __init__(self, base_url=BASE_URL, output_dir=None, scenarios=None):
        self.base_url = base_url.rstrip('/')
        self.started_at = datetime.now().astimezone().isoformat()
        self.run_id = datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')
        self.output_dir = Path(output_dir) if output_dir else REPO_ROOT / 'test-results' / self.run_id
        self.output_dir.mkdir(parents=True, exist_ok=False)
        self.scenarios = sorted(set(scenarios if scenarios is not None else STEP_COUNTS))
        self.results = []
        self.driver = None
        self.execution_error = None

    def setup_driver(self):
        options = Options()
        for argument in ('--headless=new', '--window-size=1920,1080',
                         '--no-sandbox', '--disable-dev-shm-usage'):
            options.add_argument(argument)
        if os.environ.get('CHROME_BINARY'):
            options.binary_location = os.environ['CHROME_BINARY']
        options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
        service = Service(executable_path=os.environ.get('CHROMEDRIVER'))
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(30)
        self.driver.implicitly_wait(0)
        self.wait = WebDriverWait(self.driver, 20, poll_frequency=0.2,
                                  ignored_exceptions=(StaleElementReferenceException,))

    def teardown_driver(self):
        if self.driver:
            self.driver.quit()

    def capture_screenshot(self, filename, description=''):
        if not self.driver.save_screenshot(str(self.output_dir / filename)):
            raise RuntimeError(f'Screenshot failed: {filename}')
        return filename

    def record_step(self, scenario_id, author, step_no, action, expected, actual,
                    status, duration, screenshot=None):
        evidence_error = None
        if status == 'FAIL' and self.driver:
            try:
                prefix = f'{scenario_id.lower()}_{step_no:02d}_fail'
                screenshot = screenshot or self.capture_screenshot(f'{prefix}.png')
                (self.output_dir / f'{prefix}.html').write_text(self.driver.page_source, encoding='utf-8')
                (self.output_dir / f'{prefix}_browser.json').write_text(
                    json.dumps(self.driver.get_log('browser'), ensure_ascii=False, indent=2), encoding='utf-8')
            except Exception as exc:
                evidence_error = f'{type(exc).__name__}: {exc}'
        self.results.append({
            'scenario_id': scenario_id.replace('TS-', 'TS-NIDIKO-'),
            'timestamp': datetime.now().astimezone().isoformat(), 'author': author,
            'step_no': step_no, 'action': action, 'expected': expected, 'actual': actual,
            'status': status, 'duration_sec': round(duration, 2), 'screenshot': screenshot,
            'evidence_error': evidence_error,
        })
        print(f'[{scenario_id}.{step_no}] {status}: {actual}', flush=True)

    def step(self, scenario, number, action, expected, check, screenshot_name=None):
        start = time.monotonic()
        screenshot = None
        try:
            actual = check() or expected
            screenshot = screenshot_name or self.capture_screenshot(f'ts{scenario:02d}_{number:02d}.png')
            status = 'PASS'
        except Exception as exc:
            actual = f'{type(exc).__name__}: {exc}'
            status = 'FAIL'
        self.record_step(f'TS-{scenario:02d}',
                         'Tilen Kek' if scenario <= 3 else 'Mihajlo Dejanović',
                         number, action, expected, actual, status,
                         time.monotonic() - start, screenshot)

    def visible(self, locator):
        return self.wait.until(EC.visibility_of_element_located(locator))

    def click(self, locator):
        def attempt(driver):
            try:
                element = driver.find_element(*locator)
                if not element.is_displayed() or not element.is_enabled():
                    return False
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                element.click()
                return True
            except (StaleElementReferenceException, ElementClickInterceptedException):
                return False
        self.wait.until(attempt, f'Element is not clickable: {locator}')

    def open(self, path):
        self.driver.get(f'{self.base_url}{path}')
        self.path(path.split('?')[0])
        return self.heading()

    def path(self, expected):
        self.wait.until(lambda d: urlparse(d.current_url).path == expected,
                        f'Expected URL path {expected}')

    def heading(self, expected=None):
        return self.wait.until(lambda d: next((h.text for h in d.find_elements(By.TAG_NAME, 'h1')
                                               if h.is_displayed() and h.text.strip() and
                                               (expected is None or h.text == expected)), False))

    def answer(self, label):
        self.click((By.XPATH, f"//button[contains(@class, 'answer-card')][span[normalize-space()='{label}']]"))
        self.wait.until(lambda d: label in d.find_element(By.CSS_SELECTOR, '.answer-card--selected').text)
        button = self.wait.until(EC.element_to_be_clickable(NEXT))
        return button.text

    def assessment_result(self, path):
        self.path(path)
        self.visible((By.XPATH, "//h2[normalize-space()='Samoocena']"))
        # The Samoocena heading also exists before submission. Require the stored API result.
        self.wait.until(lambda d: d.execute_script(
            "return Object.keys(sessionStorage).some(k => k.startsWith('assessment_result') && sessionStorage.getItem(k));"))
        return f'Result stored; URL: {self.driver.current_url}'

    def reset_session(self):
        # A new tab guarantees fresh sessionStorage; origin clearing covers localStorage.
        previous = self.driver.current_window_handle
        self.driver.switch_to.new_window('tab')
        fresh = self.driver.current_window_handle
        self.driver.switch_to.window(previous)
        self.driver.close()
        self.driver.switch_to.window(fresh)
        self.driver.execute_cdp_cmd('Storage.clearDataForOrigin', {
            'origin': self.base_url, 'storageTypes': 'all'})
        self.driver.delete_all_cookies()
        self.driver.execute_cdp_cmd('Emulation.clearDeviceMetricsOverride', {})
        self.driver.set_window_size(1920, 1080)

    def run_scenario_1(self):
        def home():
            self.open('/')
            self.wait.until(EC.title_contains('NIDiKo'), 'Expected NIDiKo in document title')
            return self.driver.title
        def search():
            self.click((By.CSS_SELECTOR, "header a[href='/search']"))
            self.path('/search')
            self.visible((By.CSS_SELECTOR, "input[type='text']"))
        def query():
            field = self.visible((By.CSS_SELECTOR, "input[type='text']"))
            field.clear()
            field.send_keys('nidiko-functional-no-match-7f4a2')
            self.visible((By.XPATH, "//h3[normalize-space()='Ni zadetkov']"))
            self.wait.until(lambda d: not d.find_elements(By.TAG_NAME, 'article'))
            field.clear()
            field.send_keys('umetna inteligenca')
            self.visible((By.XPATH, "//article[.//h3[contains(., 'Iskanje informacij z umetno inteligenco')]]"))
            return f"{len(self.driver.find_elements(By.TAG_NAME, 'article'))} results"
        def filter_paths():
            boxes = self.driver.find_elements(By.CSS_SELECTOR, "aside input[type='checkbox']")
            assert len(boxes) == 3 and not any(b.is_selected() for b in boxes), 'Unexpected initial filters'
            boxes[0].click()
            def filtered(driver):
                try:
                    cards = driver.find_elements(By.TAG_NAME, 'article')
                    return boxes[0].is_selected() and cards and all(
                        c.find_element(By.CSS_SELECTOR, 'span.uppercase').text.casefold() == 'učna pot'
                        for c in cards)
                except StaleElementReferenceException:
                    return False
            self.wait.until(filtered)
            self.visible((By.XPATH, "//article[.//h3[contains(., 'Iskanje informacij z umetno inteligenco')]]"))
        def detail():
            self.click((By.XPATH, "//article[.//h3[contains(., 'Iskanje informacij z umetno inteligenco')]]"))
            self.path('/learning-paths/up_001')
            self.heading('Iskanje informacij z umetno inteligenco')
        self.step(1, 1, 'Odpri /', 'Naslov zavihka vsebuje NIDiKo', home)
        self.step(1, 2, 'Klikni Iskanje', 'Iskalnik na /search je viden', search)
        self.step(1, 3, 'Preveri prazno iskanje in vpiši umetna inteligenca', 'Prazen rezultat za neobstoječ niz, nato ciljna učna pot', query)
        self.step(1, 4, 'Izberi Učne poti', 'Izbran filter; samo učne poti, vključno z up_001', filter_paths)
        self.step(1, 5, 'Klikni ciljno kartico', 'Pot /learning-paths/up_001 in pravilen naslov', detail)

    def run_scenario_2(self):
        questions = {}
        def start():
            self.open('/learning-paths/up_001')
            self.click((By.XPATH, "//button[contains(., 'Odpri vprašalnik')]"))
            self.path('/assessment')
            questions['first'] = self.visible(QUESTION).text
            return questions['first']
        def yes():
            text = self.answer('Da')
            assert 'Naslednjo' in text, f'Unexpected action: {text}'
            return text
        def next_question():
            self.click(NEXT)
            self.wait.until(lambda d: d.find_element(*QUESTION).text.strip() and
                            d.find_element(*QUESTION).text != questions.get('first'))
            return self.visible(QUESTION).text
        def no():
            text = self.answer('Ne')
            assert 'Zaključi' in text, f'Unexpected action: {text}'
            return text
        def submit():
            self.click(NEXT)
            return self.assessment_result('/learning-paths/up_001')
        self.step(2, 1, 'Odpri vprašalnik up_001', 'Prvo vprašanje je vidno', start)
        self.step(2, 2, 'Odgovori Da', 'Izbran Da in omogočen Naslednjo', yes)
        self.step(2, 3, 'Klikni Naslednjo', 'Besedilo vprašanja se spremeni', next_question)
        self.step(2, 4, 'Odgovori Ne', 'Izbran Ne in omogočen Zaključi', no)
        self.step(2, 5, 'Klikni Zaključi', 'Shranjena samoocena in vrnitev na up_001', submit)

    def run_scenario_3(self):
        def protected_action():
            self.open('/learning-paths/up_001')
            self.click((By.CSS_SELECTOR, "button[aria-label='Shrani za pozneje']"))
            self.visible((By.XPATH, "//*[contains(text(), 'Za to dejanje se moraš prijaviti')]"))
        def login_page():
            self.click((By.XPATH, "//button[contains(., 'Prijavi se')]"))
            self.path('/login')
            self.visible((By.ID, 'auth-email'))
        def invalid_login():
            email = self.visible((By.ID, 'auth-email'))
            password = self.visible((By.ID, 'auth-password'))
            email.clear()
            email.send_keys('neveljaven_uporabnik@test.si')
            password.clear()
            password.send_keys('NepravilnoGeslo123!')
            self.click((By.XPATH, "//form[.//input[@id='auth-password']]//button[@type='submit']"))
            error = self.visible((By.XPATH,
                "//*[normalize-space(text())='Napačen e-poštni naslov ali geslo.' or "
                "normalize-space(text())='Prišlo je do napake. Poskusite znova.']")).text
            assert error == 'Napačen e-poštni naslov ali geslo.', f'Unexpected auth error: {error}'
            self.path('/login')
            assert not self.driver.execute_script("""
                return [localStorage, sessionStorage].some(s => Object.keys(s).some(
                    k => /^sb-.*-auth-token$/.test(k) && s.getItem(k)));
            """), 'Rejected login created a session'
            return error
        def assistant():
            self.open('/learning-paths/up_001')
            self.click((By.CSS_SELECTOR, "button[aria-label='Odpri chat pomočnika']"))
            field = self.wait.until(lambda d: next((e for e in d.find_elements(
                By.CSS_SELECTOR, "input[placeholder*='Vprašaj'], textarea") if e.is_displayed()), False))
            field.send_keys('Kaj obsega ta učna pot?')
            assert field.get_attribute('value') == 'Kaj obsega ta učna pot?'
            self.wait.until(lambda d: any(b.is_displayed() and b.is_enabled() for b in d.find_elements(
                By.CSS_SELECTOR, "button[aria-label='Pošlji vprašanje']")))
        self.step(3, 1, 'Shrani brez prijave', 'Prikazan je poziv k prijavi', protected_action)
        self.step(3, 2, 'Klikni Prijavi se', 'Prijavni obrazec na /login', login_page)
        self.step(3, 3, 'Oddaj napačne prijavne podatke', 'Točna napaka in odsotnost prijavljene seje', invalid_login)
        self.step(3, 4, 'Odpri AI in vpiši osnutek', 'Vnos sprejet, Pošlji omogočen', assistant)

    def run_scenario_4(self):
        def module():
            self.open('/modules/mod_014')
            self.heading('Analiza in obdelava podatkov')
        def nodes():
            node = self.driver.find_element(By.CSS_SELECTOR, 'button[data-lu-node="0"]')
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", node)
            self.wait.until(EC.visibility_of(node))
        def unit():
            self.click((By.CSS_SELECTOR, 'button[data-lu-node="0"]'))
            self.path('/learning-units/ue_036')
            self.heading('Uvod v podatkovno modeliranje')
        self.step(4, 1, 'Odpri mod_014', 'Pravilen naslov modula', module)
        self.step(4, 2, 'Preglej učne enote', 'Prvo vozlišče je vidno', nodes)
        self.step(4, 3, 'Klikni prvo vozlišče', 'Pot ue_036 in pravilen naslov', unit)

    def run_scenario_5(self):
        def start():
            self.open('/assessment?target_type=module&target_id=mod_014')
            return self.visible(QUESTION).text
        def yes():
            return self.answer('Da')
        def submit():
            first = self.visible(QUESTION).text
            label = self.visible(NEXT).text
            self.click(NEXT)
            if 'Naslednjo' in label:
                self.wait.until(lambda d: d.find_element(*QUESTION).text != first)
                assert 'Zaključi' in self.answer('Ne')
                self.click(NEXT)
            return self.assessment_result('/modules/mod_014')
        self.step(5, 1, 'Odpri vprašalnik mod_014', 'Prvo vprašanje je vidno', start)
        self.step(5, 2, 'Odgovori Da', 'Izbran Da in omogočen naslednji korak', yes)
        self.step(5, 3, 'Nadaljuj, odgovori Ne in zaključi', 'Shranjena samoocena in vrnitev na mod_014', submit)

    def run_scenario_6(self):
        def about():
            return self.open('/about')
        def navigation():
            for path in ('/', '/search', '/about', '/register'):
                self.click((By.CSS_SELECTOR, f"header a[href='{path}']"))
                self.path(path)
                self.heading()
            self.open('/about')
        def mobile():
            try:
                self.driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
                    'width': 375, 'height': 812, 'deviceScaleFactor': 1, 'mobile': False})
                def fits(driver):
                    sizes = driver.execute_script('return {width: innerWidth, height: innerHeight, '
                                                  'contentWidth: document.documentElement.scrollWidth};')
                    return sizes if sizes['width'] == 375 and sizes['height'] == 812 and sizes['contentWidth'] <= 376 else False
                sizes = self.wait.until(fits, 'Viewport mismatch or horizontal overflow')
                self.heading()
                # Capture while emulation is still active.
                self.capture_screenshot('ts06_03_mobile.png')
                return str(sizes)
            finally:
                self.driver.execute_cdp_cmd('Emulation.clearDeviceMetricsOverride', {})
                self.driver.set_window_size(1920, 1080)
        self.step(6, 1, 'Odpri O nas', 'Viden glavni naslov na /about', about)
        self.step(6, 2, 'Klikni štiri navigacijske povezave', 'Vsaka odpre pravo pot z glavnim naslovom', navigation)
        self.step(6, 3, 'Nastavi viewport 375 × 812', 'Pravilna velikost in brez vodoravnega preliva', mobile,
                  'ts06_03_mobile.png')

    def generate_json_summary(self):
        statuses = {}
        for n in self.scenarios:
            steps = [r for r in self.results if r['scenario_id'] == f'TS-NIDIKO-{n:02d}']
            expected = list(range(1, STEP_COUNTS[n] + 1))
            statuses[f'TS-NIDIKO-{n:02d}'] = 'PASS' if (
                not self.execution_error and sorted(r['step_no'] for r in steps) == expected and
                all(r['status'] == 'PASS' for r in steps)) else 'FAIL'
        summary = {
            'run_id': self.run_id, 'started_at': self.started_at,
            'timestamp': datetime.now().astimezone().isoformat(), 'python': platform.python_version(),
            'selenium': selenium.__version__,
            'browser_version': self.driver.capabilities.get('browserVersion') if self.driver else None,
            'git_sha': os.environ.get('GITHUB_SHA'), 'execution_error': self.execution_error,
            'target_environment': self.base_url, 'total_steps': len(self.results),
            'passed_steps': sum(r['status'] == 'PASS' for r in self.results),
            'failed_steps': sum(r['status'] == 'FAIL' for r in self.results),
            'scenario_statuses': statuses, 'steps': self.results,
        }
        (self.output_dir / 'test_execution_summary.json').write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
        suite = ET.Element('testsuite', name='NIDiKo functional', tests=str(len(statuses)),
                           failures=str(sum(s == 'FAIL' for s in statuses.values())))
        for scenario, status in statuses.items():
            steps = [r for r in self.results if r['scenario_id'] == scenario]
            case = ET.SubElement(suite, 'testcase', classname='functional', name=scenario,
                                 time=str(round(sum(r['duration_sec'] for r in steps), 2)))
            if status == 'FAIL':
                ET.SubElement(case, 'failure', message=self.execution_error or 'Failed or missing steps').text = '\n'.join(
                    f"Step {r['step_no']}: {r['actual']}" for r in steps if r['status'] == 'FAIL')
        ET.ElementTree(suite).write(self.output_dir / 'junit.xml', encoding='utf-8', xml_declaration=True)
        return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default=BASE_URL)
    parser.add_argument('--output-dir', help='New output directory; existing evidence is never overwritten')
    parser.add_argument('--scenarios', nargs='+', type=int, choices=STEP_COUNTS, default=list(STEP_COUNTS))
    args = parser.parse_args(argv)
    if not __debug__:
        parser.error('Do not use Python -O: assertions must remain enabled')
    runner = FunctionalTestRunner(args.base_url, args.output_dir, args.scenarios)
    try:
        runner.setup_driver()
        for scenario in runner.scenarios:
            runner.reset_session()
            getattr(runner, f'run_scenario_{scenario}')()
    except Exception as exc:
        runner.execution_error = f'{type(exc).__name__}: {exc}'
        print(runner.execution_error, flush=True)
    finally:
        summary = runner.generate_json_summary()
        runner.teardown_driver()
    print(f"PASS: {summary['passed_steps']}; FAIL: {summary['failed_steps']}", flush=True)
    return 0 if not summary['execution_error'] and all(s == 'PASS' for s in summary['scenario_statuses'].values()) else 1


if __name__ == '__main__':
    sys.exit(main())
