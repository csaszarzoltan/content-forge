"""Consent-oriented, content-free pilot metrics."""
from statistics import median

_EVENTS={'journey_started','first_draft_saved','next_action_answered','invite_previewed','invite_accepted','review_opened','review_decided','publish_completed','connection_recovery_started','connection_recovery_completed','support_intervention','weekly_time_reported','critical_incident_reported'}
_FORBIDDEN=('content','text','caption','token','secret','authorization','email','name','url','remote_id')
def validate_event(event:str,attributes:dict)->None:
    if event not in _EVENTS: raise ValueError('invalid_pilot_event')
    if any(any(x in k.lower() for x in _FORBIDDEN) for k in attributes): raise ValueError('forbidden_pilot_attribute')
def aggregate_metrics(rows:list[dict])->dict:
    if not rows:return {'count':0,'median_first_draft_minutes':None,'next_action_rate':None,'saved_two_hours_rate':None}
    return {'count':len(rows),'median_first_draft_minutes':median(r['first_draft_minutes'] for r in rows),'next_action_rate':sum(bool(r['next_action_under_10s']) for r in rows)/len(rows),'saved_two_hours_rate':sum(r['hours_saved']>=2 for r in rows)/len(rows)}
def decision_state(active:int,critical:int,requested_go:bool)->str:
    if critical:return 'BLOCKED_SAFETY'
    if requested_go and active>=5:return 'GO'
    return 'NO_GO' if requested_go else 'DRAFT'
