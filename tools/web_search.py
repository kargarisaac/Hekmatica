from langchain_community.tools.tavily_search import TavilySearchResults
import html
from loguru import logger
import os  # Import os to access environment variables
from tavily import TavilyClient

# Ensure TAVILY_API_KEY is set (optional, but good practice)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    logger.warning(
        "TAVILY_API_KEY environment variable not set. Tavily search and extract may fail."
    )
# Instantiate the client once if the key exists
tavily_client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None


def web_search(query: str, max_results: int = 5):
    """Search the web using Tavily for the query and return a list of dictionaries, each with 'content' and 'link'."""
    results = []  # Stores list of dicts {'content': '...', 'link': '...'}
    try:
        # Instantiate TavilySearchResults
        # max_results is handled directly by the tool
        search_tool = TavilySearchResults(max_results=max_results)
        # Tavily returns a list of documents (dictionaries) directly
        raw_results = search_tool.invoke(query)

        # No need to limit results manually, Tavily does it via max_results

    except Exception as e:
        logger.error(f"Tavily search query failed: {e}")
        return results  # Return empty list on failure

    if not raw_results:
        logger.info(f"No results found for query: {query}")
        return results  # Return empty list if no results

    # Process Tavily results
    for item in raw_results:
        # Ensure item is a dictionary before proceeding
        if not isinstance(item, dict):
            logger.warning(f"Skipping unexpected search result format: {item}")
            continue

        # Tavily returns 'content' and 'url'
        content = item.get("content", "")
        link = item.get("url", "")  # Use 'url' key from Tavily results

        # Optional: Unescape HTML entities if needed, though Tavily often provides clean text
        content = html.unescape(content)
        content = content.strip()

        if content and link:  # Only add if both content and link are present
            # Keep the desired output format {'content': ..., 'link': ...}
            results.append({"content": content, "link": link})
        else:
            logger.warning(f"Skipping result with missing content or link: {item}")

    return results


# --- New Function: extract_content_from_url ---
def extract_content_from_url(url: str) -> str | None:
    """
    Extracts the main content from a given URL using Tavily's extract API.

    Args:
        url: The URL to extract content from.

    Returns:
        The extracted content as a string, or None if extraction fails or the client isn't available.
    """
    if not tavily_client:
        logger.error("Tavily client not initialized. Set TAVILY_API_KEY.")
        return None

    logger.info(f"Attempting to extract content from URL: {url}")
    try:
        # Use the extract method from TavilyClient
        # See: https://docs.tavily.com/sdk/python/quick-start
        # And: https://docs.tavily.com/documentation/api-reference/endpoint/extract
        response = tavily_client.extract(
            urls=[url],  # API expects a list of URLs
            include_raw_content=True,  # Get the main textual content
            # include_images=False, # Default is false
            # extract_depth="basic" # Default is basic
        )

        # Response is a list of results, one for each URL provided
        if response and isinstance(response, list) and len(response) > 0:
            result_dict = response[0]  # Get the result for the first (only) URL
            if result_dict.get("status") == "success" and "raw_content" in result_dict:
                logger.success(f"Successfully extracted content from {url}")
                return result_dict["raw_content"]
            elif "error" in result_dict:
                logger.error(
                    f"Tavily extraction failed for {url}: {result_dict.get('error')}"
                )
                return None
            else:
                logger.warning(
                    f"Tavily extraction returned unexpected structure for {url}: {result_dict}"
                )
                return None
        elif response and isinstance(response, dict) and response.get("failed_results"):
            # Handle cases where the API might return failed_results directly (less common with SDK)
            failed = response["failed_results"][0]
            logger.error(
                f"Tavily extraction failed for {failed.get('url', url)}: {failed.get('error', 'Unknown error')}"
            )
            return None
        else:
            logger.warning(
                f"Received unexpected empty or invalid response from Tavily extract for {url}: {response}"
            )
            return None

    except Exception as e:
        logger.error(f"Exception during Tavily content extraction for {url}: {e}")
        return None


if __name__ == "__main__":
    # --- Example for web_search ---
    search_query = "Latest advancements in AI fairness"
    print(f"Searching for: {search_query}")
    search_results = web_search(search_query)
    first_url_to_extract = None
    if search_results:
        print("\nSearch Results:")
        for i, result in enumerate(search_results):
            print(
                f"{i + 1}. Content: {result['content'][:150]}..."
            )  # Print snippet of content
            print(f"   Link: {result['link']}")
            if i == 0:  # Get the first URL for the extraction example
                first_url_to_extract = result["link"]
    else:
        print("No search results found or search failed.")

    print("\n" + "=" * 20 + "\n")  # Separator

    # --- Example for extract_content_from_url ---
    if first_url_to_extract:
        print(
            f"Attempting to extract content from first result: {first_url_to_extract}"
        )
        extracted_content = extract_content_from_url(first_url_to_extract)
        if extracted_content:
            print("\nExtracted Content (first 500 chars):")
            print(extracted_content[:500] + "...")
        else:
            print("Failed to extract content.")
    else:
        print("Skipping content extraction example as no search results were found.")

    # --- Example for extract_content_from_url with a direct URL ---
    print("\n" + "=" * 20 + "\n")  # Separator
    direct_url = "https://en.wikipedia.org/wiki/Large_language_model"
    print(f"Attempting to extract content directly from: {direct_url}")
    extracted_content_direct = extract_content_from_url(direct_url)
    if extracted_content_direct:
        print("\nExtracted Content (first 500 chars):")
        print(extracted_content_direct[:500] + "...")
    else:
        print("Failed to extract content.")
