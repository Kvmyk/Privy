import unittest
from unittest.mock import patch, MagicMock
from privy import status

class TestStatus(unittest.TestCase):

    @patch('privy.status.psutil')
    def test_get_cpu_info(self, mock_psutil):
        mock_psutil.cpu_percent.return_value = 15.5
        result = status.get_cpu_info()
        self.assertEqual(result, "15.5%")

    @patch('privy.status.psutil')
    def test_get_mem_info(self, mock_psutil):
        mock_mem = MagicMock()
        mock_mem.used = 1024 * 1024 * 500  # 500 MB
        mock_mem.total = 1024 * 1024 * 1024 * 8 # 8 GB
        mock_psutil.virtual_memory.return_value = mock_mem
        
        result = status.get_mem_info()
        self.assertEqual(result, "500MB / 8192MB")

    @patch('privy.status.requests.get')
    def test_get_ollama_status_online(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'models': [{'name': 'm1'}, {'name': 'm2'}]}
        mock_get.return_value = mock_response
        
        result = status.get_ollama_status()
        self.assertIn("Online (2 models)", result)

    @patch('privy.status.requests.get')
    def test_get_ollama_status_offline(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")
        result = status.get_ollama_status()
        self.assertIn("Offline", result)

if __name__ == '__main__':
    unittest.main()
