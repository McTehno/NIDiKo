"""Run the real frontend/API against disposable MongoDB, then prove a defect is detected."""
import argparse
import json
import os
import socket
import subprocess
import sys
import threading
import time
from contextlib import ExitStack
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from local_environment import REPO_ROOT, create_auth_stub, seed_database

RUNNER = Path(__file__).with_name('run_functional_tests.py')
BASE_URL = 'http://localhost:5173'
TITLE = '<title>NIDiKo</title>'
BROKEN_TITLE = '<title>NAMERNA NAPAKA</title>'


def wait_ready(url, processes, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for process in processes:
            if process.poll() is not None:
                raise RuntimeError(f'Application process exited with code {process.returncode}; inspect service logs')
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError):
            pass
        time.sleep(0.2)
    raise TimeoutError(f'Application not ready within {timeout}s: {url}')


def verify_detection(baseline, mutant, restored, codes):
    if codes != [0, 1, 0]:
        raise AssertionError(f'Expected exit codes [0, 1, 0], got {codes}')
    if any(s != 'PASS' for s in baseline['scenario_statuses'].values()):
        raise AssertionError('All baseline scenarios must pass before introducing the defect')
    if mutant['execution_error'] or mutant['total_steps'] != 5 or mutant['failed_steps'] != 1:
        raise AssertionError('Mutation must fail exactly one assertion, not browser/environment setup')
    failed = [s for s in mutant['steps'] if s['status'] == 'FAIL']
    if (failed[0]['scenario_id'], failed[0]['step_no']) != ('TS-NIDIKO-01', 1):
        raise AssertionError('The mutation must be detected by title check TS-NIDIKO-01.1')
    if mutant['scenario_statuses'] != {'TS-NIDIKO-01': 'FAIL'}:
        raise AssertionError('Mutated scenario must fail')
    if restored['scenario_statuses'] != {'TS-NIDIKO-01': 'PASS'}:
        raise AssertionError('Restoring the app must restore the passing scenario')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mongo-uri', default='mongodb://127.0.0.1:27028')
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    database_name = f'nidiko_functional_{time.time_ns()}'
    processes = []
    auth = None
    try:
        for port in (5173, 8008, 54321):
            with socket.socket() as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                probe.bind(('127.0.0.1', port))
        seed_database(args.mongo_uri, database_name)
        env = {**os.environ, 'MONGODB_URI': args.mongo_uri, 'DATABASE_NAME': database_name,
               'VITE_API_BASE_URL': 'http://localhost:8008/api',
               'VITE_SUPABASE_URL': 'http://localhost:54321',
               'VITE_SUPABASE_ANON_KEY': 'functional-test-public-placeholder'}
        with ExitStack() as stack:
            build_log = stack.enter_context((output / 'build.log').open('w', encoding='utf-8'))
            npm = 'npm.cmd' if os.name == 'nt' else 'npm'
            subprocess.run([npm, 'run', 'build'], cwd=REPO_ROOT / 'frontend', env=env,
                           stdout=build_log, stderr=subprocess.STDOUT, check=True)
            auth = create_auth_stub()
            threading.Thread(target=auth.serve_forever, daemon=True).start()
            commands = [
                ([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8008'],
                 REPO_ROOT / 'backend', 'backend.log'),
                # Start Vite directly so terminate() also stops the server on Windows.
                (['node', 'node_modules/vite/bin/vite.js', 'preview', '--host', '127.0.0.1',
                  '--port', '5173', '--strictPort'], REPO_ROOT / 'frontend', 'frontend.log'),
            ]
            try:
                for command, cwd, name in commands:
                    log = stack.enter_context((output / name).open('w', encoding='utf-8'))
                    processes.append(subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT))
                wait_ready('http://localhost:8008/api/learning-paths/up_001', processes)
                wait_ready(BASE_URL, processes)
                wait_ready('http://localhost:54321/health', processes)

                def run(name, scenarios=None):
                    command = [sys.executable, str(RUNNER), '--base-url', BASE_URL,
                               '--output-dir', str(output / name)]
                    if scenarios:
                        command.extend(['--scenarios', *map(str, scenarios)])
                    with (output / f'{name}.log').open('w', encoding='utf-8') as log:
                        code = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
                    summary = json.loads((output / name / 'test_execution_summary.json').read_text(encoding='utf-8'))
                    print(f'{name}: exit {code}; PASS {summary["passed_steps"]}; FAIL {summary["failed_steps"]}', flush=True)
                    return code, summary

                baseline_code, baseline = run('baseline')
                if baseline_code:
                    raise AssertionError('Baseline failed; inspect baseline.log and baseline/test_execution_summary.json')
                if auth.rejected_logins != 1:
                    raise AssertionError('Expected exactly one invalid login request to the Auth stub')
                changes = {
                    REPO_ROOT / 'frontend/index.html': (TITLE.encode(), BROKEN_TITLE.encode()),
                    REPO_ROOT / 'frontend/src/app/PageTitleManager.tsx':
                        (b"'/': 'NIDiKo'", b"'/': 'NAMERNA NAPAKA'"),
                }
                originals = {path: path.read_bytes() for path in changes}
                for path, (before, after) in changes.items():
                    if originals[path].count(before) != 1:
                        raise AssertionError(f'Expected one mutation target in {path.name}')
                (output / 'intentional-defect.diff').write_text(
                    '--- frontend/index.html\n+++ frontend/index.html (temporary)\n'
                    f'-{TITLE}\n+{BROKEN_TITLE}\n'
                    '--- frontend/src/app/PageTitleManager.tsx\n'
                    '+++ frontend/src/app/PageTitleManager.tsx (temporary)\n'
                    "-  '/': 'NIDiKo',\n+  '/': 'NAMERNA NAPAKA',\n", encoding='utf-8')
                try:
                    for path, (before, after) in changes.items():
                        path.write_bytes(originals[path].replace(before, after))
                    with (output / 'mutation-build.log').open('w', encoding='utf-8') as log:
                        subprocess.run([npm, 'run', 'build'], cwd=REPO_ROOT / 'frontend', env=env,
                                       stdout=log, stderr=subprocess.STDOUT, check=True)
                    mutant_code, mutant = run('intentional-defect', [1])
                finally:
                    for path, original in originals.items():
                        path.write_bytes(original)
                    with (output / 'restored-build.log').open('w', encoding='utf-8') as log:
                        subprocess.run([npm, 'run', 'build'], cwd=REPO_ROOT / 'frontend', env=env,
                                       stdout=log, stderr=subprocess.STDOUT, check=True)
                restored_code, restored = run('restored', [1])
                codes = [baseline_code, mutant_code, restored_code]
                verify_detection(baseline, mutant, restored, codes)
                report = {'status': 'PASS', 'database': database_name,
                          'auth_mode': 'local Supabase protocol stub; no real Supabase verification',
                          'rejected_login_requests': auth.rejected_logins,
                          'defect': 'Changed home page title in index.html and PageTitleManager.tsx to NAMERNA NAPAKA',
                          'detected_by': 'TS-NIDIKO-01.1', 'exit_codes': codes,
                          'source_restored': all(path.read_bytes() == original for path, original in originals.items())}
                (output / 'mutation_summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
                print('Intentional defect detected; app restored; scenario passes again.', flush=True)
            finally:
                for process in reversed(processes):
                    if process.poll() is None:
                        process.terminate()
                for process in processes:
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
    except Exception as exc:
        (output / 'suite_error.txt').write_text(f'{type(exc).__name__}: {exc}', encoding='utf-8')
        print(f'{type(exc).__name__}: {exc}', file=sys.stderr)
        return 1
    finally:
        if auth:
            auth.shutdown()
            auth.server_close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
