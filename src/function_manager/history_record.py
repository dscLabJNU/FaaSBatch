import numpy as np
import gevent


class HistoryRecord():
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
        return 0 if self.is_empty() else self.values.mean()

    def get_std(self):
        return 0 if self.is_empty() else self.values.std()

    def get_max(self):
        return 0 if self.is_empty() else self.values.max()

    def get_last(self):
        return 0 if self.is_empty() else self.values[-1]

    def append(self, value):
        self.values = np.append(self.values, value)

    def is_empty(self):
        return self.size() == 0

    def get_gradient(self):
        if self.size() <= 1:
            return 0
        return np.gradient(self.values)

    def size(self):
        return len(self.values)
