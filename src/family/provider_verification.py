"""Privacy-safe provider outcome normalization."""
from __future__ import annotations

_ALLOWED={'id','workspace_id','channel','scenario','state','http_status','provider_correlation_id','remote_id','error_code','retry_after_at','cleanup_state','started_at','completed_at','attempt_count'}
def classify_outcome(status:int|None,remote_id:str|None,ambiguous:bool)->tuple[str,str|None]:
    if ambiguous or (status and 200<=status<300 and not remote_id): return 'UNKNOWN','provider_state_unknown'
    if status and 200<=status<300 and remote_id: return 'PUBLISHED',None
    if status in (401,): return 'FAILED','auth_expired'
    if status in (403,): return 'FAILED','permission_missing'
    if status==429:return 'RETRYABLE','rate_limited'
    if status and status>=500:return 'RETRYABLE','provider_error'
    return 'FAILED','provider_error'
def retryable_channels(deliveries:list[dict])->list[str]:
    return [d['channel'] for d in deliveries if d.get('state') in {'FAILED','RETRYABLE'}]
def safe_evidence(data:dict)->dict:
    return {k:v for k,v in data.items() if k in _ALLOWED}
