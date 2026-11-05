"""TS-03.3 v pravem brskalniku s kontroliranim odgovorom Supabase.

Preverja UI pogodbo, ne dosegljivosti zunanjega Auth. Polni staging E2E ostaja
run_functional_tests.py in se izvaja brez tega testnega nadomestka.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


AUTH_RESPONSE = r"""
(() => {
  const originalFetch = window.fetch.bind(window);
  window.__authTestRequests = [];
  window.fetch = async (input, init) => {
    const url = new URL(typeof input === 'string' ? input : input.url);
    if (url.hostname.endsWith('.supabase.co') &&
        url.pathname === '/auth/v1/token' &&
        url.searchParams.get('grant_type') === 'password') {
      window.__authTestRequests.push({method: init?.method, path: url.pathname});
      return new Response(JSON.stringify({
        code: 'invalid_credentials', message: 'Invalid login credentials'
      }), {status: 400, headers: {'Content-Type': 'application/json'}});
    }
    return originalFetch(input, init);
  };
})();
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:5179')
    parser.add_argument('--output-dir', required=True, help='Nova mapa za dokaze')
    args = parser.parse_args()
    if urlparse(args.base_url).hostname not in ('localhost', '127.0.0.1'):
        parser.error('Kontrolirani odgovor je dovoljen samo pri lokalnem frontendu.')
    if not __debug__:
        parser.error('Preverjanja assert zahtevajo Python brez -O.')
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=False)
    result = {'scenario': 'TS-NIDIKO-03.3', 'mode': 'controlled-auth-response',
              'timestamp': datetime.now(timezone.utc).isoformat(), 'status': 'FAIL'}
    driver = None
    try:
        options = Options()
        for arg in ('--headless=new', '--window-size=1920,1080', '--no-sandbox', '--disable-dev-shm-usage'):
            options.add_argument(arg)
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        result['browser_version'] = driver.capabilities.get('browserVersion')
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': AUTH_RESPONSE})
        driver.get(args.base_url.rstrip('/') + '/login')
        wait = WebDriverWait(driver, 12)
        wait.until(EC.visibility_of_element_located((By.NAME, 'email'))).send_keys('neveljaven_uporabnik@test.si')
        driver.find_element(By.NAME, 'password').send_keys('NepravilnoGeslo123!')
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        alert = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[role='alert']")))
        result['actual'] = alert.text
        assert 'Napačen e-poštni naslov ali geslo.' in alert.text, f'Napacno obvestilo: {alert.text}'
        assert urlparse(driver.current_url).path == '/login', 'Neveljavna prijava je preusmerila uporabnika'
        requests = driver.execute_script('return window.__authTestRequests')
        assert len(requests) == 1 and requests[0]['method'].upper() == 'POST', 'Pricakovan en prijavni zahtevek'
        assert not driver.execute_script("""
            return [localStorage, sessionStorage].some(storage =>
              Object.keys(storage).some(key => /^sb-.*-auth-token$/.test(key)));
        """), 'Po neuspesni prijavi je shranjena seja'
        result['status'] = 'PASS'
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        if driver:
            try:
                if not driver.save_screenshot(str(output / 'login.png')):
                    raise RuntimeError('Zajem slike ni uspel')
            except Exception as exc:
                result['status'] = 'FAIL'
                result['evidence_error'] = str(exc)
            try:
                driver.quit()
            except Exception as exc:
                result['status'] = 'FAIL'
                result['teardown_error'] = str(exc)
        (output / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
