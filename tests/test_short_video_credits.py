"""RED contract tests for short-video P0-7: Credit System Integration.

All imports come from src.short_video.credits which does not exist yet.
Every test MUST fail with ModuleNotFoundError (RED) until the developer implements the module.
"""

from __future__ import annotations

import inspect

import pytest


# ---------------------------------------------------------------------------
# Layer 1 — Import / existence tests
# ---------------------------------------------------------------------------
class TestImports:
    """Verify that the expected public API exists in src.short_video.credits."""

    def test_import_credits_module(self):
        from src.short_video import credits  # noqa: F401

    def test_import_credit_manager(self):
        from src.short_video.credits import CreditManager  # noqa: F401

    def test_import_insufficient_credits_error(self):
        from src.short_video.credits import InsufficientCreditsError  # noqa: F401

    def test_import_credit_transaction(self):
        from src.short_video.credits import CreditTransaction  # noqa: F401


# ---------------------------------------------------------------------------
# Layer 2 — Interface / signature tests
# ---------------------------------------------------------------------------
class TestInterface:
    """Verify signatures and types for the P0-7 public API."""

    def test_insufficient_credits_error_is_exception(self):
        from src.short_video.credits import InsufficientCreditsError

        assert issubclass(InsufficientCreditsError, Exception)

    def test_credit_transaction_is_pydantic_model(self):
        from src.short_video.credits import CreditTransaction

        assert hasattr(CreditTransaction, "model_fields")

    def test_credit_transaction_fields(self):
        from src.short_video.credits import CreditTransaction

        fields = CreditTransaction.model_fields
        assert "id" in fields
        assert "user_id" in fields
        assert "job_id" in fields
        assert "clip_id" in fields
        assert "amount" in fields
        assert "balance_after" in fields
        assert "description" in fields
        assert "created_at" in fields

    def test_credit_manager_has_cost_per_clip(self):
        from src.short_video.credits import CreditManager

        assert hasattr(CreditManager, "COST_PER_CLIP")
        assert isinstance(CreditManager.COST_PER_CLIP, int)
        assert CreditManager.COST_PER_CLIP > 0

    def test_credit_manager_init_signature(self):
        from src.short_video.credits import CreditManager

        sig = inspect.signature(CreditManager.__init__)
        assert "db_path" in sig.parameters

    def test_credit_manager_has_get_balance(self):
        from src.short_video.credits import CreditManager

        assert hasattr(CreditManager, "get_balance")
        assert callable(CreditManager.get_balance)

    def test_get_balance_signature(self):
        from src.short_video.credits import CreditManager

        sig = inspect.signature(CreditManager.get_balance)
        assert "user_id" in sig.parameters

    def test_credit_manager_has_deduct(self):
        from src.short_video.credits import CreditManager

        assert hasattr(CreditManager, "deduct")
        assert callable(CreditManager.deduct)

    def test_deduct_signature(self):
        from src.short_video.credits import CreditManager

        sig = inspect.signature(CreditManager.deduct)
        assert "user_id" in sig.parameters
        assert "job_id" in sig.parameters
        assert "clip_count" in sig.parameters

    def test_credit_manager_has_refund(self):
        from src.short_video.credits import CreditManager

        assert hasattr(CreditManager, "refund")
        assert callable(CreditManager.refund)

    def test_refund_signature(self):
        from src.short_video.credits import CreditManager

        sig = inspect.signature(CreditManager.refund)
        assert "user_id" in sig.parameters
        assert "job_id" in sig.parameters
        assert "reason" in sig.parameters

    def test_credit_manager_has_get_transactions(self):
        from src.short_video.credits import CreditManager

        assert hasattr(CreditManager, "get_transactions")
        assert callable(CreditManager.get_transactions)

    def test_get_transactions_signature(self):
        from src.short_video.credits import CreditManager

        sig = inspect.signature(CreditManager.get_transactions)
        assert "user_id" in sig.parameters
        assert "limit" in sig.parameters


# ---------------------------------------------------------------------------
# Layer 3 — Behavioral / future tests
# ---------------------------------------------------------------------------
class TestBehavioral:
    """Behavioral expectations that will pass only after implementation."""

    def test_credit_manager_cost_per_clip(self):
        from src.short_video.credits import CreditManager

        assert CreditManager.COST_PER_CLIP == 10

    def test_credit_manager_init_default(self):
        from src.short_video.credits import CreditManager

        mgr = CreditManager()
        assert mgr.COST_PER_CLIP == 10
        assert mgr._db_path == "short_video.db"

    def test_deduct_insufficient_credits(self, tmp_path):
        from src.short_video.credits import (
            CreditManager,
            InsufficientCreditsError,
        )

        mgr = CreditManager(db_path=str(tmp_path / "credits.db"))
        with pytest.raises(InsufficientCreditsError):
            mgr.deduct(user_id="user1", job_id="job1", clip_count=5)

    def test_deduct_sufficient_credits(self, tmp_path):
        from src.short_video.credits import CreditManager

        mgr = CreditManager(db_path=str(tmp_path / "credits.db"))
        # First add credits via internal method
        mgr._add_credits("user1", 100, "initial")
        new_balance = mgr.deduct(user_id="user1", job_id="job1", clip_count=3)
        assert new_balance == 70  # 100 - (3 * 10)

    def test_refund(self, tmp_path):
        from src.short_video.credits import CreditManager

        mgr = CreditManager(db_path=str(tmp_path / "credits.db"))
        mgr._add_credits("user1", 100, "initial")
        mgr.deduct(user_id="user1", job_id="job1", clip_count=2)
        balance = mgr.refund(
            user_id="user1", job_id="job1", reason="processing failed"
        )
        assert balance == 100  # refunded

    def test_get_balance_zero_initial(self, tmp_path):
        from src.short_video.credits import CreditManager

        mgr = CreditManager(db_path=str(tmp_path / "credits.db"))
        assert mgr.get_balance("new_user") == 0

    def test_get_transactions_empty(self, tmp_path):
        from src.short_video.credits import CreditManager

        mgr = CreditManager(db_path=str(tmp_path / "credits.db"))
        txns = mgr.get_transactions("new_user")
        assert txns == []
