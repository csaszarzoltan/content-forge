import pytest

from src.family.permissions import capabilities_for
from src.family.pilot import aggregate_metrics, decision_state, validate_event
from src.family.privacy import deletion_plan
from src.family.provider_verification import classify_outcome, retryable_channels, safe_evidence
from src.family.visibility import visibility_for


# US-001..003 RED contracts
def test_us_001_provider_requires_remote_id():
    assert classify_outcome(200, None, False)[0] == 'UNKNOWN'
    assert classify_outcome(201, 'remote-1', False)[0] == 'PUBLISHED'
def test_us_002_selective_retry_excludes_success_and_unknown():
    ds=[{'channel':'linkedin','state':'PUBLISHED'},{'channel':'twitter','state':'RETRYABLE'},{'channel':'other','state':'UNKNOWN'}]
    assert retryable_channels(ds)==['twitter']
def test_us_003_evidence_redacts_secrets():
    out=safe_evidence({'state':'FAILED','token':'secret','authorization':'Bearer x','remote_id':'r'})
    assert out=={'state':'FAILED','remote_id':'r'}

# US-004..006
def test_us_004_pilot_rejects_content_payload():
    with pytest.raises(ValueError, match='forbidden_pilot_attribute'):
        validate_event('first_draft_saved', {'content':'private'})
def test_us_005_timing_and_rates_are_measurable():
    m=aggregate_metrics([{'first_draft_minutes':8,'next_action_under_10s':True,'hours_saved':3},{'first_draft_minutes':12,'next_action_under_10s':False,'hours_saved':1}])
    assert m['median_first_draft_minutes']==10 and m['next_action_rate']==0.5 and m['saved_two_hours_rate']==0.5
def test_us_006_safety_blocks_go():
    assert decision_state(5,1,True)=='BLOCKED_SAFETY'

# US-007..009
def test_us_007_role_capabilities_are_explicit():
    teen=capabilities_for('TEEN_CONTRIBUTOR')
    assert teen['publish']['allowed'] is False and teen['drafts']['allowed'] is True
def test_us_008_deletion_plan_retains_minimum_publication_evidence():
    p=deletion_plan({'private_ideas':2,'private_drafts':1,'published_deliveries':1})
    assert p['delete']==3 and p['pseudonymize']==1
def test_us_009_visibility_never_calls_unknown_public():
    assert visibility_for('UNKNOWN')['code']=='VERIFICATION_REQUIRED'
    assert visibility_for('APPROVED')['code']=='APPROVED_FOR_ADULT_PUBLISHING'
