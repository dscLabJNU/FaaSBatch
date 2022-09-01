import numpy as np
import gevent


class HistoryDelay():
    """
    Data structure for request execute delay.
    Only stores the latency in last #self.update_interval seconds!!!
    """

    def __init__(self, update_interval=10) -> None:
        self.values = np.array([])
        self.old_len = 0
        self.update_interval = update_interval  # in s

        gevent.spawn_later(self.update_interval,
                           self.periodically_update_delay)

    def periodically_update_delay(self):
        gevent.spawn_later(self.update_interval,
                           self.periodically_update_delay)

        self.values = np.delete(
            self.values, [x for x in range(self.old_len)])
        self.old_len = len(self.values)

    def get_last10s_delay(self):
        return self.get_mean()

    def get_mean(self):
        if len(self.values) == 0:
            return 0
        return self.values.mean()

    def get_std(self):
        if len(self.values) <= 1:
            return np.inf
        return self.values.std()

    def get_max(self):
        if len(self.values) == 0:
            return 0
        return self.values.max()

    def get_last(self):
        if len(self.values) == 0:
            return 0
        return self.values[-1]

    def append(self, value):
        self.values = np.append(self.values, value)

    def is_empty(self):
        return len(self.values) == 0
