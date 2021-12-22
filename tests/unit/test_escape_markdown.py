import unittest
from telegram.utils.helpers import escape_markdown



class TestMarkdown(unittest.TestCase):

    def test_markdown_escape_with_backslash_parenthesis(self):
        sut = 'モナ\\(//∇//)\\'
        expected = 'モナ\\\\\\(//∇//\\)\\\\'    # This is valid markdown escape
        result = escape_markdown(sut.replace('\\', '\\\\'), version=2)
        self.assertEqual(result, expected)

    def test_markdown_escape_with_backslash_consecutive(self):
        sut = '[Fans Vote] Raiden Shogun\\\\\\雷電将軍'
        expected = '\\[Fans Vote\\] Raiden Shogun\\\\\\\\\\\\雷電将軍'  # This is also valid markdown escape
        result = escape_markdown(sut.replace('\\', '\\\\'), version=2)
        self.assertEqual(result, expected)

    def test_markdown_escape_with_backslash_only(self):
        sut = '/ \\'
        expected = '/ \\\\'
        result = escape_markdown(sut.replace('\\', '\\\\'), version=2)
        self.assertEqual(result, expected)
