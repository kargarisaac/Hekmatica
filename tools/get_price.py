import requests
from loguru import logger

# Common mappings for coin names to CoinGecko IDs
COIN_ID_MAP = {
    "bitcoin": "bitcoin",
    "btc": "bitcoin",
    "ethereum": "ethereum",
    "eth": "ethereum",
    "litecoin": "litecoin",
    "ltc": "litecoin",
    "solana": "solana",
    "sol": "solana",
    "dogecoin": "dogecoin",
    "doge": "dogecoin",
    # Add more mappings as needed
}


def get_current_price(coin_name: str):
    """Fetch the current price (USD) of the given cryptocurrency. Returns a string like '$12345.67' or None if not found."""
    coin_key = coin_name.strip().lower()
    # Use mapping to find CoinGecko ID
    coin_id = COIN_ID_MAP.get(coin_key, coin_key)
    url = (
        f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    )
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Price API request failed for {coin_name}: {e}")
        return None
    data = resp.json()
    if coin_id in data and "usd" in data[coin_id]:
        price = data[coin_id]["usd"]
        # Format the price with comma and two decimals
        price_str = f"${price:,.2f}"
        return price_str
    else:
        logger.info(f"Price for {coin_name} not found in API response.")
        return None


if __name__ == "__main__":
    print(get_current_price("bitcoin"))
    print(get_current_price("ethereum"))
    print(get_current_price("litecoin"))
    print(get_current_price("solana"))
    print(get_current_price("dogecoin"))
