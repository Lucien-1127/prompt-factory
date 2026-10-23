#!/usr/bin/env python3
"""Regression checks for fixture contracts and static-validator evidence limits."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from validate_prompt_factory import validate, validate_cases

ROOT = Path(__file__).resolve().parents[1]


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads((ROOT / 'evals/behavior-cases.json').read_text())

    def test_installed_skill(self):
        errors, warnings = validate(ROOT)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_generation_duplicates_do_not_satisfy_coverage(self):
        case = next(x for x in self.fixture['cases'] if x['actions'] == ['generation'])
        self.fixture['cases'] = [dict(copy.deepcopy(case), id=f'case-{i}') for i in range(30)]
        errors = validate_cases(self.fixture)
        self.assertTrue(any('missing actions coverage' in x for x in errors))
        self.assertTrue(any('missing domains coverage' in x for x in errors))

    def test_compound_action_order_is_preserved(self):
        case = next(x for x in self.fixture['cases'] if x['actions'] == ['evaluation', 'optimization'])
        before = copy.deepcopy(case)
        self.assertEqual(validate_cases(self.fixture), [])
        self.assertEqual(case, before)

    def test_missing_image_domain_is_detected(self):
        for case in self.fixture['cases']:
            case['domains'] = [x for x in case['domains'] if x != 'image'] or ['general']
        self.assertTrue(any('missing domains coverage' in x and 'image' in x
                            for x in validate_cases(self.fixture)))

    def test_malformed_cases_return_errors(self):
        for malformed in [None, [], 'cases', 7]:
            with self.subTest(malformed=malformed):
                self.assertTrue(validate_cases(malformed))
        self.fixture['cases'].append(None)
        self.assertTrue(any('case must be a mapping' in x for x in validate_cases(self.fixture)))

    def test_empty_or_nontext_expectations_rejected(self):
        for value in [[], [' '], [3], [{}]]:
            with self.subTest(value=value):
                data = copy.deepcopy(self.fixture)
                data['cases'][0]['expected']['must'] = value
                self.assertTrue(any('expected.must' in x for x in validate_cases(data)))

    def test_duplicate_case_id_rejected(self):
        self.fixture['cases'].append(copy.deepcopy(self.fixture['cases'][0]))
        self.assertTrue(any('duplicate id' in x for x in validate_cases(self.fixture)))

    def test_malformed_interface_returns_error(self):
        original = Path.read_text
        def read(path, *args, **kwargs):
            if path == ROOT / 'agents/openai.yaml':
                return 'interface: []\n'
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', read):
            errors, _ = validate(ROOT)
        self.assertTrue(any('interface must be a mapping' in x for x in errors))

    def test_bad_heading_link_detected(self):
        original = Path.read_text
        def read(path, *args, **kwargs):
            content = original(path, *args, **kwargs)
            if path == ROOT / 'SKILL.md':
                content += '\n[missing](references/templates.md#does-not-exist)\n'
            return content
        with patch.object(Path, 'read_text', read):
            errors, _ = validate(ROOT)
        self.assertTrue(any('broken heading link' in x for x in errors))


    def test_technique_contract_and_evidence_gate(self):
        contract = (ROOT / 'references/technique-composition.md').read_text(encoding='utf-8')
        for token in ('理解問題', '資訊缺口盤點', '證據閘門', '實際輸出檢驗',
                      '有界自我迭代', '使用者 QC 閉環', 'L1 靜態驗證',
                      'L3 真實運行驗收', '固定雙份交付契約'):
            with self.subTest(token=token):
                self.assertIn(token, contract)

    def test_manifest_references_include_technique_contract(self):
        import yaml
        manifest = yaml.safe_load((ROOT / 'manifest.yaml').read_text(encoding='utf-8'))
        self.assertIn('references/technique-composition.md', manifest['resources'])
        self.assertEqual(manifest['repository']['version'], '11.2.0')

    def test_missing_new_reference_registration_is_detected(self):
        original = Path.read_text
        def read(path, *args, **kwargs):
            content = original(path, *args, **kwargs)
            if path == ROOT / 'manifest.yaml':
                return content.replace('  - references/technique-composition.md', '# deliberately omitted for test')
            return content
        with patch.object(Path, 'read_text', read):
            errors, _ = validate(ROOT)
        self.assertTrue(any('missing registered resource references/technique-composition.md'
                            in error for error in errors))

    def test_clean_example_and_separate_guide(self):
        prompt_path = ROOT / 'examples/summary-prompt.md'
        guide_path = ROOT / 'examples/summary-usage.md'
        self.assertTrue(prompt_path.is_file())
        self.assertTrue(guide_path.is_file())
        prompt = prompt_path.read_text(encoding='utf-8')
        guide = guide_path.read_text(encoding='utf-8')
        for required in ('恰好三點', '30 個中文字', '繁體中文',
                         '不加入未出現的事實', '逐字稿為空'):
            self.assertIn(required, prompt)
        for forbidden in ('## 如何使用', '## 示例', '技巧候選', '多代理',
                          '請先閱讀使用說明'):
            self.assertNotIn(forbidden, prompt)
        for required in ('## 如何使用', '## 示例', '## 限制', '## 失敗時怎麼做'):
            self.assertIn(required, guide)

    def test_behavior_fixtures_include_user_qc(self):
        ids = {case['id'] for case in self.fixture['cases']}
        self.assertIn('user-qc-closed-loop', ids)
        self.assertIn('technique-feedback-based-revision', ids)


if __name__ == '__main__':
    unittest.main()
