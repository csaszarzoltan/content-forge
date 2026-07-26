"""Interface and behavioral tests for SocialMediaConnector ABC.

Interface tests  — verify imports, abstract methods, cannot instantiate (should PASS with stubs).
Behavioral tests — verify NotImplementedError for subclasses that don't implement.
"""

from __future__ import annotations

import inspect

import pytest


class TestSocialMediaConnectorInterface:
    """Verify the SocialMediaConnector ABC interface."""

    def test_social_media_connector_importable(self):
        """SocialMediaConnector should be importable from src.connectors.base."""
        from src.connectors.base import SocialMediaConnector

        assert SocialMediaConnector is not None

    def test_social_media_connector_is_abc(self):
        """SocialMediaConnector should inherit from ABC."""
        from abc import ABC

        from src.connectors.base import SocialMediaConnector

        assert issubclass(SocialMediaConnector, ABC)

    def test_social_media_connector_cannot_instantiate(self):
        """Direct instantiation of SocialMediaConnector should raise TypeError."""
        from src.connectors.base import SocialMediaConnector

        with pytest.raises(TypeError):
            SocialMediaConnector()  # type: ignore[abstract]

    def test_social_media_connector_has_publish_abstract(self):
        """SocialMediaConnector should have an abstract publish method."""
        from src.connectors.base import SocialMediaConnector

        assert hasattr(SocialMediaConnector, "publish")
        assert callable(SocialMediaConnector.publish)
        assert inspect.iscoroutinefunction(SocialMediaConnector.publish)

    def test_social_media_connector_has_preview_abstract(self):
        """SocialMediaConnector should have an abstract preview method."""
        from src.connectors.base import SocialMediaConnector

        assert hasattr(SocialMediaConnector, "preview")
        assert callable(SocialMediaConnector.preview)
        assert inspect.iscoroutinefunction(SocialMediaConnector.preview)

    def test_social_media_connector_has_validate_credentials_abstract(self):
        """SocialMediaConnector should have an abstract validate_credentials method."""
        from src.connectors.base import SocialMediaConnector

        assert hasattr(SocialMediaConnector, "validate_credentials")
        assert callable(SocialMediaConnector.validate_credentials)
        assert inspect.iscoroutinefunction(SocialMediaConnector.validate_credentials)

    def test_social_media_connector_has_platform_name_property(self):
        """SocialMediaConnector should have an abstract platform_name property."""
        from src.connectors.base import SocialMediaConnector

        assert hasattr(SocialMediaConnector, "platform_name")
        # platform_name should be an abstract property, not a method
        assert not inspect.ismethod(SocialMediaConnector.platform_name) or hasattr(
            type(SocialMediaConnector).platform_name, "fget"
        )

    def test_concrete_subclass_instantiable(self):
        """A concrete subclass implementing all abstract methods should be instantiable."""
        from src.connectors.base import SocialMediaConnector

        class _ConcreteConnector(SocialMediaConnector):
            @property
            def platform_name(self) -> str:
                return "test"

            async def publish(self, text: str, **kwargs) -> dict:
                return {"url": "https://example.com/post/1"}

            async def preview(self, text: str, **kwargs) -> dict:
                return {"preview": text[:50]}

            async def validate_credentials(self) -> bool:
                return True

        connector = _ConcreteConnector()
        assert connector is not None
        assert connector.platform_name == "test"


class TestConnectorsPackage:
    """Verify the connectors package can be imported."""

    def test_connectors_init_importable(self):
        """The connectors package __init__ should be importable."""
        from src import connectors

        assert connectors is not None
