"""Lokalni testi poganjalnika; ne klicejo staging okolja ali brskalnika."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def module():
    spec = importlib.util.spec_from_file_location(
        'functional_runner', Path(__file__).with_name('run_functional_tests.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_steps_cannot_pass(module, tmp_path):
    runner = module.FunctionalTestRunner(output_dir=tmp_path / 'run')
    runner.record_step('TS-01', 'Tester', 1, 'akcija', 'rezultat', 'rezultat', 'PASS', 1)
    summary = runner.generate_json_summary()
    assert summary['scenario_statuses']['TS-NIDIKO-01'] == 'FAIL'
    assert summary['scenario_statuses']['TS-NIDIKO-06'] == 'FAIL'
    assert summary['steps'][0]['scenario_id'] == 'TS-NIDIKO-01'


def test_preserves_previous_evidence(module, tmp_path):
    existing = tmp_path / 'run'
    existing.mkdir()
    evidence = existing / 'test_execution_summary.json'
    evidence.write_text('previous evidence')
    with pytest.raises(FileExistsError):
        module.FunctionalTestRunner(output_dir=existing)
    assert evidence.read_text() == 'previous evidence'


def test_setup_failure_still_exports_failure_and_returns_nonzero(module, tmp_path):
    output = tmp_path / 'run'
    with patch.object(module.sys, 'argv', ['runner', '--output-dir', str(output)]), \
         patch.object(module.FunctionalTestRunner, 'setup_driver', side_effect=RuntimeError('no browser')):
        assert module.main() == 1
    summary = json.loads((output / 'test_execution_summary.json').read_text(encoding='utf-8'))
    assert 'no browser' in summary['execution_error']
    assert set(summary['scenario_statuses'].values()) == {'FAIL'}


def test_failed_step_retains_original_error_when_screenshot_fails(module, tmp_path):
    runner = module.FunctionalTestRunner(output_dir=tmp_path / 'run')
    runner.driver = Mock()
    runner.driver.save_screenshot.side_effect = RuntimeError('screenshot failed')
    runner.record_step('TS-03', 'Tester', 3, 'login', 'rejection', 'missing rejection', 'FAIL', 1)
    assert runner.results[0]['actual'] == 'missing rejection'
    assert runner.results[0]['status'] == 'FAIL'
    assert runner.results[0]['screenshot'] is None


def test_all_steps_required_and_one_failure_fails_scenario(module, tmp_path):
    runner = module.FunctionalTestRunner(output_dir=tmp_path / 'run')
    for scenario, count in enumerate((5, 5, 4, 3, 3, 3), 1):
        for step in range(1, count + 1):
            status = 'FAIL' if (scenario, step) == (3, 3) else 'PASS'
            runner.record_step(f'TS-{scenario:02d}', 'Tester', step, '', '', '', status, 0)
    summary = runner.generate_json_summary()
    assert summary['scenario_statuses']['TS-NIDIKO-03'] == 'FAIL'
    assert sum(s == 'PASS' for s in summary['scenario_statuses'].values()) == 5
    assert summary['passed_steps'] == 22
    assert summary['failed_steps'] == 1


def test_duplicate_steps_cannot_replace_missing_step(module, tmp_path):
    runner = module.FunctionalTestRunner(output_dir=tmp_path / 'run', scenarios=[1])
    for number in (1, 2, 3, 4, 4):
        runner.record_step('TS-01', 'Tester', number, '', '', '', 'PASS', 0)
    assert runner.generate_json_summary()['scenario_statuses'] == {'TS-NIDIKO-01': 'FAIL'}


def test_runner_instances_keep_their_own_target_and_evidence(module, tmp_path):
    first = module.FunctionalTestRunner('http://first.test', tmp_path / 'first', [1])
    second = module.FunctionalTestRunner('http://second.test', tmp_path / 'second', [6])
    assert first.generate_json_summary()['target_environment'] == 'http://first.test'
    assert second.generate_json_summary()['target_environment'] == 'http://second.test'
    assert (tmp_path / 'first/test_execution_summary.json').exists()
    assert (tmp_path / 'second/test_execution_summary.json').exists()


def test_junit_reports_missing_scenarios_and_escapes_errors(module, tmp_path):
    import xml.etree.ElementTree as ET
    runner = module.FunctionalTestRunner(output_dir=tmp_path / 'run')
    runner.execution_error = 'Setup failed: <browser> & driver'
    runner.generate_json_summary()
    suite = ET.parse(tmp_path / 'run/junit.xml').getroot()
    assert suite.attrib['tests'] == '6'
    assert suite.attrib['failures'] == '6'
    assert len(suite.findall('testcase/failure')) == 6
    assert suite.find('testcase/failure').attrib['message'] == runner.execution_error


@pytest.fixture
def local_suite(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parent))
    import run_local_suite
    return run_local_suite


def mutation_reports():
    baseline = {'scenario_statuses': {f'TS-NIDIKO-{n:02d}': 'PASS' for n in range(1, 7)}}
    mutant = {'execution_error': None, 'total_steps': 5, 'failed_steps': 1,
              'steps': [{'scenario_id': 'TS-NIDIKO-01', 'step_no': 1, 'status': 'FAIL'}],
              'scenario_statuses': {'TS-NIDIKO-01': 'FAIL'}}
    restored = {'scenario_statuses': {'TS-NIDIKO-01': 'PASS'}}
    return baseline, mutant, restored


def test_mutation_requires_a_passing_baseline_specific_failure_and_restoration(local_suite):
    baseline, mutant, restored = mutation_reports()
    local_suite.verify_detection(baseline, mutant, restored, [0, 1, 0])
    mutant['execution_error'] = 'Browser did not start'
    with pytest.raises(AssertionError, match='not browser/environment setup'):
        local_suite.verify_detection(baseline, mutant, restored, [0, 1, 0])


@pytest.mark.parametrize('case', ['baseline', 'wrong_step', 'extra_failure', 'restoration', 'exit_code'])
def test_unrelated_failures_cannot_count_as_mutation_detection(local_suite, case):
    baseline, mutant, restored = mutation_reports()
    codes = [0, 1, 0]
    if case == 'baseline':
        baseline['scenario_statuses']['TS-NIDIKO-03'] = 'FAIL'
    elif case == 'wrong_step':
        mutant['steps'][0]['step_no'] = 3
    elif case == 'extra_failure':
        mutant['failed_steps'] = 2
    elif case == 'restoration':
        restored['scenario_statuses']['TS-NIDIKO-01'] = 'FAIL'
    elif case == 'exit_code':
        codes[1] = 0
    with pytest.raises(AssertionError):
        local_suite.verify_detection(baseline, mutant, restored, codes)


@pytest.mark.parametrize('uri,name', [
    ('mongodb://production.example', 'nidiko_functional_test'),
    ('mongodb://127.0.0.1', 'psi_up'),
])
def test_seed_rejects_external_host_or_production_database(local_suite, uri, name):
    with pytest.raises(ValueError):
        local_suite.seed_database(uri, name)


def test_startup_failure_stops_already_started_services(local_suite, tmp_path):
    process = Mock()
    process.poll.return_value = None
    output = tmp_path / 'suite'
    with patch.object(local_suite.sys, 'argv', ['suite', '--output-dir', str(output)]), \
         patch.object(local_suite.socket, 'socket'), \
         patch.object(local_suite, 'seed_database'), \
         patch.object(local_suite, 'create_auth_stub'), \
         patch.object(local_suite.threading, 'Thread'), \
         patch.object(local_suite.subprocess, 'run'), \
         patch.object(local_suite.subprocess, 'Popen', side_effect=[process, OSError('frontend missing')]):
        assert local_suite.main() == 1
    process.terminate.assert_called_once()
    process.wait.assert_called_once()
    assert 'frontend missing' in (output / 'suite_error.txt').read_text()


def test_navigation_retries_stale_heading_and_link(module, tmp_path):
    runner = module.FunctionalTestRunner(output_dir=tmp_path / 'run')
    runner.driver = Mock()
    runner.wait = module.WebDriverWait(runner.driver, 0.2, poll_frequency=0.001)
    link = Mock()
    runner.driver.find_element.side_effect = [module.StaleElementReferenceException(), link]
    heading = Mock()
    heading.is_displayed.side_effect = [module.StaleElementReferenceException(), True]
    heading.text = 'Prijava'
    runner.driver.find_elements.return_value = [heading]
    runner.driver.current_url = 'http://example.test/login'
    runner.navigate_from_header('/login')
    assert runner.driver.find_element.call_count == 2
    assert heading.is_displayed.call_count == 2
    link.click.assert_called_once()


@pytest.mark.parametrize('url,heading_text', [('/wrong', 'Naslov'), ('/login', '')])
def test_navigation_still_rejects_wrong_page(module, tmp_path, url, heading_text):
    from selenium.common.exceptions import TimeoutException
    runner = module.FunctionalTestRunner(output_dir=tmp_path / 'run')
    runner.driver = Mock()
    runner.wait = module.WebDriverWait(runner.driver, 0.01, poll_frequency=0.001)
    runner.driver.current_url = 'http://example.test' + url
    runner.driver.find_elements.return_value = [Mock(text=heading_text)]
    with pytest.raises(TimeoutException):
        runner.navigate_from_header('/login')
