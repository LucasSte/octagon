from collections.abc import Callable
from datetime import date
from urllib.parse import quote_plus

import feedparser
from dateutil.relativedelta import relativedelta
from openai import OpenAI
from pydantic.dataclasses import dataclass

from octagon.dashboard.log_type import LogType
from octagon.tools.tool_definition import ToolDefinition


@dataclass
class RssSource:
    website: str
    name: str
    native_rss: list[str]


ECONOMIST_RSS = [
    "https://www.economist.com/finance-and-economics/rss.xml",
    "https://www.economist.com/international/rss.xml",
    "https://www.economist.com/business/rss.xml",
    "https://www.economist.com/united-states/rss.xml",
]

FT_RSS = [
    "https://www.ft.com/markets?format=rss",
    "https://www.ft.com/global-economy?format=rss",
    "https://www.ft.com/emerging-markets?format=rss",
    "https://www.ft.com/world?format=rss",
    "https://www.ft.com/companies?format=rss",
    "https://www.ft.com/financials?format=rss",
    "https://www.ft.com/technology-sector?format=rss",
]

TECH_CRUNCH_RSS = [
    "https://techcrunch.com/feed",
]

SOURCES = {
    "economist": RssSource("economist.com", "The Economist", ECONOMIST_RSS),
    "ft": RssSource("ft.com", "Financial Times", FT_RSS),
    "tech_crunch": RssSource("techcrunch.com", "Tech Crunch", TECH_CRUNCH_RSS),
}


def fetch_from_rss(query: str, rss_source: list):
    results = []

    for url in rss_source:
        feed = feedparser.parse(url)
        for e in feed.entries:
            if query.lower() in (e.title + e.get("summary", "")).lower():
                results.append(f"{e.title}: {e.get('summary', '')}")

    return results


def fetch_from_google_rss(query, source: RssSource, months_ago):
    query = f"{query} site:{source.website}"
    if months_ago is not None:
        cutoff = date.today() - relativedelta(months=months_ago)
        query += f" before:{cutoff.isoformat()}"

    url = f"https://news.google.com/rss/search?q={quote_plus(query)}"
    feed = feedparser.parse(url)

    len_to_trim = len(source.name) + 3
    entries = [e.title[:-len_to_trim] for e in feed.entries]
    return entries


def fetch_from_all_rss(query, source: RssSource, months_ago):
    results = fetch_from_rss(query, source.native_rss) + fetch_from_google_rss(
        query, source, months_ago
    )
    return results


def fetch_headlines(query, months_ago):
    economits_source = SOURCES["economist"]
    economist = fetch_from_all_rss(query, economits_source, months_ago)
    economist_string = "\n\nHeadlines from The Economist:\n\n" + "\n".join(economist)

    ft_source = SOURCES["ft"]
    ft = fetch_from_all_rss(query, ft_source, months_ago)
    ft_string = "\n\nHeadlines from Financial Times:\n\n" + "\n".join(ft)

    tech_crunch_source = SOURCES["tech_crunch"]
    tech_crunch = fetch_from_all_rss(query, tech_crunch_source, months_ago)
    tech_crunch_string = "\n\nHeadlines from Tech Crunch:\n\n" + "\n".join(tech_crunch)

    return economist_string + ft_string + tech_crunch_string


class NewsHeadlines(ToolDefinition):
    def __init__(self, client: OpenAI, model: str) -> None:
        self.client = client
        self.log_callback = None
        self.model = model

    def summarize_headlines(self, query):
        query = query.lower()
        prompt = (
            "Given the following headlines, pick the five most important ones, "
            "select three keywords to describe them, and summarize the scenario "
            f"for the given query used to fetch them: {query}\n\n"
        )

        prompt += fetch_headlines(query, None)

        content = [{"type": "text", "text": prompt}]
        history = [
            {
                "role": "user",
                "content": content,
            }
        ]

        try:
            chat_response = self.client.chat.completions.create(
                model=self.model,
                messages=history,
                max_tokens=20000,
                temperature=0.7,
                top_p=0.95,
                extra_body={
                    "top_k": 20,
                },
            )
        # ruff: noqa: BLE001
        except Exception as e:
            if self.log_callback is not None:
                self.log_callback(LogType.ERROR, f"Fail to fetch news: {e}")
            return "Failed to fetch news"

        response_message = chat_response.choices[0].message

        if response_message.content is not None and len(response_message.content) > 0:
            return response_message.content
        else:
            return "No headlines found"

    def description(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "summarize_headlines",
                    "description": "Fetches news headlines for a company and summarizes the information found. News might give hints about future stock performance.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Name of the company to search for (e.g. nvidia, apple, boeing).",
                            },
                        },
                        "required": ["query"],
                    },
                    "returns": {
                        "type": "string",
                        "description": "The headlines found, three keywords and a summary.",
                    },
                },
            }
        ]

    def dispatch_dictionary(self) -> dict[str, Callable]:
        return {"summarize_headlines": self.summarize_headlines}

    def register_log_callback(self, callback: Callable[[LogType, str], None]):
        self.log_callback = callback
