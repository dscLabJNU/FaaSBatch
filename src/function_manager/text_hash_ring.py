# 完整的一致性哈希代码，包含测试代码在 main 函数中

import hashlib
import random
from bisect import bisect_left, insort

class ConsistentHash:
    def __init__(self, num_virtual_nodes=100):
        self.num_virtual_nodes = num_virtual_nodes
        self.nodes = []  # 存放所有节点（包括虚拟节点）的哈希值
        self.node_map = {}  # 存放虚拟节点和物理节点的映射关系

    def _hash(self, key):
        """使用 md5 算法计算哈希值"""
        m = hashlib.md5()
        m.update(key.encode('utf-8'))
        return int(m.hexdigest(), 16)

    def add_node(self, node):
        """添加一个物理节点及其对应的虚拟节点"""
        for i in range(self.num_virtual_nodes):
            virtual_node = f"{node}#{i}"
            hash_value = self._hash(virtual_node)
            insort(self.nodes, hash_value)  # 保持 nodes 列表有序
            self.node_map[hash_value] = node

    def remove_node(self, node):
        """删除一个物理节点及其对应的虚拟节点"""
        for i in range(self.num_virtual_nodes):
            virtual_node = f"{node}#{i}"
            hash_value = self._hash(virtual_node)
            self.nodes.remove(hash_value)
            del self.node_map[hash_value]

    def get_node(self, key):
        """获取一个 key 应该路由到的节点"""
        if not self.nodes:
            return None
        hash_value = self._hash(key)
        idx = bisect_left(self.nodes, hash_value) % len(self.nodes)
        return self.node_map[self.nodes[idx]]


def main():
    # 初始化一个一致性哈希对象，每个物理节点有 100 个虚拟节点
    ch = ConsistentHash(num_virtual_nodes=10)
    
    # 添加 100 个物理节点
    for i in range(1, 101):
        ch.add_node(f"node{i}")

    # 生成 2000 个测试键
    test_keys = [f"key{i}" for i in range(1, 2001)]

    # 生成偏斜的访问模式
    skewed_keys = test_keys[:200] * 8 + test_keys[200:] * 2

    # 测试 key 的分布情况
    key_distribution = {f"node{i}": 0 for i in range(1, 101)}

    for key in skewed_keys:
        node = ch.get_node(key)
        if node:  # 防止节点已被删除
            key_distribution[node] += 1

    # 输出分布情况
    print("Key distribution:", key_distribution)

    # 计算一些分布的统计信息
    avg_keys_per_node = sum(key_distribution.values()) / len(key_distribution)
    max_keys_per_node = max(key_distribution.values())
    min_keys_per_node = min(key_distribution.values())

    print(f"Average keys per node: {avg_keys_per_node}")
    print(f"Max keys per node: {max_keys_per_node}")
    print(f"Min keys per node: {min_keys_per_node}")

# 如果直接运行这个脚本，就执行 main 函数进行测试
if __name__ == "__main__":
    main()
