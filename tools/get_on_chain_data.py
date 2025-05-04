import requests
import json
from datetime import datetime, timedelta

# Base URL for the Coin Metrics Community API
COMMUNITY_API_URL = "https://community-api.coinmetrics.io/v4"


# --- Helper Function to make API calls ---
def _make_api_request(endpoint: str, params: dict) -> dict:
    """Makes a GET request to a Coin Metrics API endpoint."""
    try:
        response = requests.get(
            f"{COMMUNITY_API_URL}{endpoint}", params=params, timeout=30
        )
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Request Error for {endpoint}: {e}")
        return {"error": str(e)}
    except json.JSONDecodeError as e:
        print(f"API JSON Decode Error for {endpoint}: {e}")
        print(f"Response text: {response.text}")
        return {
            "error": "Failed to decode JSON response",
            "response_text": response.text,
        }


# --- 1) Function for Timeseries Asset Metrics ---
def get_asset_metrics(
    asset: str,
    metrics: list,
    start_time: str = None,
    end_time: str = None,
    frequency: str = "1d",
    page_size: int = 1000,  # Default to a larger page size for timeseries
    paging_from: str = "start",
) -> dict:
    """
    Fetches timeseries data for specified metrics for a given asset.
    Ref: https://docs.coinmetrics.io/api/v4/#tag/Timeseries/operation/getTimeseriesAssetMetrics
    """
    print(f"Fetching asset metrics for {asset}...")
    params = {
        "assets": asset,
        "metrics": ",".join(metrics),
        "frequency": frequency,
        "page_size": page_size,
        "paging_from": paging_from,
    }
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time

    # Note: This function currently only fetches the first page.
    # Implement pagination handling using 'next_page_token' if needed for longer time ranges.
    data = _make_api_request("/timeseries/asset-metrics", params)
    print(f"Finished fetching asset metrics for {asset}.")
    return data


# --- 2) Function for Chain Monitor Transaction Tracker ---
def get_transaction_tracker_info(
    asset: str,
    page_size: int = 100,  # Get recent transactions by default
    start_time: str = None,
    end_time: str = None,
    paging_from: str = "end",  # Default to get the most recent first
) -> dict:
    """
    Fetches status updates for recent transactions for the specified asset.
    Ref: https://docs.coinmetrics.io/api/v4/#tag/Chain-Monitor-tools/operation/getTxTracker

    Note: Parameters like 'addresses', 'replacements_for_txids' are BTC-only
          and not used in this general function.
    """
    print(f"Fetching transaction tracker info for {asset}...")
    params = {
        "page_size": page_size,
        "paging_from": paging_from,
    }
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time

    endpoint = f"/blockchain/{asset}/transaction-tracker"

    # Note: This function currently only fetches the first page.
    # Implement pagination handling using 'next_page_token' if needed.
    data = _make_api_request(endpoint, params)
    print(f"Finished fetching transaction tracker info for {asset}.")
    return data


# --- 3) Main Function to Aggregate Data ---
def get_comprehensive_on_chain_data(
    asset_name: str,
    metrics_list: list = None,
    timeseries_start_time: str = None,
    timeseries_end_time: str = None,
    tracker_start_time: str = None,
    tracker_end_time: str = None,
    frequency: str = "1d",
) -> dict:
    """
    Fetches comprehensive on-chain data for a given asset by calling
    specific Coin Metrics API functions.

    Args:
        asset_name: The asset identifier (e.g., 'btc', 'eth').
        metrics_list: Optional list of asset metrics to fetch. Defaults to a standard set.
        timeseries_start_time: Optional start time for asset metrics (YYYY-MM-DD). Defaults to 30 days ago.
        timeseries_end_time: Optional end time for asset metrics (YYYY-MM-DD). Defaults to today.
        tracker_start_time: Optional start time for transaction tracker (YYYY-MM-DDTHH:MM:SSZ). Defaults to None.
        tracker_end_time: Optional end time for transaction tracker (YYYY-MM-DDTHH:MM:SSZ). Defaults to None.
        frequency: Frequency for timeseries data ('1d', '1h', etc.).

    Returns:
        A dictionary containing the fetched data.
    """
    print(f"\n--- Starting comprehensive data fetch for {asset_name.upper()} ---")

    # Set default metrics if none provided
    if metrics_list is None:
        metrics_list = [
            "AdrActCnt",  # Active Addresses Count
            "TxCnt",  # Transaction Count
            "FeeTotNtv",  # Total Fees in Native Units
            "SplyCur",  # Current Supply
            "NVTAdj",  # Adjusted NVT Ratio
            "BlkCnt",  # Block Count
            "DiffMean",  # Mean Difficulty (if applicable)
            "PriceUSD",  # Price in USD (for context)
        ]

    # Set default time range for timeseries (last 30 days) if not provided
    if timeseries_start_time is None and timeseries_end_time is None:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        timeseries_start_time = start_date.strftime("%Y-%m-%d")
        timeseries_end_time = end_date.strftime("%Y-%m-%d")
        print(
            f"Defaulting timeseries range: {timeseries_start_time} to {timeseries_end_time}"
        )

    # Fetch Asset Metrics
    asset_metrics_data = get_asset_metrics(
        asset=asset_name,
        metrics=metrics_list,
        start_time=timeseries_start_time,
        end_time=timeseries_end_time,
        frequency=frequency,
    )

    # Fetch Transaction Tracker Info
    # Note: Tracker uses more precise timestamps if needed, but defaults work
    transaction_tracker_data = get_transaction_tracker_info(
        asset=asset_name, start_time=tracker_start_time, end_time=tracker_end_time
    )

    print(f"--- Finished comprehensive data fetch for {asset_name.upper()} ---\n")

    # Combine results
    comprehensive_data = {
        "asset": asset_name,
        "query_parameters": {
            "asset_metrics": {
                "metrics": metrics_list,
                "start_time": timeseries_start_time,
                "end_time": timeseries_end_time,
                "frequency": frequency,
            },
            "transaction_tracker": {
                "start_time": tracker_start_time,
                "end_time": tracker_end_time,
                "page_size": 100,  # Default used in function
            },
        },
        "results": {
            "asset_metrics": asset_metrics_data,
            "transaction_tracker": transaction_tracker_data,
        },
    }

    return comprehensive_data


# --- Example Usage ---
if __name__ == "__main__":
    # Example: Get data for Ethereum for the last 30 days
    eth_data = get_comprehensive_on_chain_data("eth")
    print("\n--- Ethereum Data (Last 30 Days) ---")
    # Pretty print the JSON output
    print(json.dumps(eth_data, indent=2))

    # Example: Get data for Bitcoin for a specific date range
    # btc_data = get_comprehensive_on_chain_data(
    #     asset_name="btc",
    #     timeseries_start_time="2024-01-01",
    #     timeseries_end_time="2024-01-31"
    # )
    # print("\n--- Bitcoin Data (Jan 2024) ---")
    # print(json.dumps(btc_data, indent=2))

    # Example: Get specific metrics for Cardano
    # ada_metrics = ["AdrActCnt", "TxCnt", "PriceUSD"]
    # ada_data = get_comprehensive_on_chain_data(
    #     asset_name="ada",
    #     metrics_list=ada_metrics,
    #     timeseries_start_time="2024-04-01",
    #     timeseries_end_time="2024-04-10"
    # )
    # print("\n--- Cardano Data (Specific Metrics & Range) ---")
    # print(json.dumps(ada_data, indent=2))
