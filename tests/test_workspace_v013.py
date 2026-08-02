from pathlib import Path
import pytest
from src.product_ops import ContentOpsStore, render_publish_batch_detail, render_workspace
pytestmark=pytest.mark.quick

def ops(tmp_path: Path): return ContentOpsStore(tmp_path/'ops.db')

def batch_with_partial_failure(s):
    bid=s.create_publish_batch('asset-1',['linkedin','twitter'])
    s.record_delivery(bid,'linkedin','PUBLISHED','li-1')
    s.record_delivery(bid,'twitter','RETRYABLE',None)
    return bid

def test_publish_workspace_links_batch_cards(tmp_path):
    s=ops(tmp_path); bid=batch_with_partial_failure(s); html=render_workspace('publish',s)
    assert f'/workspace/publish/{bid}' in html and 'Open delivery batch' in html

def test_publish_detail_preserves_success_and_scopes_retry(tmp_path):
    s=ops(tmp_path); bid=batch_with_partial_failure(s); html=render_publish_batch_detail(bid,s)
    assert 'Linkedin' in html and 'Published' in html
    assert 'Twitter' in html and 'Retry available' in html
    assert 'Retry failed channels' in html
    assert 'linkedin' not in html.split('name="channels"',1)[-1]

def test_request_retry_marks_batch_without_mutating_success(tmp_path):
    s=ops(tmp_path); bid=batch_with_partial_failure(s)
    channels=s.request_publish_retry(bid)
    assert channels==['twitter']
    assert s.publish_batch(bid)['state']=='RETRYING'
    deliveries=s.publish_batch(bid)['deliveries']
    assert next(x for x in deliveries if x['channel']=='linkedin')['state']=='PUBLISHED'

def test_request_retry_rejects_fully_published_batch(tmp_path):
    s=ops(tmp_path); bid=s.create_publish_batch('asset-1',['linkedin']); s.record_delivery(bid,'linkedin','PUBLISHED','li-1')
    with pytest.raises(ValueError,match='PUBLISH_NOT_RETRYABLE'): s.request_publish_retry(bid)
