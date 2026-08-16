import http.client
import json
from urllib.request import Request, urlopen


_API = "https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
_UA = "octagon/0.1"


def fetch_stocktwits_messages(ticker: str, limit: int = 30, timeout: float = 10.0) -> str:
    url = _API.format(ticker=ticker)
    req = Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except (OSError, http.client.HTTPException, json.JSONDecodeError) as exc:
        return 'Unable to reach stocktwits'

    messages = data.get("messages", []) if isinstance(data, dict) else []
    if not messages:
        return f"no StockTwits messages found for ${ticker.upper()}"

    bullish = bearish = unlabeled = 0
    for m in messages[:limit]:
        entities = m.get("entities") or {}
        sentiment_obj = entities.get("sentiment") or {}
        sentiment = sentiment_obj.get("basic") if isinstance(sentiment_obj, dict) else None

        if sentiment == "Bullish":
            bullish += 1
        elif sentiment == "Bearish":
            bearish += 1
        else:
            unlabeled += 1

    total = bullish + bearish + unlabeled
    bull_pct = round(100 * bullish / total) if total else 0
    bear_pct = round(100 * bearish / total) if total else 0
    summary = (
        f"Bullish: {bullish} ({bull_pct}%) · "
        f"Bearish: {bearish} ({bear_pct}%) · "
        f"Unlabeled: {unlabeled} · "
        f"Total: {total} most-recent messages"
    )
    return summary + "\n\n"


if __name__ == "__main__":
    result = fetch_stocktwits_messages('MSFT')
    print(result)