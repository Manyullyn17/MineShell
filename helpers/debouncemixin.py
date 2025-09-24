from copy import deepcopy
from textual.timer import Timer

class DebounceMixin:
    def __init__(self):
        super().__init__()
        self._debounce_timers: dict[str, Timer] = {}
        self._prev_filters: dict[str, dict[str, list]] = {}

    def debounce(self, name: str, delay: float, callback, filters: dict[str, list] = {}):
        """
        Schedule a debounced callback.
        `name` identifies the timer, `delay` is seconds,
        `callback` is the function to call.
        """
        # cancel existing timer
        if name in self._debounce_timers:
            timer = self._debounce_timers[name]
            if timer._active:
                timer.stop()

        # set a new timer
        self._debounce_timers[name] = self.set_timer(delay, lambda: self.call_callback(callback, name, filters)) # type: ignore

    def call_callback(self, callback, name: str, filters: dict[str, list] = {}):
        if filters:
            if filters == self._prev_filters.get(name, {}):
                return
            self._prev_filters[name] = deepcopy(filters)
        callback()
    