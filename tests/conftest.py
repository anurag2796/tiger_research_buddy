import sys
from unittest.mock import MagicMock

# Manual mock for modules
mock_modules = [
    'kuzu', 'rich', 'rich.console', 'dotenv', 'networkx', 'matplotlib',
    'matplotlib.pyplot', 'pandas', 'numpy', 'sklearn',
    'sklearn.feature_extraction', 'sklearn.feature_extraction.text',
    'sklearn.decomposition', 'sklearn.cluster', 'scipy',
    'scipy.spatial', 'scipy.spatial.distance', 'mlxtend',
    'mlxtend.frequent_patterns'
]

for mod in mock_modules:
    sys.modules[mod] = MagicMock()
