import unittest

from openai import OpenAI

from octagon.tools.analysis.news_analysis import NewsHeadlines


class TestHeadlines(unittest.TestCase):
    def test_function(self):
        client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")
        tool = NewsHeadlines(client, "qwen/qwen3.8-27b")
        result = tool.summarize_headlines("apple")
        print(result)


if __name__ == "__main__":
    unittest.main()
