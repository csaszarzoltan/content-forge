"""Data-minimizing family privacy planning primitives."""
def deletion_plan(counts:dict[str,int])->dict[str,int]:
    return {'delete':counts.get('private_ideas',0)+counts.get('private_drafts',0),'pseudonymize':counts.get('published_deliveries',0)}
