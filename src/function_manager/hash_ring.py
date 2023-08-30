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
