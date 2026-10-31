from src.recovery import recover_timeout, RecoveryContext
from src.llm_provider import OfflineProvider

def test_timeout_attempt_allowed():
    provider = OfflineProvider()
    provider.recovery_ctx = RecoveryContext()
    allowed = recover_timeout(provider, "WeatherLookup", {}, None)
    assert allowed is True
    assert provider.recovery_ctx.timeout_attempted

def test_timeout_max_one_attempt():
    provider = OfflineProvider()
    provider.recovery_ctx = RecoveryContext()
    recover_timeout(provider, "WeatherLookup", {}, None)
    allowed = recover_timeout(provider, "WeatherLookup", {}, None)
    assert allowed is False
