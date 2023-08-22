import hashlib


class HashRing:
    def __init__(self, replicas=3):
        self.ring = {}
        self.sorted_keys = []
        self.replicas = replicas
        self.mapping = {}

    def _hash(self, key):
        sha1 = hashlib.sha1()
        sha1.update(key.encode('utf-8'))
        return int(sha1.hexdigest(), 16)

    def add_container(self, container):
        for i in range(self.replicas):
            virtual_node_key = f"{container}:virtual_node:{i}"
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

    def can_hold_key(slef, container, key, cached_keys):
        # 加了当前的key之后，容器中的cached_key数量仍没有达到替换条件
        cur_num_of_cached_keys = len(set(cached_keys).add(key))
        if cur_num_of_cached_keys > 10:
            return False
        return True

    def get_container(self, current_key, container_cached_key, cur_container_pool):
        """
        理论上来说self.sorted_keys应该和cur_container_pool对应
        但是由于这些变量是由self管理的, 在并发量大的情况下有可能无法及时获取正确的数据
        正常来说, cur_container_pool的更新速度要比sorted_keys快
        """
        if not self.sorted_keys:
            # No containers yet
            return None

        current_hash = self._hash(current_key)
        idx = self._find_key_index(current_hash)
        last_container_in_pool = None

        # 遍历副本，寻找能够存放当前键的容器
        for _ in range(self.replicas):
            container = self.ring[self.sorted_keys[idx]]
            if container in cur_container_pool:
                # only filter the avialble container
                last_container_in_pool = container
                if self.can_hold_key(container=container,
                                     key=current_key,
                                     cached_keys=container_cached_key[container]):
                    return container
            idx = (idx + 1) % len(self.sorted_keys)

        # 如果没有找到能够存放当前键的容器，则返回最后一个在池中的容器
        return last_container_in_pool

    def _find_key_index(self, h):
        for i, k in enumerate(self.sorted_keys):
            if h < k:
                return i
        return 0  # 当超出环的最大键时，返回到环的开始


if __name__ == "__main__":
    import random

    class Container:
        def __init__(self, name):
            self.name = name
            self.container = self

    # 为了可重复性，我们设置随机种子
    random.seed(42)

    # 初始化HashRing实例
    hash_ring = HashRing(replicas=3)

    # 添加初始容器
    initial_containers = [Container(f"container-{i}") for i in range(1, 4)]
    for container in initial_containers:
        hash_ring.add_container(container)

    # 生成随机键并映射到容器
    num_keys = 1000
    keys = [f"key-{i}" for i in range(num_keys)]
    initial_mapping = {key: hash_ring.get_container(key).name for key in keys}

    # 添加新容器
    new_containers = [Container(f"container-{i}") for i in range(4, 6)]
    for container in new_containers:
        hash_ring.add_container(container)

    # 重新映射键并检查一致性
    new_mapping = {key: hash_ring.get_container(key).name for key in keys}
    changed_mappings = {key: (initial_mapping[key], new_mapping[key])
                        for key in keys if initial_mapping[key] != new_mapping[key]}

    # 我们期望一些键的映射会发生变化，但大部分键应保持不变
    print(
        f"num of changed keys: {len(changed_mappings)}, it counts: {len(changed_mappings) / num_keys * 100}% of total")
