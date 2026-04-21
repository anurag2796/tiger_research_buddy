## 2024-05-18 - String Concatenation in Graph Traversal Hot Loops
**Learning:** The `EntityExtractor` uses a naive lexical matching algorithm that loops over every single node in the graph (which can be 100k+ entries). Inside this loop, it was dynamically allocating a padded query string `f" {query_lower} "` on every single iteration.
**Action:** When performing full-scan iterations over the Knowledge Graph index, ensure all invariant operations (like padding strings or compiling regexes) are hoisted out of the `for` loop to prevent excessive memory allocations.
