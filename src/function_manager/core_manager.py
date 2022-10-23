from collections import defaultdict
import time
import logging


class CoreManaerger:
    def __init__(self, available_cores) -> None:
        # Idel containers are not in this core-busy list
        # busy_core -> [containers]
        self.busy_cores = {
            core: [] for core in available_cores
        }
        # container -> [busy_cores]
        self.container_cores = defaultdict()

    def shedule_cores(self, container, concurrency):

        logging.info(f"Getting available cores in {concurrency} concurrency")
        cores_to_assgin = self.get_idel_cores(concurrency=concurrency)
        aval_core_str = ",".join(cores_to_assgin)

        logging.info(
            f"Assigning core {cores_to_assgin} to container: {container.container.name}")
        container.container.update(cpuset_cpus=aval_core_str)
        self.assign_busy_cores(container=container,
                               cores_to_assgin=cores_to_assgin)

    # ============ OPTIONS to get idle cores ============
    def get_idel_cores(self, concurrency):
        sorted_tuple = sorted(self.busy_cores.items(),
                              key=lambda x: len(x[1]), reverse=False)

        return [str(x[0]) for x in sorted_tuple[:concurrency]]

    def get_idel_cores_by_start_time(self, concurrency):
        def sum_start_times(containers):
            return sum([c.container.start_time for c in containers])

        sorted_tuple = sorted(self.busy_cores.items(),
                              key=lambda x: sum_start_times(x[1]), reverse=False)
        # print(sorted_tuple)
        return [str(x[0]) for x in sorted_tuple[:concurrency]]
    # ============ OPTIONS to get idle cores ============

    def get_assigned_cores(self, container):
        return self.container_cores[container]

    def assign_busy_cores(self, container, cores_to_assgin):
        for core in cores_to_assgin:
            if container in self.busy_cores[core]:
                raise ValueError(
                    f"Duplicate container are going to be assigned on cores: {core}")
            self.busy_cores[core].append(container)
        self.container_cores[container] = cores_to_assgin
        logging.info(
            f"Busy cores {cores_to_assgin} has been assigned to container {container.container.name} successfully!")

    def release_busy_cores(self, container):
        assigned_cores = self.get_assigned_cores(container)
        logging.info(
            f"Releasing busy cores {assigned_cores} of container: {container.container.name}")
        for core in assigned_cores:
            if container not in self.busy_cores[core]:
                raise ValueError(f"There is no container using cores: {core}")
            self.busy_cores[core].remove(container)

        self.container_cores[container].clear()
        if not assigned_cores:
            logging.info(
                f"Busy cores of {container.container.name} has been released successfully!")
        else:
            raise ValueError("Release busy cores failed for unkown reasons")


if __name__ == "__main__":
    from random import sample, randint, seed

    class Container:
        def __init__(self, start_time) -> None:
            # self.start_time = time.time()
            self.start_time = start_time
            self.container = self


    containers = []
    for i in range(1, 10):
        containers.append(Container(start_time=i))
    seed(1234)
    busy_cores = {
        "3": sample(containers, randint(1, len(containers))),
        "5": sample(containers, randint(1, len(containers))),
        "8": sample(containers, randint(1, len(containers))),
        "2": sample(containers, randint(1, len(containers))),
        "1": sample(containers, randint(1, len(containers))),
        "7": sample(containers, randint(1, len(containers)))
    }
    for core, containers in busy_cores.items():
        # print(f"Core {core} running {len(containers)} of containers")
        print(f"Core: {core}, sum of start times {sum([c.start_time for c in containers])}")
        # for i, container in enumerate(containers):
        # print(f"\t- Container {i} started at {container.start_time}")

    cm = CoreManaerger([])
    cm.busy_cores = busy_cores

    concurrency = 1
    print(cm.get_idel_cores_by_start_time(concurrency))
