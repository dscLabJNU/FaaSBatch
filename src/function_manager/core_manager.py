from collections import defaultdict
import logging
import psutil
import gevent
import numpy as np


class Core:
    def __init__(self, str_id) -> None:
        # 核上正在运行的任务数量
        self.containers = []
        # 该核被分配的次数
        self.assign_times = 0
        # 核 id
        self.str_id = str_id
        # utilizations, Only stores specific number
        self.utilizations = []

    def __repr__(self):
        return f"Core-{self.str_id}"


class CoreManaerger:
    log_file = None

    def __init__(self, core_ids) -> None:
        self.busy_cores = []
        for str_id in core_ids:
            self.busy_cores.append(Core(str_id=str_id))
        # Only for evaluation, doesn't matters
        self.busy_cores_old = {
            core: 0 for core in core_ids
        }
        # container -> [busy_cores]
        self.container_cores = defaultdict()

        # Only store the utilization for a specific number of states
        self.num_states = 3

        self.collect_interval = 0.2  # in second
        # Collect core utilization every $(collect_interval) second
        gevent.spawn_later(self.collect_interval, self.collect_utilization)

    def collect_utilization(self):
        gevent.spawn_later(self.collect_interval, self.collect_utilization)
        core_utilization = psutil.cpu_percent(percpu=True)
        for core in self.busy_cores:
            int_id = int(core.str_id)
            core.utilizations.append(core_utilization[int_id])
            # Only stores specific number of the utilizations, since the previous states bring no benifit for evaluation the future load of a core
            diff = len(core.utilizations) - self.num_states
            while diff > 0:
                core.utilizations.pop(0)
                diff -= 1
            # print(f"utilization of {core.str_id} : {core.utilizations}")

    def snapshot_busy_cores(self):
        """Record self.busy_core as slef.busy_core_old
        Only for evaluation !!!
        """
        for core in self.busy_cores:
            self.busy_cores_old[core.str_id] = len(core.containers)

    def show_cores_utils(self):
        """Only for evaluation !!!
        """
        for core in self.busy_cores:
            core_id = core.str_id
            # if self.busy_cores_old[core.str_id] != len(core.containers):
            print(
                f"core {core_id}- load: {self.busy_cores_old[core.str_id]} => {len(core.containers)}, usage: {core.assign_times}")

    def schedule_cores_balance(self, container, concurrency):
        cores_to_assign = self.get_idel_cores_by_balance(concurrency=concurrency)
        self.process(container, concurrency, cores_to_assign)

    def schedule_cores(self, container, concurrency):
        cores_to_assign = self.get_idel_cores_by_utils(concurrency=concurrency)
        self.process(container, concurrency, cores_to_assign)

    def process(self, container, concurrency, cores_to_assign):
        if len(cores_to_assign) != concurrency:
            logging.warning(
                f"We get {len(cores_to_assign)} of available cores, which is less than the concurrency requirement: {concurrency} ")

        self.assign_busy_cores(container=container,
                               cores_to_assign=cores_to_assign)
        aval_core_str = ",".join(
            list(map(lambda x: x.str_id, cores_to_assign)))
        container.container.update(cpuset_cpus=aval_core_str)

    # ============ OPTIONS to get idle cores ============
    def get_idel_cores_by_balance(self, concurrency):
        """Measuring the load of each CPU core by a second-level sort
        1. First sort by len(core.containers), 
        2. and then sort by core.assign_times when we got equivalent len(core.containers)
        """
        sorted_tuple = sorted(
            self.busy_cores, key=lambda core: (len(core.containers), core.assign_times), reverse=False)
        return sorted_tuple[:concurrency]

    def get_idel_cores_by_utils(self, concurrency):
        """Measuring the load of each CPU cores by thier transient (or historical) utilization
        1. First sort by current utilization
        2. and then sort by sum(np.diff(np.array(utilization))) in ascending order when we got equivalent current utilization
        """
        sorted_tuple = sorted(
            self.busy_cores, key=lambda core: (
                core.utilizations[-1], sum(np.diff(np.array(core.utilizations))))
        )
        return sorted_tuple[:concurrency]
    # ============ OPTIONS to get idle cores ============

    def assign_busy_cores(self, container, cores_to_assign):
        self.snapshot_busy_cores()
        for core in cores_to_assign:
            if container in core.containers:
                raise ValueError(
                    f"Duplicate container are going to be assigned on cores: {core}")
            core.containers.append(container)
            core.assign_times += 1
        self.container_cores[container] = cores_to_assign
        logging.info(
            f"Busy cores {cores_to_assign} has been assigned to container {container.container.name} successfully!")
        self.show_cores_utils()

    def get_assigned_cores(self, container):
        return self.container_cores[container]

    def release_busy_cores(self, container):
        assigned_cores = self.get_assigned_cores(container)
        logging.info(
            f"Releasing busy cores {assigned_cores} of container: {container.container.name}")
        for core in assigned_cores:
            if container not in core.containers:
                raise ValueError(f"There is no container using cores: {core}")
            core.containers.remove(container)

        # 'assigned_cores' will be cleared since 'get_assigned_cores' returns a reference
        self.container_cores[container].clear()
        container.container.update(cpuset_cpus=None)

        if not assigned_cores:
            logging.info(
                f"Busy cores of {container.container.name} has been released successfully!")
        else:
            raise ValueError("Release busy cores failed for unkown reasons")


if __name__ == "__main__":
    from random import randint, seed, choice
    logging.basicConfig(format='%(asctime)s: %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s',
                        datefmt='%H:%M:%S', level='INFO')

    class Container:
        def __init__(self, name) -> None:
            self.container = self
            self.name = name

        def update(self, cpuset_cpus):
            logging.info(f"Update cpuset_cpus of to {cpuset_cpus}")
    seed(54)
    containers = []
    num_containers = 100
    # Simulates $num_containers of containers
    for i in range(1, num_containers+1):
        containers.append(Container(name=f"container {i}"))

    num_cores = 16
    # Simulates 16 of cores, each id starts from 0
    cm = CoreManaerger([str(i) for i in range(num_cores)])

    max_concurrency = 32
    # Simulates cores assignment
    for container in containers:
        concurrency = randint(1, max_concurrency)
        logging.info(f"Concurrency: {concurrency}")
        cm.schedule_cores(container, concurrency=concurrency)
        if choice([0, 1, 2]) == 0:
            cm.release_busy_cores(container)
