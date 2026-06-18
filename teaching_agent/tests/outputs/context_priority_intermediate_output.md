**Explanation**
1. Definition and purpose: A hash table is a data structure that stores key-value pairs in an array using a hash function to map keys to indices of the array. Its primary purpose is to provide efficient lookup, insertion, and deletion operations.
2. How it works internally: The hash index formula `index = hash(key) % table_size` is used to determine the index at which a key-value pair should be stored. When a collision occurs (i.e., two keys hash to the same index), collision resolution strategies such as open addressing (linear probing) or separate chaining are employed.
3. Trade-offs and when to use it: Hash tables offer O(1) average performance for lookup, insertion, and deletion operations, but this can degrade to O(n) in the worst case when many collisions cluster. To maintain O(1) average performance, the load factor α (number of entries / table size) should be kept below 0.7. Hash tables are suitable for applications where fast lookup and insertion are crucial, such as caching, database indexing, and set operations.
4. Common pitfalls and how to avoid them: One common pitfall is allowing the load factor to exceed 0.7, which can lead to poor performance. To avoid this, the table size can be dynamically resized when the load factor threshold is reached, as is done in Python's built-in dict with a load factor threshold of approximately 2/3.

**Notes**
### Key Properties
* Hash function: maps keys to indices of the array
* Load factor α: number of entries / table size
* Collision resolution strategies: open addressing (linear probing), separate chaining
### Complexity/Performance Characteristics
* Average performance: O(1) for lookup, insertion, and deletion
* Worst-case performance: O(n) when many collisions cluster
### Important Variants or Alternatives
* Open addressing (linear probing)
* Separate chaining
* Python's built-in dict (uses open addressing with dynamic resizing)

**Example**
```python
# Create a simple hash table with open addressing (linear probing)
class HashTable:
    def __init__(self, size):
        self.size = size
        self.table = [None] * size

    def _hash(self, key):
        # Simple hash function: hash(key) % table_size
        return hash(key) % self.size

    def insert(self, key, value):
        index = self._hash(key)
        # Linear probing for collision resolution
        while self.table[index] is not None:
            index = (index + 1) % self.size
        self.table[index] = (key, value)

    def lookup(self, key):
        index = self._hash(key)
        # Linear probing for collision resolution
        while self.table[index] is not None:
            if self.table[index][0] == key:
                return self.table[index][1]
            index = (index + 1) % self.size
        return None

# Create a hash table and insert some key-value pairs
hash_table = HashTable(10)
hash_table.insert("key1", "value1")
hash_table.insert("key2", "value2")

# Lookup a key
print(hash_table.lookup("key1"))  # Output: value1
```