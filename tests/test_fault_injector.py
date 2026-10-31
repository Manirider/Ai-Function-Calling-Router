import pytest
from src.fault_injector import FaultInjector, TimeoutErrorException

def dummy_func(args):
    return {"status": "success", "ok": True}

def test_none_no_fault():
    FaultInjector.reset_counters()
    FaultInjector.set_config({"type":"NONE","persistence":"once"})
    res = FaultInjector.apply("T", dummy_func, {})
    assert res == {"status": "success", "ok": True}

def test_timeout_once():
    FaultInjector.reset_counters()
    FaultInjector.set_config({"type":"TIMEOUT","persistence":"once"})
    with pytest.raises(TimeoutErrorException):
        FaultInjector.apply("T", dummy_func, {})
    # second call should succeed
    res = FaultInjector.apply("T", dummy_func, {})
    assert res == {"status": "success", "ok": True}

def test_timeout_always():
    FaultInjector.reset_counters()
    FaultInjector.set_config({"type":"TIMEOUT","persistence":"always"})
    with pytest.raises(TimeoutErrorException):
        FaultInjector.apply("T", dummy_func, {})
    with pytest.raises(TimeoutErrorException):
        FaultInjector.apply("T", dummy_func, {})

def test_malformed_once():
    FaultInjector.reset_counters()
    FaultInjector.set_config({"type":"MALFORMED_RESPONSE","persistence":"once"})
    res = FaultInjector.apply("T", dummy_func, {})
    # status should be corrupted to invalid
    assert res.get("status") == "invalid"
    assert res.get("ok") is True
    res2 = FaultInjector.apply("T", dummy_func, {})
    assert res2 == {"status": "success", "ok": True}

def test_malformed_always():
    FaultInjector.reset_counters()
    FaultInjector.set_config({"type":"MALFORMED_RESPONSE","persistence":"always"})
    res = FaultInjector.apply("T", dummy_func, {})
    assert res.get("status") == "invalid"

def test_isolation_between_tools():
    FaultInjector.reset_counters()
    FaultInjector.set_config({"type":"TIMEOUT","persistence":"once"})
    with pytest.raises(TimeoutErrorException):
        FaultInjector.apply("A", dummy_func, {})
    # B should also timeout first time because counters per tool name
    with pytest.raises(TimeoutErrorException):
        FaultInjector.apply("B", dummy_func, {})
