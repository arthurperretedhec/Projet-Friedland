"""Lightweight external-data tests. Run python -m unittest discover -s tests -v."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from validate_dataset import validate
class TestDataset(unittest.TestCase):
    def test_core_data(self):
        root=Path(__file__).resolve().parents[1]
        self.assertTrue(validate(root/'app/backend/data'))
if __name__=='__main__':unittest.main()
