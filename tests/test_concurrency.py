import pytest
from src.fault_injector import FaultInjector, TimeoutErrorException

def dummy_func(args):
    return {"status": "success"}

def test_isolation_different_configs():
    FaultInjector.reset_counters()
    # Use context manager to isolate
    with FaultInjector.fault_context({"type":"TIMEOUT","persistence":"once"}):
        with pytest.raises(TimeoutErrorException):
            FaultInjector.apply("A", dummy_func, {})
        # second attempt within same context succeeds
        res = FaultInjector.apply("A", dummy_func, {})
        assert res["status"] == "success"

    # New context with different config
    with FaultInjector.fault_context({"type":"NONE","persistence":"once"}):
        res = FaultInjector.apply("A", dummy_func, {})
        assert res["status"] == "success"

def test_concurrent_isolation_simulated():
    # Simulate two logical requests using separate contexts
    results = []
    def run_cfg(cfg, tool):
        with FaultInjector.fault_context(cfg):
            try:
                FaultInjector.apply(tool, dummy_func, {})
                results.append("ok")
            except TimeoutErrorException:
                results.append("timeout")
    run_cfg({"type":"TIMEOUT","persistence":"once"}, "X")
    run_cfg({"type":"NONE","persistence":"once"}, "X")
    assert results == ["timeout","ok"]
