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
            virtual_node_key = self._hash(f"{container}:{i}")
            self.ring[virtual_node_key] = container
            self.sorted_keys.append(virtual_node_key)
        self.sorted_keys.sort()

    def remove_container(self, container):
        for i in range(self.replicas):
            virtual_node_key = self._hash(f"{container}:{i}")
            del self.ring[virtual_node_key]
            self.sorted_keys.remove(virtual_node_key)

    def get_container(self, awsBoto3_key):
        if not self.sorted_keys:
            return None
        h = self._hash(awsBoto3_key)
        idx = self._find_key_index(h)
        container = self.ring[self.sorted_keys[idx]]
        self.mapping[awsBoto3_key] = container.container.name
        print(f"AwsBoto3Key -> container: {awsBoto3_key} -> { self.mapping[awsBoto3_key]}")
        return container

    def _find_key_index(self, h):
        for i, k in enumerate(self.sorted_keys):
            if h < k:
                return i
        return 0
    