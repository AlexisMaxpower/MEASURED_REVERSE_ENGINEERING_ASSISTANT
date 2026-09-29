from __future__ import annotations
import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator, FormatChecker
REPO_ROOT=Path(__file__).resolve().parents[2]
SCHEMA_PATH=REPO_ROOT/'core'/'contracts'/'mrea_contracts_v1.schema.json'
FIXTURE_ROOT=REPO_ROOT/'tests'/'fixtures'/'contracts'
CASES={'project_v1.json':'ProjectContract','capture_package_v1.json':'CapturePackage','measurement_package_v1.json':'MeasurementPackage','sketch_package_v1.json':'SketchPackage','cad_package_v1.json':'CADPackage','cad_verification_v1.json':'CADVerificationReport','lifecycle_event_v1.json':'LifecycleEvent'}
def _load(path:Path)->dict:return json.loads(path.read_text(encoding='utf-8'))
@pytest.fixture(scope='module')
def root_schema()->dict:return _load(SCHEMA_PATH)
@pytest.mark.parametrize(('fixture_name','definition_name'),CASES.items())
def test_canonical_fixture_matches_owned_schema(root_schema,fixture_name,definition_name):
    scoped={'$schema':root_schema['$schema'],'$defs':root_schema['$defs'],'$ref':f'#/$defs/{definition_name}'}
    Draft202012Validator(scoped,format_checker=FormatChecker()).validate(_load(FIXTURE_ROOT/fixture_name))
def test_golden_contract_chain_ids_are_consistent():
    p=_load(FIXTURE_ROOT/'project_v1.json');c=_load(FIXTURE_ROOT/'capture_package_v1.json');m=_load(FIXTURE_ROOT/'measurement_package_v1.json');s=_load(FIXTURE_ROOT/'sketch_package_v1.json');cad=_load(FIXTURE_ROOT/'cad_package_v1.json');v=_load(FIXTURE_ROOT/'cad_verification_v1.json')
    assert c['project_id']==p['project_id'] and c['part_id']==p['part_id']
    assert m['project_id']==p['project_id'] and m['part_id']==p['part_id'] and m['capture_package_id']==c['capture_package_id']
    assert s['project_id']==p['project_id'] and s['part_id']==p['part_id']
    assert cad['sketch_package_id']==s['sketch_package_id']
    assert v['cad_package_id']==cad['cad_package_id'] and v['sketch_package_id']==s['sketch_package_id']
