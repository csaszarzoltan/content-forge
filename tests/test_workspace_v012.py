from pathlib import Path
import pytest
from src.product_ops import ContentOpsStore, render_approval_detail, render_workspace
pytestmark=pytest.mark.quick

def ops(tmp_path: Path): return ContentOpsStore(tmp_path/'ops.db')

def test_approval_card_links_to_review(tmp_path):
    s=ops(tmp_path); rid=s.request_approval('asset-1','alice','HIGH',['restricted claim']); html=render_workspace('approvals',s)
    assert f'/workspace/approvals/{rid}' in html and 'Review request' in html

def test_approval_detail_is_contextual_and_actionable(tmp_path):
    s=ops(tmp_path); rid=s.request_approval('asset-1','alice','HIGH',['restricted claim']); html=render_approval_detail(rid,s)
    assert 'restricted claim' in html and 'Record decision' in html and 'Request changes' in html

def test_decided_approval_hides_form(tmp_path):
    s=ops(tmp_path); rid=s.request_approval('asset-1','alice','LOW',[]); s.decide_approval(rid,'bob','APPROVED','ok'); html=render_approval_detail(rid,s)
    assert 'Approved' in html and 'Record decision' not in html

def test_high_risk_self_approval_is_blocked_in_web(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from src.main import app
    from src.routers import workspaces
    monkeypatch.setattr(workspaces,'_DB',tmp_path/'web.db'); rid=workspaces._store().request_approval('asset-1','alice','HIGH',['claim'])
    r=TestClient(app).post(f'/workspace/approvals/{rid}/decision',data={'reviewer':'alice','decision':'APPROVED','reason':'ok'})
    assert r.status_code==403 and 'cannot be approved by its requester' in r.text
