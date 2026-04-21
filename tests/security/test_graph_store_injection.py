import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Mock EVERYTHING in src.knowledge_graph except graph_store
sys.modules['src.knowledge_graph.builder'] = MagicMock()
sys.modules['src.knowledge_graph.analytics'] = MagicMock()
sys.modules['src.knowledge_graph.data_mining'] = MagicMock()
sys.modules['src.knowledge_graph.entity_resolver'] = MagicMock()
sys.modules['src.knowledge_graph.graph_builder'] = MagicMock()
sys.modules['src.knowledge_graph.graph_refiner'] = MagicMock()
sys.modules['src.knowledge_graph.queries'] = MagicMock()
sys.modules['src.knowledge_graph.visualizer'] = MagicMock()

# Mock external dependencies
for mod in ['kuzu', 'rich', 'rich.console', 'dotenv']:
    sys.modules[mod] = MagicMock()

# Now import GraphStore directly from the file to avoid __init__.py issues
import importlib.util
spec = importlib.util.spec_from_file_location("graph_store", "src/knowledge_graph/graph_store.py")
graph_store_mod = importlib.util.module_from_spec(spec)
sys.modules["graph_store"] = graph_store_mod
spec.loader.exec_module(graph_store_mod)

GraphStore = graph_store_mod.GraphStore

class TestGraphStoreSecurity(unittest.TestCase):
    def setUp(self):
        self.db_path = Path("test_db")
        # Prevent _init_schema from running during init to avoid noise
        with patch.object(GraphStore, '_init_schema'):
            self.store = GraphStore(self.db_path)
            self.store.conn = MagicMock()

    def test_create_node_table_injection_name(self):
        with self.assertRaises(ValueError):
            self.store._create_node_table("Faculty; DROP TABLE Faculty", {"name": "STRING"}, "name")

    def test_create_node_table_injection_schema_key(self):
        with self.assertRaises(ValueError):
            self.store._create_node_table("Faculty", {"name); DROP TABLE Faculty; --": "STRING"}, "name")

    def test_create_node_table_injection_schema_type(self):
        with self.assertRaises(ValueError):
            self.store._create_node_table("Faculty", {"name": "STRING); DROP TABLE Faculty; --"}, "name")

    def test_create_node_table_injection_primary_key(self):
        with self.assertRaises(ValueError):
            self.store._create_node_table("Faculty", {"name": "STRING"}, "name); DROP TABLE Faculty; --")

    def test_create_rel_table_injection_name(self):
        with self.assertRaises(ValueError):
            self.store._create_rel_table("Authored; DROP TABLE Faculty", "Faculty", "Paper")

    def test_create_rel_table_injection_src(self):
        with self.assertRaises(ValueError):
            self.store._create_rel_table("Authored", "Faculty; DROP TABLE Faculty", "Paper")

    def test_create_rel_table_injection_dst(self):
        with self.assertRaises(ValueError):
            self.store._create_rel_table("Authored", "Faculty", "Paper; DROP TABLE Faculty")

    def test_create_rel_table_injection_property_key(self):
        with self.assertRaises(ValueError):
            self.store._create_rel_table("Authored", "Faculty", "Paper", {"weight); DROP TABLE Faculty; --": "INT64"})

    def test_create_rel_table_injection_property_type(self):
        with self.assertRaises(ValueError):
            self.store._create_rel_table("Authored", "Faculty", "Paper", {"weight": "INT64); DROP TABLE Faculty; --"})

    def test_valid_inputs(self):
        # Should not raise any error
        self.store._create_node_table("Faculty", {"name": "STRING", "age": "INT64"}, "name")
        self.store._create_rel_table("Authored", "Faculty", "Paper", {"weight": "INT64"})

if __name__ == '__main__':
    unittest.main()
