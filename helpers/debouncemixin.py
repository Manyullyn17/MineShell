from textual.timer import Timer

class DebounceMixin:
    def __init__(self):
        super().__init__()
        self._debounce_timers: dict[str, Timer] = {}

    def debounce(self, name: str, delay: float, callback):
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
        self._debounce_timers[name] = self.set_timer(delay, callback) # type: ignore
