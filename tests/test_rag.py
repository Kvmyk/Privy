import unittest
import os
import shutil
import tempfile
from privy import rag

class TestRag(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for docs
        self.test_dir = tempfile.mkdtemp()
        rag.DOCS_DIR = self.test_dir

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self.test_dir)

    def test_search_docs_found(self):
        # Create a dummy file
        file_path = os.path.join(self.test_dir, "test_doc.txt")
        with open(file_path, "w") as f:
            f.write("This is a secret document about aliens.")
        
        result = rag.search_docs("aliens")
        self.assertIn("--- DOCUMENT: test_doc.txt ---", result)
        self.assertIn("This is a secret document about aliens.", result)

    def test_search_docs_not_found(self):
        file_path = os.path.join(self.test_dir, "test_doc.txt")
        with open(file_path, "w") as f:
            f.write("Just boring stuff.")
        
        result = rag.search_docs("aliens")
        self.assertEqual(result, "")

    def test_search_docs_no_dir(self):
        rag.DOCS_DIR = "/non/existent/path/12345"
        result = rag.search_docs("anything")
        self.assertEqual(result, "")

if __name__ == '__main__':
    unittest.main()
