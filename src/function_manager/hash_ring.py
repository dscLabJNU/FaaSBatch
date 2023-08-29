import hashlib


class HashRing:
    def __init__(self, replicas=1):
        self.ring = {}
        self.sorted_keys = []
        self.replicas = replicas

    def _hash(self, key):
        sha1 = hashlib.sha1()
        sha1.update(key.encode('utf-8'))
        return int(sha1.hexdigest(), 16)

    def add_container(self, container):
        for i in range(self.replicas):
            virtual_node_key = f"{container.container.name}:virtual_node:{i}"
            print(f"Adding virtual node to hash ring: {virtual_node_key}")
            hash_key = self._hash(virtual_node_key)
            self.ring[hash_key] = container
            self.sorted_keys.append(hash_key)
        self.sorted_keys.sort()

    def remove_container(self, container):
        for i in range(self.replicas):
            virtual_node_key = f"{container}:virtual_node:{i}"
            hash_key = self._hash(virtual_node_key)
            del self.ring[hash_key]
            self.sorted_keys.remove(hash_key)

    def can_hold_key(self, container, key, cached_keys, cache_capacity=10):
        # 加了当前的key之后，容器中的cached_key数量仍没有达到替换条件
        cur_num_of_cached_keys = len(set(cached_keys) | {key})
        limit_reached = cur_num_of_cached_keys > cache_capacity
        can_hold = not limit_reached
        if limit_reached:
            print(
                f"Container {container.container.name} out cache limit {cur_num_of_cached_keys} of {cache_capacity}")
        return can_hold

    def get_container(self, current_key, container_cached_key, cur_container_pool, cache_capacity):
        if not self.sorted_keys:
            return None

        current_hash = self._hash(current_key)
        idx = self._find_key_index(current_hash)

        # 遍历副本，寻找能够存放当前键的容器
        for _ in range(self.replicas):
            container = self.ring[self.sorted_keys[idx]]
            # if container in cur_container_pool:
            if self.can_hold_key(container=container,
                                 key=current_key,
                                 cache_capacity=cache_capacity,
                                 cached_keys=container_cached_key[container]):
                return container
            idx = (idx + 1) % len(self.sorted_keys)
        for container, keys in container_cached_key.items():
            print(f"{container.container.name} has cached {len(keys)} of items")
        # 如果没有找到能够存放当前键的容器，则从container_cached_key中找到value长度最短的key对应的container
        if container_cached_key:
            container = min(container_cached_key,
                            key=lambda k: len(container_cached_key[k]))
            print(
                f"Seeking the container with {len(container_cached_key[container])} of cached_key ({container.container.name})")
            return container
        return None

    def _find_key_index(self, h):
        for i, k in enumerate(self.sorted_keys):
            if h < k:
                return i
        return 0  # 当超出环的最大键时，返回到环的开始


if __name__ == "__main__":
    class Container:
        def __init__(self, name):
            self.name = name

    # Initialize HashRing
    hash_ring = HashRing(replicas=3)
    containers = [Container(f"container-{i}") for i in range(1, 4)]
    for container in containers:
        hash_ring.add_container(container)

    # Setup container_cached_key
    container_cached_key = {container: set() for container in containers}
    cache_capacity = 10

    # Basic Mapping Test
    print("1. Basic Mapping Test")
    key = "key-42"
    container = hash_ring.get_container(
        key, container_cached_key, containers, cache_capacity)
    print(f"Key {key} mapped to container {container.name if container else None}")

    # Replicas Test
    print("\n2. Replicas Test")
    print(f"Number of sorted keys: {len(hash_ring.sorted_keys)} (expected: 9)")

    # Container Addition/Deletion Test
    print("\n3. Container Addition/Deletion Test")
    hash_ring.remove_container(containers[0])
    print(
        f"Number of sorted keys after removal: {len(hash_ring.sorted_keys)} (expected: 6)")
    new_container = Container("container-4")
    hash_ring.add_container(new_container)
    print(
        f"Number of sorted keys after addition: {len(hash_ring.sorted_keys)} (expected: 9)")

    # Key Allocation Test
    print("\n4. Key Allocation Test")
    all_containers = containers + [new_container]
    container_cached_key = {container: set() for container in all_containers}
    container_count = {container.name: 0 for container in all_containers}
    for i in range(1000):
        key = f"key-{i}"
        container = hash_ring.get_container(
            key, container_cached_key, all_containers, cache_capacity)
        container_count[container.name] += 1
    print("Key distribution:", container_count)

    # Cached Keys Limit Test
    print("\n5. Cached Keys Limit Test")
    container_cached_key = {
        containers[0]: {f"key-{i}" for i in range(10)},
        containers[1]: {f"key-{i}" for i in range(5)},
        containers[2]: {f"key-{i}" for i in range(7)},
    }
    selected_container = hash_ring.get_container(
        "key-new", container_cached_key, containers, cache_capacity)
    print(
        f"Selected container for key with limit reached: {selected_container.name if selected_container else None}")
