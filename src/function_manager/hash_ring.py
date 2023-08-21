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

    def get_container(self, awsBoto3_key):
        if not self.sorted_keys:
            return None
        h = self._hash(awsBoto3_key)
        idx = self._find_key_index(h)
        container = self.ring[self.sorted_keys[idx]]
        self.mapping[awsBoto3_key] = container.container.name
        print(
            f"AwsBoto3Key -> container: {awsBoto3_key} -> { self.mapping[awsBoto3_key]}")
        return container

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
