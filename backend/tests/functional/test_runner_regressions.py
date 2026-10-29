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
