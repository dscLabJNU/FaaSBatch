import numpy as np
import gevent


class HistoryDelay():
    """
    Data structure for request execute delay.
    Only stores the latency in last #self.update_interval seconds!!!
    """

    def __init__(self) -> None:
        self.history_delay = np.array([])
        self.old_len = 0
        self.update_interval = 100  # in s

        gevent.spawn_later(self.update_interval,
                           self.periodically_update_delay)

    def periodically_update_delay(self):
        gevent.spawn_later(self.update_interval,
                           self.periodically_update_delay)

        self.history_delay = np.delete(
            self.history_delay, [x for x in range(self.old_len)])
        self.old_len = len(self.history_delay)

    def get_last10s_delay(self):
        return self.get_mean()

    def get_mean(self):
        if len(self.history_delay) == 0:
            return 0
        return self.history_delay.mean()

    def get_max(self):
        if len(self.history_delay) == 0:
            return 0
        return self.history_delay.max()

    def get_last(self):
        if len(self.history_delay) == 0:
            return 0
        return self.history_delay[-1]

    def append(self, value):
        self.history_delay = np.append(self.history_delay, value)

