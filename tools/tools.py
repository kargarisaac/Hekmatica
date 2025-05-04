import html
import logging
import requests

from langchain_community.tools import DuckDuckGoSearchRun, DuckDuckGoSearchResults

# Fallback: optionally, implement a simple HTML query to DuckDuckGo if library not installed (not shown for brevity)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SearchTool")


logger = logging.getLogger("PriceTool")

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

def web_search(query: str, max_results: int = 5):
    """Search the web for the query and return a list of dictionaries, each with 'content' and 'link'."""
    results = [] # Now stores list of dicts
    try:
        # Use DuckDuckGoSearchResults with list output format
        search_list_tool = DuckDuckGoSearchResults(output_format="list")
        raw_results = search_list_tool.invoke(query) 
        
        # Limit results manually
        raw_results = raw_results[:max_results]

    except Exception as e:
        logger.error(f"Search query failed: {e}")
        return results # Return empty list on failure

    if not raw_results:
        return results # Return empty list if no results

    for item in raw_results:
        # Ensure item is a dictionary before proceeding
        if not isinstance(item, dict):
            logger.warning(f"Skipping unexpected search result format: {item}")
            continue
            
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        link = item.get("link", "") # Get the link

        title = html.unescape(title)
        snippet = html.unescape(snippet)
        
        content = title + ": " + snippet if snippet else title
        content = content.strip()
        
        if content and link: # Only add if both content and link are present
            results.append({'content': content, 'link': link})
            
    return results


def get_current_price(coin_name: str):
    """Fetch the current price (USD) of the given cryptocurrency. Returns a string like '$12345.67' or None if not found."""
    coin_key = coin_name.strip().lower()
    # Use mapping to find CoinGecko ID
    coin_id = COIN_ID_MAP.get(coin_key, coin_key)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
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