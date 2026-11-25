'''tests/test_config_dryrun.py -- M29-3 guard for the drill config sample set.

Nature of this suite (red line, docs/RUN-UNATTENDED-v1.2.md §1): the files under
config/ are SYNTHETIC, awaiting governance sign-off. They are NOT G7 (F-2). No
assertion here claims that a real run is available; what is claimed is exactly
two things:

  1. positive -- dsm.config.load_all accepts the drill directory (the baseline
     refusal, EXIT_CONFIG=3 for a missing/placeholder config, no longer fires
     on config/), and the landed config consumers (models validators, the
     params_from_config gates of attainment / normalize / evidence /
     diagnostics / pooling, triangulation.is_enabled, cli._build_preflight_config)
     read it without inventing anything, so the chain is walkable from the
     config layer up;
  2. negative -- the gates stay shut: every required file, the PLACEHOLDER
     token scan, the semantic judgements (weight sums, exactly-four monotone
     floors, non-empty actions) and the weight version / provenance policy
     still refuse, so adding this drill set did not weaken any door.

Every governance value asserted below is traceable to a K id and carries the
SYNTH / 合成待签认 marker (yaml comment plus the SYNTH naming convention, e.g.
WIF-SYNTH-2026-01, dsm/fixtures_gen.py:87). No expected value is copied from an
implementation output (R-14); the reference payloads are the frozen fixtures
(fixtures/input/*.jsonl) and the landed consumer key spellings of dsm/*.py.
'''
import shutil
from pathlib import Path

import pytest
import yaml

from dsm import cli, config as cfgmod

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / 'config'
WEIGHTS_STEM = 'weights_WV-SYNTH-2026'
REQUIRED_YAML = ('eval_config', 'redlines', 'grade_rules', 'anchor_set',
                 'ahp_matrices')


def _copy_config(tmp_path):
    dest = tmp_path / 'config'
    shutil.copytree(CONFIG_DIR, dest)
    return dest


def _load(tmp_path, **kw):
    return cfgmod.load_all(_copy_config(tmp_path), **kw)


# --------------------------------------------------------------------- #
# positive: load_all accepts the drill config (baseline: it refused)     #
# --------------------------------------------------------------------- #

def test_load_all_accepts_the_drill_config():
    app = cfgmod.load_all(CONFIG_DIR)
    assert isinstance(app, cfgmod.AppConfig)
    assert sorted(app.weights) == [WEIGHTS_STEM], \
        'the drill set carries exactly one frozen weights document'
    assert app.eval_config['config_class'] == 'SYNTH_DRILL_PENDING_SIGNOFF'
    assert [row['grade_code'] for row in app.grade_rules['grades']] == \
        ['L1', 'L2', 'L3', 'L4']


def test_load_all_with_a_covering_period_passes_and_a_stale_one_blocks():
    # closed interval [effective_from, effective_to] of [L880]; inside passes,
    # outside still leaves through WEIGHT_VERSION_STALE with exit 2 ([L1413]).
    app = cfgmod.load_all(CONFIG_DIR, period='2026-06')
    assert app.weights[WEIGHTS_STEM]['status'] == 'FROZEN'
    with pytest.raises(cfgmod.WeightVersionInvalidError) as excinfo:
        cfgmod.load_all(CONFIG_DIR, period='2027-01')
    assert excinfo.value.exit_code == 2
    assert excinfo.value.reason_code is cfgmod.reason_codes.RC.WEIGHT_VERSION_STALE


def test_landed_models_validate_the_drill_trees():
    app = cfgmod.load_all(CONFIG_DIR)
    from dsm import models
    doc = models.WeightVersionDoc.model_validate(app.weights[WEIGHTS_STEM])
    assert doc.weight_version_id == 'WV-SYNTH-2026'
    assert doc.provenance.whatif_run_id == 'WIF-SYNTH-2026-01'
    anchor = models.AnchorSetDoc.model_validate(app.anchor_set)
    assert anchor.anchor_set_id == 'AS-SYNTH-2026'
    assert len(anchor.strategy_ids) == 8
    rows = [models.GradeRuleRow.model_validate(row)
            for row in app.grade_rules['grades']]
    assert [row.grade_code for row in rows] == ['L1', 'L2', 'L3', 'L4']


def test_landed_config_consumers_read_the_drill_config():
    '''params_from_config of every landed consumer accepts the drill trees --
    the config layer of the chain is walkable (NOT a claim of real-run use).'''
    app = cfgmod.load_all(CONFIG_DIR)
    from dsm import attainment, diagnostics, evidence, normalize, pooling, \
        triangulation
    params = attainment.params_from_config(app)
    assert str(params.attainment_cap) == '1.2', \
        'K-05 drill value, fixtures lineage (tests/test_attainment.py:30)'
    assert normalize.params_from_config(app).method == 'min_max'
    assert evidence.params_from_config(app).evidence_mode == 'GATE_ONLY', \
        'K-13 stays disabled (SDD L1750), no discount table shipped'
    assert diagnostics.params_from_config(app).corr_method == 'pearson'
    assert pooling.params_from_config(app).min_pool_size == 1
    assert triangulation.is_enabled(app.eval_config) is True


