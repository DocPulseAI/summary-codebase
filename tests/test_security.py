import unittest
from src.github_client import GitHubClient


class TestSecurityFeatures(unittest.TestCase):
    def setUp(self):
        self.client = GitHubClient("owner", "repo", "ghp_FAKE_TOKEN_FOR_TESTING_ONLY")

    def test_sanitize_token_in_url(self):
        """Test that tokens in URLs are sanitized."""
        text = "fatal: repository 'https://x-access-token:ghp_FAKE_TOKEN_FOR_TESTING_ONLY@github.com/owner/repo.git' not found"
        sanitized = self.client._sanitize_log(text)

        self.assertNotIn("ghp_FAKE", sanitized)
        self.assertIn("***", sanitized)

    def test_sanitize_github_personal_token(self):
        """Test that GitHub personal access tokens are sanitized."""
        text = "Using token ghp_FAKE_TOKEN_FOR_TESTING_ONLY for authentication"
        sanitized = self.client._sanitize_log(text)

        self.assertNotIn("ghp_FAKE", sanitized)
        self.assertIn("***REDACTED_TOKEN***", sanitized)

    def test_sanitize_github_oauth_token(self):
        """Test that GitHub OAuth tokens are sanitized."""
        text = "Using token gho_FAKE_TOKEN_FOR_TESTING_ONLY for authentication"
        sanitized = self.client._sanitize_log(text)

        self.assertNotIn("gho_FAKE", sanitized)
        self.assertIn("***REDACTED_TOKEN***", sanitized)

    def test_sanitize_basic_auth_url(self):
        """Test that basic auth credentials in URLs are sanitized."""
        text = "Cloning into 'repo'...\nfatal: repository 'https://user:password@github.com/owner/repo.git' not found"
        sanitized = self.client._sanitize_log(text)

        self.assertNotIn("user:password", sanitized)
        self.assertIn("***@", sanitized)

    def test_sanitize_none_or_empty(self):
        """Test that None and empty strings are handled."""
        self.assertEqual(self.client._sanitize_log(None), None)
        self.assertEqual(self.client._sanitize_log(""), "")

    def test_sanitize_preserves_safe_content(self):
        """Test that safe content is not modified."""
        safe_text = "Successfully pushed to branch auto/docs/abc123"
        sanitized = self.client._sanitize_log(safe_text)

        self.assertEqual(safe_text, sanitized)


if __name__ == '__main__':
    unittest.main()
