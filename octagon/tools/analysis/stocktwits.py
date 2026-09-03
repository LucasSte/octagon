import json
from urllib.request import Request, urlopen


def stocktwits_sentiments(ticker):
    url = f'https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json'
    req = Request(url, headers={"User-Agent": "octagon/0.1", "Accept": "application/json"})
    try:
        with urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
    # ruff: noqa: BLE001
    except Exception:
        return 'Unable to reach stocktwits'

    messages = data.get('messages', []) if isinstance(data, dict) else []
    if not messages:
        return f'No stocktwits messages found for ticker {ticker}'

    bullish = 0
    bearish = 0
    unlabeled = 0
    for mes in messages[:50]:
        entities = mes.get('entities') or {}
        sentiment = entities.get('sentiment') or {}
        label = sentiment.get('basic') if isinstance(sentiment, dict) else None

        if label == "Bullish":
            bullish += 1
        elif label == "Bearish":
            bearish += 1
        else:
            unlabeled += 1

    total = bullish + bearish + unlabeled
    bullish_percent = round(100 * bullish / total) if total else 0
    bearish_percent = round(100 * bearish / total) if total else 0
    unlabeled_percent = round(100 * unlabeled / total) if total else 0

    formatted_message = f'Stocktwits sentiment analysis from {total} most recent message:\n\n'
    formatted_message += f'Bullish: {bullish} ({bullish_percent}%)\n'
    formatted_message += f'Bearish: {bearish} ({bearish_percent}%)\n'
    formatted_message += f'Unlabaled: {unlabeled} ({unlabeled_percent}%)'

    return formatted_message