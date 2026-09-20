#!/usr/bin/env python3
"""Validate installed skill structure and fixture coverage; never run model evals."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

REFERENCE_FILES = (
    'references/templates.md',
    'references/session-kernel.md',
    'references/agent-runtime-contract.md',
    'references/tool-contract.md',
    'references/orchestration.md',
    'references/evaluation-security.md',
)
REQUIRED_FILES = ('SKILL.md', 'agents/openai.yaml', *REFERENCE_FILES,
                  'evals/behavior-cases.json')
VALID_ACTIONS = {'boundary', 'discussion', 'generation', 'optimization', 'evaluation'}
VALID_DOMAINS = {'general', 'image', 'video', 'agent', 'tools', 'orchestration', 'safety'}
REQUIRED_ACTIONS = VALID_ACTIONS
REQUIRED_DOMAINS = VALID_DOMAINS


def text_list(value: object) -> bool:
    return (isinstance(value, list) and bool(value)
            and all(isinstance(x, str) and bool(x.strip()) for x in value))


def validate_cases(fixture: object) -> list[str]:
    """Validate fixture shape and routing coverage, not semantic correctness."""
    errors: list[str] = []
    if not isinstance(fixture, dict):
        return ['behavior cases: top level must be a mapping']
    if fixture.get('version') != 2:
        errors.append('behavior cases: schema version must be 2')
    if fixture.get('skill') != 'prompt-factory':
        errors.append('behavior cases: wrong skill identifier')
    cases = fixture.get('cases')
    if not isinstance(cases, list) or not cases:
        return errors + ['behavior cases: cases must be a non-empty list']
    seen: set[str] = set()
    covered = {'actions': set(), 'domains': set()}
    for i, case in enumerate(cases):
        label = f'behavior cases[{i}]'
        if not isinstance(case, dict):
            errors.append(f'{label}: case must be a mapping')
            continue
        cid = case.get('id')
        if not isinstance(cid, str) or not cid.strip():
            errors.append(f'{label}: id is required')
        elif cid in seen:
            errors.append(f'{label}: duplicate id {cid}')
        else:
            seen.add(cid)
        request = case.get('request')
        if not isinstance(request, str) or not request.strip():
            errors.append(f'{label}: request is required')
        for key, allowed in [('actions', VALID_ACTIONS), ('domains', VALID_DOMAINS)]:
            values = case.get(key)
            if not text_list(values):
                errors.append(f'{label}: {key} must be a non-empty string list')
                continue
            if len(values) != len(set(values)):
                errors.append(f'{label}: duplicate {key}')
            unknown = set(values) - allowed
            if unknown:
                errors.append(f'{label}: unknown {key}: {sorted(unknown)}')
            covered[key].update(set(values) & allowed)
        expected = case.get('expected')
        if not isinstance(expected, dict):
            errors.append(f'{label}: expected must be a mapping')
            continue
        for key in ('must', 'must_not'):
            if not text_list(expected.get(key)):
                errors.append(f'{label}: expected.{key} must be a non-empty string list')
    for key, required in [('actions', REQUIRED_ACTIONS), ('domains', REQUIRED_DOMAINS)]:
        missing = required - covered[key]
        if missing:
            errors.append(f'behavior cases: missing {key} coverage: {sorted(missing)}')
    return errors


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(f'{path.name}: expected a YAML mapping')
    return data


def frontmatter(text: str) -> dict:
    match = re.match(r'^---\n(.*?)\n---(?:\n|$)', text, re.DOTALL)
    if not match:
        raise ValueError('SKILL.md: invalid YAML frontmatter')
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict):
        raise ValueError('SKILL.md: frontmatter must be a mapping')
    return data


def heading_ids(text: str) -> set[str]:
    ids: set[str] = set()
    for heading in re.findall(r'^#{1,6}\s+(.+)$', text, flags=re.MULTILINE):
        slug = re.sub(r'[^\w\- ]', '', heading.strip().lower()).replace(' ', '-')
        ids.add(slug)
    return ids


def check_links(path: Path, root: Path, text: str) -> list[str]:
    errors: list[str] = []
    for href in re.findall(r'\[[^\]]+\]\(([^)]+)\)', text):
        link = urlsplit(href)
        if link.scheme or link.netloc:
            continue
        target = (path.parent / unquote(link.path)).resolve() if link.path else path
        label = str(path.relative_to(root))
        if not target.is_relative_to(root):
            errors.append(f'{label}: local link escapes skill root: {href}')
        elif not target.is_file():
            errors.append(f'{label}: broken link: {href}')
        elif link.fragment and target.suffix == '.md':
            if unquote(link.fragment) not in heading_ids(target.read_text(encoding='utf-8')):
                errors.append(f'{label}: broken heading link: {href}')
    return errors


def validate(root: Path) -> tuple[list[str], list[str]]:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    for name in REQUIRED_FILES:
        if not (root / name).is_file():
            errors.append(f'missing required file: {name}')
    if errors:
        return errors, warnings
    try:
        text = (root / 'SKILL.md').read_text(encoding='utf-8')
        metadata = frontmatter(text)
        if metadata.get('name') != 'prompt-factory':
            errors.append('SKILL.md: name must be prompt-factory')
        description = metadata.get('description')
        if not isinstance(description, str) or not description.strip():
            errors.append('SKILL.md: description is required')
        else:
            dv = re.search(r'v(\d+\.\d+\.\d+)', description)
            tv = re.search(r'^# 提示詞工廠 v(\d+\.\d+\.\d+)\s*$', text, re.MULTILINE)
            if not dv or not tv or dv.group(1) != tv.group(1):
                errors.append('SKILL.md: missing or inconsistent semantic version')
        if len(text.splitlines()) > 500:
            errors.append('SKILL.md exceeds 500 lines')
        if '[TODO' in text:
            errors.append('SKILL.md contains unfinished scaffolding')
        for name in REFERENCE_FILES:
            if name not in text:
                errors.append(f'SKILL.md does not route to {name}')
        for path in [root / 'SKILL.md', *sorted((root / 'references').glob('*.md'))]:
            content = path.read_text(encoding='utf-8')
            errors.extend(check_links(path, root, content))
            if path.name != 'SKILL.md' and len(content.splitlines()) > 500:
                warnings.append(f'{path.relative_to(root)}: consider splitting long reference')
    except (OSError, ValueError, yaml.YAMLError) as exc:
        errors.append(str(exc))
    try:
        ui = load_yaml(root / 'agents/openai.yaml')
        interface = ui.get('interface')
        if not isinstance(interface, dict):
            errors.append('agents/openai.yaml: interface must be a mapping')
        else:
            if interface.get('display_name') != '提示詞工廠':
                errors.append('agents/openai.yaml: display_name is inconsistent')
            if '$prompt-factory' not in str(interface.get('default_prompt', '')):
                errors.append('agents/openai.yaml: default_prompt must invoke $prompt-factory')
            description = interface.get('short_description')
            if not isinstance(description, str) or not 25 <= len(description) <= 64:
                errors.append('agents/openai.yaml: short_description must contain 25-64 characters')
            for key in ('icon_small', 'icon_large'):
                if key not in interface:
                    continue
                icon = interface[key]
                if not isinstance(icon, str) or not icon:
                    errors.append(f'agents/openai.yaml: invalid {key}')
                    continue
                target = (root / icon).resolve()
                if not target.is_relative_to(root) or not target.is_file():
                    errors.append(f'agents/openai.yaml: missing or invalid {key}')
        policy = ui.get('policy', {})
        if not isinstance(policy, dict):
            errors.append('agents/openai.yaml: policy must be a mapping')
        elif 'allow_implicit_invocation' in policy and not isinstance(policy['allow_implicit_invocation'], bool):
            errors.append('agents/openai.yaml: allow_implicit_invocation must be boolean')
    except (OSError, ValueError, yaml.YAMLError) as exc:
        errors.append(str(exc))
    try:
        fixture = json.loads((root / 'evals/behavior-cases.json').read_text(encoding='utf-8'))
        errors.extend(validate_cases(fixture))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f'behavior cases: {exc}')
    return errors, warnings


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    errors, warnings = validate(root)
    print(json.dumps({'root': str(root), 'evidence_level': 'static',
                      'model_evaluations_run': 0, 'errors': errors, 'warnings': warnings},
                     ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
