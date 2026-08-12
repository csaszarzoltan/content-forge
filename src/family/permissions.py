"""Shared, explicit family role capability policy."""
from __future__ import annotations

CATEGORIES=('ideas','drafts','review','publish','connections','billing','members')
_ALLOWED={
'ADULT_OWNER':set(CATEGORIES)-{'billing'},
'ADULT_COLLABORATOR':{'ideas','drafts','review','publish'},
'TEEN_CONTRIBUTOR':{'ideas','drafts'},
'VIEWER':set(),
}
def capabilities_for(role:str)->dict[str,dict[str,object]]:
    if role not in _ALLOWED: raise ValueError('invalid_role')
    return {c:{'allowed':c in _ALLOWED[role],'reason':('Allowed for this role' if c in _ALLOWED[role] else 'Not available for this role')} for c in CATEGORIES}