def test_cli_preflight_config_builds_from_the_drill_set():
    '''dsm/cli.py:492 _build_preflight_config: all unsigned governance fields
    it demands are present, so the preflight entry of the chain no longer dies
    at the config step. exactly-one weights document is its own precondition.'''
    app = cfgmod.load_all(CONFIG_DIR)
    preflight_config = cli._build_preflight_config(app, '2026-Q3')
    assert str(preflight_config.period_ref_date) == '2026-09-30'
    assert tuple(preflight_config.signed_signoff_status) == ('SIGNED',)
    assert preflight_config.weight_version.weight_version_id == 'WV-SYNTH-2026'
    assert cli._signed_weight_version_id(app) == 'WV-SYNTH-2026'


# --------------------------------------------------------------------- #
# positive: every governance value carries the SYNTH / sign-off marker   #
# --------------------------------------------------------------------- #

def test_every_drill_file_declares_synthetic_pending_signoff():
    for path in sorted(CONFIG_DIR.glob('*.yaml')):
        text = path.read_text(encoding='utf-8')
        assert '合成待签认' in text, path.name + ' lacks the pending marker'
        assert 'G7' in text, path.name + ' lacks the G7-not-signed disclaimer'


def test_every_k_id_from_the_manifest_is_referenced_in_the_drill_comments():
    '''K-01 ~ K-20 (SDD L1734-L1757 via docs/digest/M38-k-params.md) plus the
    K-22 config-key question must all be traceable from the shipped comments.'''
    text = ''.join(path.read_text(encoding='utf-8')
                   for path in sorted(CONFIG_DIR.glob('*.yaml')))
    for index in range(1, 21):
        assert 'K-%02d' % index in text, 'missing K-%02d traceability' % index
    assert 'K-22' in text


def test_identifier_values_follow_the_repo_synth_naming_convention():
    app = cfgmod.load_all(CONFIG_DIR)
    doc = app.weights[WEIGHTS_STEM]
    assert doc['weight_version_id'] == 'WV-SYNTH-2026'
    assert doc['provenance']['whatif_run_id'] == 'WIF-SYNTH-2026-01'
    assert doc['approved_by'] == 'SYNTH_APPROVER'
    assert doc['provenance']['approved_by'] == 'SYNTH_APPROVER'
    assert app.anchor_set['anchor_set_id'] == 'AS-SYNTH-2026'
    assert app.anchor_set['rationale'].startswith('SYNTH-')
    for row in app.grade_rules['grades']:
        assert row['grade_label'].startswith('SYNTH_')
        assert all(action.startswith('SYNTH_') for action in row['actions'])
    assert list(app.ahp_matrices['dimension_matrices']) == \
        ['SYNTH-EXPERT-01', 'SYNTH-EXPERT-02']


# --------------------------------------------------------------------- #
# negative: the doors still shut (gate not weakened by the new files)    #
# --------------------------------------------------------------------- #

@pytest.mark.parametrize('stem', REQUIRED_YAML)
def test_removing_any_required_yaml_still_refuses(tmp_path, stem):
    directory = _copy_config(tmp_path)
    (directory / (stem + '.yaml')).unlink()
    with pytest.raises(cfgmod.ConfigPlaceholderError) as excinfo:
        cfgmod.load_all(directory)
    assert stem in excinfo.value.missing_files
    assert excinfo.value.exit_code == cfgmod.EXIT_CONFIG == 3


def test_removing_the_weights_document_still_refuses(tmp_path):
    directory = _copy_config(tmp_path)
    (directory / (WEIGHTS_STEM + '.yaml')).unlink()
    with pytest.raises(cfgmod.ConfigPlaceholderError) as excinfo:
        cfgmod.load_all(directory)
    assert 'weights_*' in excinfo.value.missing_files, \
        'the wildcard gap of ORCH-23 ruling 18 stays spelled weights_*'


def test_a_placeholder_token_reintroduced_still_refuses(tmp_path):
    directory = _copy_config(tmp_path)
    path = directory / (WEIGHTS_STEM + '.yaml')
    text = path.read_text(encoding='utf-8')
    assert 'CONTRIB: "0.30"' in text
    path.write_text(text.replace('CONTRIB: "0.30"',
                                 'CONTRIB: "PLACEHOLDER-TO-SIGNOFF(K-01)"'),
                    encoding='utf-8', newline='\n')
    with pytest.raises(cfgmod.ConfigPlaceholderError) as excinfo:
        cfgmod.load_all(directory)
    assert excinfo.value.paths == (WEIGHTS_STEM + '.level1_weights.CONTRIB',)


def test_an_empty_required_file_still_refuses(tmp_path):
    directory = _copy_config(tmp_path)
    (directory / 'eval_config.yaml').write_text('', encoding='utf-8',
                                                newline='\n')
    with pytest.raises(cfgmod.ConfigPlaceholderError) as excinfo:
        cfgmod.load_all(directory)
    assert 'eval_config' in excinfo.value.paths, \
        'the bare-stem hit of ORCH-23 ruling 6 (None tree) stays enforced'


