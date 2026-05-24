from app.services.providers.base_strategy import ProviderCapabilities
from app.services.providers.factory import ProviderFactory
from app.services.providers.withings.data_247 import Withings247Data
from app.services.providers.withings.oauth import WithingsOAuth
from app.services.providers.withings.strategy import WithingsStrategy


def test_factory_returns_withings_strategy() -> None:
    strategy = ProviderFactory().get_provider("withings")
    assert isinstance(strategy, WithingsStrategy)


def test_withings_strategy_properties() -> None:
    strategy = WithingsStrategy()
    assert strategy.name == "withings"
    assert strategy.api_base_url == "https://wbsapi.withings.net"
    assert strategy.has_cloud_api is True
    assert strategy.workouts is None
    assert isinstance(strategy.oauth, WithingsOAuth)
    assert isinstance(strategy.data_247, Withings247Data)


def test_withings_capabilities() -> None:
    strategy = WithingsStrategy()
    assert strategy.capabilities == ProviderCapabilities(rest_pull=True)
