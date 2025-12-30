import unittest
from privy import main

class TestMain(unittest.TestCase):
    def test_detect_intent_coder(self):
        queries = [
            "Please write code for a calculator",
            "create script to backup files",
            "napisz kod w pythonie"
        ]
        for q in queries:
            self.assertEqual(main.detect_intent(q), "coder")

    def test_detect_intent_admin(self):
        queries = [
            "Check disk space",
            "List files",
            "How are you?"
        ]
        for q in queries:
            self.assertEqual(main.detect_intent(q), "admin")

if __name__ == '__main__':
    unittest.main()
