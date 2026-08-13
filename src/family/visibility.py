"""Consistent private/public state language."""
_MAP={
'IDEA':('PRIVATE_IDEA','Private to family'),'DRAFT':('PRIVATE_DRAFT','Private draft'),
'PENDING':('WAITING_FOR_REVIEW','Waiting for adult review'),'APPROVED':('APPROVED_FOR_ADULT_PUBLISHING','Approved for adult publishing'),
'QUEUED':('PUBLISHING','Publishing'),'PUBLISHING':('PUBLISHING','Publishing'),
'PUBLISHED':('PUBLIC','Public'),'PARTIAL':('PARTIALLY_PUBLIC','Partially public'),
'UNKNOWN':('VERIFICATION_REQUIRED','Verification required'),'FAILED':('PUBLICATION_FAILED','Publication failed'),'RETRYABLE':('PUBLICATION_FAILED','Publication failed')}
def visibility_for(state:str)->dict[str,str]:
    code,label=_MAP.get(state,('PRIVATE_DRAFT','Private draft')); return {'code':code,'label':label}
