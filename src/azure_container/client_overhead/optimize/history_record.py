import numpy as np
import const


class HistoryRecord():
    """
    Data structure for request execute delay.
    Only stores the latency in last #self.update_interval seconds!!!
    """

    def __init__(self) -> None:
        self.values = np.array([])

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
        """
        values: [diff_0, ..., diff_i, time_stamp]
        Last one value is the latest arrival timestamp,
        it is used to calculate the next iat (inter-arrival time)
        """
        if self.size() > 0:
            self.values[-1] = value - self.values[-1]
        self.values = np.append(self.values, value)

    def get_percentail(self, percent):
        """
        Calculate ${percent} percentail without the last value

        A default idle time is set for some cold invocations
        """
        if self.size() <= const.DEFAULT_COLD_SAMPLES:
            return const.DEFAULT_IDLE_INTERVAL
        return np.percentile(self.values[:-1], percent)

    def clear(self):
        self.values = np.array([])

    def is_empty(self):
        return self.size() == 0

    def get_gradient(self):
        if self.size() <= 1:
            return 0
        return np.gradient(self.values)

    def size(self):
        return len(self.values)