import threading

_signal_state = threading.local()
_signal_state.active = True


def signals_enabled():
    return getattr(_signal_state, "active", True)


def disable_signals():
    _signal_state.active = False


def enable_signals():
    _signal_state.active = True
