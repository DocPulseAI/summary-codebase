import unittest
from unittest.mock import MagicMock, patch
from src.github_client import GitHubClient

class TestGitHubClient(unittest.TestCase):
    def setUp(self):
        self.client = GitHubClient("owner", "repo", "token")

    @patch("src.github_client.requests.post")
    def test_create_pr(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"number": 123}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        pr = self.client.create_pr("head", "base", "Title", "Body")
        self.assertEqual(pr["number"], 123)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("Title", kwargs["json"]["title"])

    @patch("src.github_client.requests.get")
    def test_find_open_pr(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"number": 123}]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        pr = self.client.find_open_pr("head", "base")
        self.assertEqual(pr["number"], 123)

    @patch("src.github_client.subprocess.run")
    def test_checkout_and_push(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = " M file" # changes detected
        
        self.client.checkout_and_push_files("branch", ["file1"], "msg")
        
        # Verify call sequence: config, config, checkout, add, status, commit, push
        # This is loose, but ensures 'push' was called eventually
        push_called = False
        for call in mock_run.call_args_list:
            args = call[0][0]
            if args[0] == "git" and args[1] == "push":
                push_called = True
        self.assertTrue(push_called)