def _rewrite(tmp_path, name, mutate):
    directory = _copy_config(tmp_path)
    path = directory / name
    tree = yaml.safe_load(path.read_text(encoding='utf-8'))
    mutate(tree)
    path.write_text(yaml.safe_dump(tree, allow_unicode=True, sort_keys=False),
                    encoding='utf-8', newline='\n')
    return directory


def test_weights_without_level1_weights_still_refuses(tmp_path):
    '''SUM_LEVEL1 is a top-level structural precondition ([L1192], ruling 9).'''
    def mutate(tree):
        del tree['level1_weights']
    with pytest.raises(cfgmod.ConfigSemanticError) as excinfo:
        cfgmod.load_all(_rewrite(tmp_path, WEIGHTS_STEM + '.yaml', mutate))
    assert any(check == 'STRUCTURE' and 'level1_weights' in path
               for check, path, _ in excinfo.value.violations)


def test_non_summing_weights_still_refuse(tmp_path):
    def mutate(tree):
        tree['level1_weights']['CONTRIB'] = '0.50'
    with pytest.raises(cfgmod.ConfigSemanticError) as excinfo:
        cfgmod.load_all(_rewrite(tmp_path, WEIGHTS_STEM + '.yaml', mutate))
    assert any(check == 'SUM_LEVEL1'
               for check, _, _ in excinfo.value.violations), \
        'Sigma W_d = 1 of [L879] / [L902] is still a door, not advice'


def test_broken_floor_monotonicity_still_refuses(tmp_path):
    def mutate(tree):
        tree['grades'][1]['attainment_floor'] = '1.00'
    with pytest.raises(cfgmod.ConfigSemanticError) as excinfo:
        cfgmod.load_all(_rewrite(tmp_path, 'grade_rules.yaml', mutate))
    assert any(check == 'FLOOR_MONOTONIC'
               for check, _, _ in excinfo.value.violations)


def test_empty_actions_still_refuse(tmp_path):
    def mutate(tree):
        tree['grades'][0]['actions'] = []
    with pytest.raises(cfgmod.ConfigSemanticError) as excinfo:
        cfgmod.load_all(_rewrite(tmp_path, 'grade_rules.yaml', mutate))
    assert any(check == 'ACTION_NON_EMPTY'
               for check, _, _ in excinfo.value.violations)


def test_missing_grade_row_still_refuses(tmp_path):
    def mutate(tree):
        tree['grades'] = tree['grades'][:3]
    with pytest.raises(cfgmod.ConfigSemanticError) as excinfo:
        cfgmod.load_all(_rewrite(tmp_path, 'grade_rules.yaml', mutate))
    assert any(check == 'STRUCTURE' and 'L4' in detail
               for check, _, detail in excinfo.value.violations), \
        'exactly the four grades of [L1200] / [L493] remain mandatory'


def test_frozen_weights_without_provenance_still_refuses(tmp_path):
    '''P-11 of [L1435]: a FROZEN version without provenance fails the load.'''
    def mutate(tree):
        del tree['provenance']
    with pytest.raises(cfgmod.WeightVersionInvalidError) as excinfo:
        cfgmod.load_all(_rewrite(tmp_path, WEIGHTS_STEM + '.yaml', mutate))
    assert excinfo.value.exit_code == 2
    assert any(check == 'WEIGHT_PROVENANCE_COMPLETE'
               for check, _, _ in excinfo.value.violations)


def test_frozen_weights_without_whatif_run_id_still_refuses(tmp_path):
    '''序 5 of ORCH-24 ruling 15 ([L880] / [L1374]): FROZEN minus
    whatif_run_id is a block, never a warning.'''
    def mutate(tree):
        del tree['provenance']['whatif_run_id']
    with pytest.raises(cfgmod.WeightVersionInvalidError) as excinfo:
        cfgmod.load_all(_rewrite(tmp_path, WEIGHTS_STEM + '.yaml', mutate))
    assert excinfo.value.exit_code == 2
    assert excinfo.value.reason_code is \
        cfgmod.reason_codes.RC.WEIGHT_MISSING_WHATIF_RUN_ID


def test_draft_status_flips_the_version_gate(tmp_path):
    '''Only FROZEN may score ([L880] / [L1190] / [L1280]) -- with a period
    injected, a DRAFT covering it must still be refused with exit 2.'''
    def mutate(tree):
        tree['status'] = 'DRAFT'
    with pytest.raises(cfgmod.WeightVersionInvalidError) as excinfo:
        cfgmod.load_all(_rewrite(tmp_path, WEIGHTS_STEM + '.yaml', mutate),
                        period='2026-06')
    assert excinfo.value.exit_code == 2
    assert excinfo.value.reason_code is \
        cfgmod.reason_codes.RC.WEIGHT_VERSION_DRAFT
