"""Test for route53 implementation of the interface."""
from unittest import TestCase

import pytest

from lexicon.tests.providers import integration_tests


class Route53ProviderTests(TestCase, integration_tests.IntegrationTestsV2):
    """Route53 Provider Tests."""

    provider_name = "route53"
    domain = "fullcr1stal.tk"

    def _filter_headers(self):
        """Sensitive headers to be filtered."""
        return ["Authorization"]

    def _test_fallback_fn(self):
        return lambda x: None if x in ("zone_id") else f"placeholder_{x}"

    @integration_tests.vcr_integration_test
    def test_provider_authenticate_private_zone_only(self):
        provider = self._build_provider_with_overrides({"private_zone": "true"})
        with pytest.raises(Exception):
            provider.authenticate()

    @integration_tests.vcr_integration_test
    def test_provider_authenticate_private_zone_false(self):
        provider = self._build_provider_with_overrides({"private_zone": "false"})
        provider.authenticate()
        assert provider.domain_id is not None

    def _build_provider_with_overrides(self, overrides):
        config = self._test_config()
        config.add_config_source(
            integration_tests.EngineOverrideConfigSource(overrides), 0
        )
        return self.provider_module.Provider(config)
