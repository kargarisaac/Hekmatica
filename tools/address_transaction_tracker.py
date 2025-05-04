import requests
import os
import time
from datetime import datetime, timezone
import json
from dotenv import load_dotenv
import math
from decimal import Decimal, getcontext

# --- Solana Specific Import ---
try:
    from solana.rpc.api import Client
    from solana.publickey import PublicKey

    SOLANA_AVAILABLE = True
except ImportError:
    SOLANA_AVAILABLE = False
    print("Solana library not found. Run 'pip install solana' to enable SOL tracking.")

# Load environment variables from .env file
load_dotenv()
getcontext().prec = 40  # Set precision for Decimal calculations

# --- Configuration ---

# -- API Keys --
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
BLOCKFROST_API_KEY = os.getenv("BLOCKFROST_API_KEY")  # For Cardano (ADA)
SUBSCAN_API_KEY = os.getenv("SUBSCAN_API_KEY")  # For Polkadot (DOT)

# -- Ethereum (ETH) --
ETHERSCAN_API_URL = "https://api.etherscan.io/api"
DEFAULT_ETH_ADDRESSES_TO_MONITOR = ["0x73BCEb1Cd57C711feaC4224D062b0F6ff338501e"]
DEFAULT_LARGE_TX_THRESHOLD_ETH = Decimal("100")
WEI_PER_ETH = Decimal("1e18")

# -- Bitcoin (BTC) --
BLOCKCHAIN_COM_API_URL = "https://blockchain.info"
DEFAULT_BTC_ADDRESSES_TO_MONITOR = ["bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"]
DEFAULT_LARGE_TX_THRESHOLD_BTC = Decimal("10")
SATOSHIS_PER_BTC = Decimal("1e8")

# -- Solana (SOL) --
# Using public RPC endpoint. Consider using a dedicated RPC provider for higher limits.
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
DEFAULT_SOL_ADDRESSES_TO_MONITOR = [
    "9WzDXwBbmkg8ZTbNMqUxvQRApF22xwsg आरए़D51"
]  # Example Phantom Wallet address (replace)
DEFAULT_LARGE_TX_THRESHOLD_SOL = Decimal("1000")
LAMPORTS_PER_SOL = Decimal("1e9")

# -- Cardano (ADA) --
BLOCKFROST_API_URL = "https://cardano-mainnet.blockfrost.io/api/v0"
DEFAULT_ADA_ADDRESSES_TO_MONITOR = [
    "addr1qx2fxv2umyvze5r2d4smhklzzdxhtahw07qxdvbs84anpcr7q gleaming"
]  # Example Yoroi address (replace)
DEFAULT_LARGE_TX_THRESHOLD_ADA = Decimal("100000")
LOVELACE_PER_ADA = Decimal("1e6")

# -- Ripple (XRP) --
XRPSCAN_API_URL = "https://api.xrpscan.com/v2"
DEFAULT_XRP_ADDRESSES_TO_MONITOR = [
    "rPdvC6ccq8hCdPKSPJkPmyZ4Mi1oG2FFkT"
]  # Example Ripple address (replace)
DEFAULT_LARGE_TX_THRESHOLD_XRP = Decimal("1000000")
DROPS_PER_XRP = Decimal("1e6")

# -- Dogecoin (DOGE) --
# Using Blockchair API (supports multiple chains)
BLOCKCHAIR_API_URL = "https://api.blockchair.com"
DEFAULT_DOGE_ADDRESSES_TO_MONITOR = [
    "D7ZEas42x4L4Y5QNgVpia4m4rmzJEcVx68"
]  # Example Doge address (replace)
DEFAULT_LARGE_TX_THRESHOLD_DOGE = Decimal("1000000")
# Smallest unit for DOGE is 10^-8, like Satoshi
SMALLEST_UNIT_PER_DOGE = Decimal("1e8")

# -- Polkadot (DOT) --
SUBSCAN_API_URL = "https://polkadot.api.subscan.io"
DEFAULT_DOT_ADDRESSES_TO_MONITOR = [
    "15oF4uVJwmo4TdGW7VfQxNLavjCXviqxT9S1MgbjMNHr6Sp5"
]  # Example Polkadot address (replace)
DEFAULT_LARGE_TX_THRESHOLD_DOT = Decimal("10000")
# Polkadot's smallest unit (Planck) is 10^10
PLANCK_PER_DOT = Decimal("1e10")


# --- Generic Helper Function Structure ---
def _make_api_request(
    url: str,
    method: str = "GET",
    headers: dict = None,
    params: dict = None,
    data: dict = None,
    timeout: int = 30,
    api_name: str = "API",
) -> dict:
    """Generic helper to make API requests and handle common errors."""
    try:
        # Add slight delay to respect rate limits
        time.sleep(0.3)  # Adjust per API if needed

        response = requests.request(
            method, url, headers=headers, params=params, json=data, timeout=timeout
        )

        if response.status_code == 429:
            print(f"{api_name} Error: Rate limit exceeded.")
            return {"status": "error", "error": f"{api_name} rate limit exceeded."}
        if response.status_code == 401:
            print(f"{api_name} Error: Unauthorized (Check API Key).")
            return {"status": "error", "error": f"{api_name} Unauthorized."}
        if response.status_code == 403:
            print(f"{api_name} Error: Forbidden (Check API Key/Permissions).")
            return {"status": "error", "error": f"{api_name} Forbidden."}

        # Check for HTML response indicating potential blocking/errors
        if response.headers.get("Content-Type", "").startswith("text/html"):
            print(
                f"{api_name} Error: Received HTML response, possibly rate limited or blocked."
            )
            return {"status": "error", "error": f"{api_name} returned HTML."}

        response.raise_for_status()  # Raise other HTTP errors

        # Handle empty response body
        if not response.content:
            print(f"{api_name} Warning: Received empty response body.")
            # Decide if empty is success or error based on context
            # For now, treat as success with empty result if status was 2xx
            if 200 <= response.status_code < 300:
                return {
                    "status": "success",
                    "result": None,
                }  # Or {} or [] depending on expected type
            else:
                # This case should be caught by raise_for_status, but as fallback:
                return {
                    "status": "error",
                    "error": f"{api_name} returned empty response with status {response.status_code}",
                }

        data = response.json()
        return {"status": "success", "result": data}

    except requests.exceptions.RequestException as e:
        print(f"{api_name} Request Error: {e}")
        return {"status": "error", "error": f"Network or request error: {e}"}
    except json.JSONDecodeError as e:
        print(f"{api_name} JSON Decode Error: {e}")
        print(f"Response text: {response.text[:500]}...")  # Log beginning of text
        return {
            "status": "error",
            "error": f"Failed to decode JSON response. Response text: {response.text[:100]}...",
        }
    except Exception as e:
        print(f"An unexpected error occurred during {api_name} call: {e}")
        return {"status": "error", "error": f"An unexpected error occurred: {e}"}


# --- Specific API Helpers ---


def _make_etherscan_request(params: dict) -> dict:
    """Makes a GET request to the Etherscan API."""
    if not ETHERSCAN_API_KEY:
        return {"status": "error", "error": "Etherscan API key missing."}
    params["apikey"] = ETHERSCAN_API_KEY
    # Use generic helper
    response_data = _make_api_request(
        ETHERSCAN_API_URL, params=params, api_name="Etherscan"
    )

    # Etherscan specific post-processing
    if response_data["status"] == "success" and isinstance(
        response_data["result"], dict
    ):
        etherscan_status = response_data["result"].get("status")
        message = response_data["result"].get("message")
        result = response_data["result"].get("result")

        if etherscan_status == "1":
            return {"status": "success", "result": result}
        elif etherscan_status == "0" and message == "No transactions found":
            return {"status": "success", "result": []}
        elif etherscan_status == "0" and message == "NOTOK":
            error_detail = (
                result
                if result
                else "Rate limit likely exceeded or invalid API key/parameters."
            )
            print(f"Etherscan API Error: {message} - {error_detail}")
            return {
                "status": "error",
                "error": f"Etherscan API Error: {message} - {error_detail}",
            }
        else:
            print(
                f"Etherscan API Error: Status {etherscan_status}, Message {message}, Result {result}"
            )
            return {
                "status": "error",
                "error": f"Etherscan API Error: Status {etherscan_status}, Message {message}",
            }
    elif response_data["status"] == "error":
        return response_data  # Propagate error
    else:  # Unexpected success format
        print(f"Unexpected Etherscan success response format: {response_data}")
        return {
            "status": "error",
            "error": "Unexpected Etherscan success response format.",
        }


def _make_blockchain_com_request(endpoint: str, params: dict = None) -> dict:
    """Makes a GET request to the Blockchain.com Info API."""
    # Uses generic helper, specific endpoint construction happens before call
    return _make_api_request(
        f"{BLOCKCHAIN_COM_API_URL}{endpoint}",
        params=params,
        api_name="Blockchain.com",
        timeout=45,
    )


def _make_blockfrost_request(endpoint: str, params: dict = None) -> dict:
    """Makes a GET request to the Blockfrost API (Cardano)."""
    if not BLOCKFROST_API_KEY:
        return {"status": "error", "error": "Blockfrost API key missing."}
    headers = {"project_id": BLOCKFROST_API_KEY}
    return _make_api_request(
        f"{BLOCKFROST_API_URL}{endpoint}",
        headers=headers,
        params=params,
        api_name="Blockfrost",
    )


def _make_xrpscan_request(endpoint: str, params: dict = None) -> dict:
    """Makes a GET request to the XRPScan API."""
    return _make_api_request(
        f"{XRPSCAN_API_URL}{endpoint}", params=params, api_name="XRPScan"
    )


def _make_blockchair_request(
    chain_path: str, endpoint_suffix: str, params: dict = None
) -> dict:
    """Makes a GET request to the Blockchair API."""
    # Example chain_path: "dogecoin", endpoint_suffix: "/dashboards/address/{address}"
    url = f"{BLOCKCHAIR_API_URL}/{chain_path}{endpoint_suffix}"
    # Blockchair responses are nested under 'data'
    response = _make_api_request(url, params=params, api_name="Blockchair")
    if response["status"] == "success" and response["result"] is not None:
        # Extract the actual data, handle cases where address might not exist
        data_key = list(response["result"].get("data", {}).keys())
        if data_key:
            response["result"] = response["result"]["data"][data_key[0]]
        else:
            # Handle case where address might not be found in Blockchair's data structure
            print(f"Blockchair Warning: Address data not found in response for {url}")
            response["result"] = None  # Or indicate not found appropriately
    return response


def _make_subscan_request(endpoint: str, data: dict = None) -> dict:
    """Makes a POST request to the Subscan API (Polkadot)."""
    if not SUBSCAN_API_KEY:
        return {"status": "error", "error": "Subscan API key missing."}
    headers = {"Content-Type": "application/json", "X-API-Key": SUBSCAN_API_KEY}
    # Subscan uses POST for queries
    response = _make_api_request(
        f"{SUBSCAN_API_URL}{endpoint}",
        method="POST",
        headers=headers,
        data=data,
        api_name="Subscan",
    )

    # Subscan specific post-processing
    if response["status"] == "success" and isinstance(response["result"], dict):
        subscan_code = response["result"].get("code")
        message = response["result"].get("message")
        result_data = response["result"].get("data")

        if subscan_code == 0:  # Success code for Subscan
            return {"status": "success", "result": result_data}
        else:
            print(f"Subscan API Error: Code {subscan_code}, Message {message}")
            return {
                "status": "error",
                "error": f"Subscan API Error: Code {subscan_code}, Message {message}",
            }
    elif response["status"] == "error":
        return response  # Propagate error
    else:  # Unexpected success format
        print(f"Unexpected Subscan success response format: {response}")
        return {
            "status": "error",
            "error": "Unexpected Subscan success response format.",
        }


# --- Chain-Specific Tracking Functions ---


def get_large_eth_transfers(
    addresses: list, threshold_eth: Decimal, offset: int = 50, **kwargs
) -> dict:
    """Fetches large ETH transfers using Etherscan."""
    print(f"\n--- Starting ETH Transfer Check (Threshold: {threshold_eth} ETH) ---")
    large_txs_by_address = {}
    threshold_wei = threshold_eth * WEI_PER_ETH

    for address in addresses:
        print(f"\nChecking ETH address: {address}")
        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "page": 1,
            "offset": offset,
            "sort": "desc",
        }
        response_data = _make_etherscan_request(params)
        # ... (rest of parsing logic is largely the same as before, using Decimal) ...
        if response_data.get("status") != "success":
            print(
                f"  Skipping ETH address {address} due to API error: {response_data.get('error')}"
            )
            continue
        transactions = response_data.get("result", [])
        if not transactions:
            continue

        found_large_for_address = []
        for tx in transactions:
            try:
                value_str = tx.get("value", "0")
                if not value_str.isdigit():
                    continue
                tx_value_wei = Decimal(value_str)

                if tx_value_wei >= threshold_wei:
                    direction = (
                        "outgoing"
                        if tx["from"].lower() == address.lower()
                        else "incoming"
                    )
                    ts = int(tx.get("timeStamp", 0))
                    large_tx_info = {
                        "chain": "eth",
                        "address": address,
                        "hash": tx.get("hash"),
                        "timestamp_unix": ts,
                        "timestamp_utc": datetime.fromtimestamp(
                            ts, timezone.utc
                        ).isoformat(),
                        "from": tx.get("from"),
                        "to": tx.get("to"),
                        "value_native": str(tx_value_wei / WEI_PER_ETH),
                        "value_smallest_unit": str(tx_value_wei),
                        "direction": direction,
                        "blockNumber": tx.get("blockNumber"),
                        "isError": tx.get("isError", "0"),
                    }
                    found_large_for_address.append(large_tx_info)
                    print(
                        f"  Found large ETH {direction} TX: {large_tx_info['value_native']} ETH, Hash: {large_tx_info['hash'][:10]}..."
                    )
            except Exception as e:
                print(f"  Error processing ETH tx {tx.get('hash', 'N/A')}: {e}")

        if found_large_for_address:
            large_txs_by_address[address] = found_large_for_address

    print("\n--- ETH Transfer Check Finished ---")
    return large_txs_by_address


def get_large_btc_transfers(
    addresses: list, threshold_btc: Decimal, limit: int = 50, **kwargs
) -> dict:
    """Fetches large BTC transfers using Blockchain.com."""
    print(f"\n--- Starting BTC Transfer Check (Threshold: {threshold_btc} BTC) ---")
    large_txs_by_address = {}
    threshold_satoshi = threshold_btc * SATOSHIS_PER_BTC

    for address in addresses:
        print(f"\nChecking BTC address: {address}")
        endpoint = f"/rawaddr/{address}"
        params = {"limit": limit}
        response_data = _make_blockchain_com_request(endpoint, params=params)
        # ... (rest of parsing logic is largely the same as before, using Decimal) ...
        if response_data.get("status") != "success":
            print(
                f"  Skipping BTC address {address} due to API error: {response_data.get('error')}"
            )
            continue
        data = response_data.get("result", {})
        transactions = data.get("txs", [])
        if not transactions:
            continue

        found_large_for_address = []
        for tx in transactions:
            try:
                tx_hash = tx.get("hash")
                tx_time_unix = tx.get("time", 0)
                satoshi_in = Decimal(0)
                satoshi_out = Decimal(0)

                for tx_input in tx.get("inputs", []):
                    prev_out = tx_input.get("prev_out")
                    if prev_out and prev_out.get("addr") == address:
                        satoshi_out += Decimal(prev_out.get("value", 0))
                for tx_output in tx.get("out", []):
                    if tx_output.get("addr") == address:
                        satoshi_in += Decimal(tx_output.get("value", 0))

                net_change_satoshi = satoshi_in - satoshi_out
                abs_net_change_satoshi = abs(net_change_satoshi)

                if (
                    abs_net_change_satoshi >= threshold_satoshi
                    and threshold_satoshi > 0
                ):
                    direction = (
                        "incoming"
                        if net_change_satoshi > 0
                        else ("outgoing" if net_change_satoshi < 0 else "internal")
                    )
                    value_btc_dec = net_change_satoshi / SATOSHIS_PER_BTC
                    large_tx_info = {
                        "chain": "btc",
                        "address": address,
                        "hash": tx_hash,
                        "timestamp_unix": tx_time_unix,
                        "timestamp_utc": datetime.fromtimestamp(
                            tx_time_unix, timezone.utc
                        ).isoformat(),
                        "net_value_native": str(value_btc_dec),
                        "net_value_smallest_unit": str(net_change_satoshi),
                        "direction": direction,
                        "block_height": tx.get("block_height"),
                    }
                    found_large_for_address.append(large_tx_info)
                    print(
                        f"  Found large BTC TX (Net: {large_tx_info['net_value_native']} BTC), Dir: {direction}, Hash: {tx_hash[:10]}..."
                    )
            except Exception as e:
                print(f"  Error processing BTC tx {tx.get('hash', 'N/A')}: {e}")

        if found_large_for_address:
            found_large_for_address.sort(
                key=lambda x: x["timestamp_unix"], reverse=True
            )
            large_txs_by_address[address] = found_large_for_address

    print("\n--- BTC Transfer Check Finished ---")
    return large_txs_by_address


def get_large_sol_transfers(
    addresses: list, threshold_sol: Decimal, limit: int = 25, **kwargs
) -> dict:
    """Fetches large SOL transfers using Solana RPC."""
    if not SOLANA_AVAILABLE:
        print("Solana library not installed. Skipping SOL check.")
        return {"error": "Solana library not installed."}

    print(f"\n--- Starting SOL Transfer Check (Threshold: {threshold_sol} SOL) ---")
    large_txs_by_address = {}
    threshold_lamports = threshold_sol * LAMPORTS_PER_SOL
    solana_client = Client(SOLANA_RPC_URL)  # Consider adding commitment level if needed

    for address in addresses:
        print(f"\nChecking SOL address: {address}")
        try:
            pubkey = PublicKey(address)
            # Get recent transaction signatures involving the address
            signatures_resp = solana_client.get_signatures_for_address(
                pubkey, limit=limit
            )  # , commitment="confirmed") Add commitment if needed

            if not signatures_resp or not signatures_resp.value:
                print("  No SOL signatures found in the checked range.")
                continue

            signatures = [s.signature for s in signatures_resp.value]
            print(f"  Found {len(signatures)} signatures, fetching details...")

            found_large_for_address = []
            # Fetch details for each transaction signature (can be slow)
            # Consider batching get_transaction calls if library/RPC supports it
            for i, sig in enumerate(signatures):
                if i > 0 and i % 5 == 0:
                    print(
                        f"    Fetched {i}/{len(signatures)} details..."
                    )  # Progress indicator
                time.sleep(0.1)  # Small delay between get_transaction calls
                try:
                    tx_detail_resp = solana_client.get_transaction(
                        sig, encoding="jsonParsed", max_supported_transaction_version=0
                    )  # jsonParsed is key
                    if not tx_detail_resp or not tx_detail_resp.value:
                        continue
                    tx_detail = (
                        tx_detail_resp.value.transaction.transaction
                    )  # Navigate structure

                    meta = tx_detail_resp.value.transaction.meta
                    if not meta or meta.err:
                        continue  # Skip failed transactions

                    block_time = tx_detail_resp.value.block_time or 0
                    pre_balances = meta.pre_balances
                    post_balances = meta.post_balances
                    account_keys = [
                        str(acc) for acc in tx_detail.message.account_keys
                    ]  # Get addresses involved

                    # Find the index of our monitored address
                    try:
                        addr_index = account_keys.index(address)
                    except ValueError:
                        continue  # Address not directly involved? Should not happen based on get_signatures_for_address

                    # Calculate net change for the monitored address
                    pre_balance = Decimal(pre_balances[addr_index])
                    post_balance = Decimal(post_balances[addr_index])
                    net_change_lamports = post_balance - pre_balance
                    abs_net_change_lamports = abs(net_change_lamports)

                    if (
                        abs_net_change_lamports >= threshold_lamports
                        and threshold_lamports > 0
                    ):
                        direction = (
                            "incoming"
                            if net_change_lamports > 0
                            else ("outgoing" if net_change_lamports < 0 else "internal")
                        )
                        value_sol_dec = net_change_lamports / LAMPORTS_PER_SOL

                        # Try to find simple transfer details (might not always work for complex TXs)
                        from_addr, to_addr = "unknown", "unknown"
                        instructions = tx_detail.message.instructions
                        for inst in instructions:
                            if inst.program_id == PublicKey(
                                "11111111111111111111111111111111"
                            ):  # SystemProgram
                                if (
                                    inst.parsed
                                    and inst.parsed.get("type") == "transfer"
                                ):
                                    from_addr = inst.parsed["info"].get("source")
                                    to_addr = inst.parsed["info"].get("destination")
                                    break  # Assume first transfer is the main one for simplicity

                        large_tx_info = {
                            "chain": "sol",
                            "address": address,
                            "hash": str(sig),
                            "timestamp_unix": block_time,
                            "timestamp_utc": datetime.fromtimestamp(
                                block_time, timezone.utc
                            ).isoformat(),
                            "from": from_addr,
                            "to": to_addr,  # Best effort from/to
                            "net_value_native": str(value_sol_dec),
                            "net_value_smallest_unit": str(net_change_lamports),
                            "direction": direction,
                            "blockNumber": tx_detail_resp.value.slot,  # Slot is like block number
                        }
                        found_large_for_address.append(large_tx_info)
                        print(
                            f"  Found large SOL TX (Net: {large_tx_info['net_value_native']} SOL), Dir: {direction}, Hash: {str(sig)[:10]}..."
                        )

                except Exception as e:
                    print(f"  Error processing SOL signature {str(sig)[:10]}...: {e}")
                    continue  # Skip to next signature

            if found_large_for_address:
                found_large_for_address.sort(
                    key=lambda x: x["timestamp_unix"], reverse=True
                )
                large_txs_by_address[address] = found_large_for_address

        except Exception as e:
            print(f"  Error fetching/processing SOL data for address {address}: {e}")
            continue  # Skip to next address

    print("\n--- SOL Transfer Check Finished ---")
    return large_txs_by_address


def get_large_ada_transfers(
    addresses: list, threshold_ada: Decimal, count: int = 50, **kwargs
) -> dict:
    """Fetches large ADA transfers using Blockfrost."""
    if not BLOCKFROST_API_KEY:
        print("Blockfrost API key missing. Skipping ADA check.")
        return {"error": "Blockfrost API key missing."}

    print(f"\n--- Starting ADA Transfer Check (Threshold: {threshold_ada} ADA) ---")
    large_txs_by_address = {}
    threshold_lovelace = threshold_ada * LOVELACE_PER_ADA

    for address in addresses:
        print(f"\nChecking ADA address: {address}")
        # Get recent transaction hashes involving the address
        endpoint_txs = f"/addresses/{address}/transactions"
        params_txs = {"order": "desc", "count": count}
        tx_hashes_resp = _make_blockfrost_request(endpoint_txs, params=params_txs)

        if tx_hashes_resp["status"] != "success" or not tx_hashes_resp["result"]:
            error_msg = tx_hashes_resp.get(
                "error", "No transactions found or API error"
            )
            print(f"  Skipping ADA address {address}: {error_msg}")
            continue

        tx_hashes_data = tx_hashes_resp["result"]  # List of {"tx_hash": "...", ...}
        print(f"  Found {len(tx_hashes_data)} tx hashes, fetching details...")

        found_large_for_address = []
        # Fetch UTXO details for each transaction to calculate net change
        for i, tx_info in enumerate(tx_hashes_data):
            tx_hash = tx_info.get("tx_hash")
            if not tx_hash:
                continue
            if i > 0 and i % 10 == 0:
                print(f"    Fetched {i}/{len(tx_hashes_data)} details...")  # Progress

            endpoint_utxo = f"/txs/{tx_hash}/utxos"
            utxo_resp = _make_blockfrost_request(endpoint_utxo)

            if utxo_resp["status"] != "success" or not utxo_resp["result"]:
                print(
                    f"  Error fetching UTXOs for ADA tx {tx_hash[:10]}...: {utxo_resp.get('error')}"
                )
                continue

            utxo_data = utxo_resp["result"]
            block_height = utxo_data.get(
                "block"
            )  # Block hash, need block details for time
            # Fetch block details for timestamp
            block_time = 0
            if block_height:
                block_resp = _make_blockfrost_request(f"/blocks/{block_height}")
                if block_resp["status"] == "success" and block_resp["result"]:
                    block_time = block_resp["result"].get("time", 0)

            lovelace_in = Decimal(0)
            lovelace_out = Decimal(0)

            # Inputs associated with the monitored address
            for tx_input in utxo_data.get("inputs", []):
                if tx_input.get("address") == address:
                    # Find the amount from the input's UTXO list (should contain exactly one amount for ADA)
                    amount_list = tx_input.get("amount", [])
                    for item in amount_list:
                        if item.get("unit") == "lovelace":
                            lovelace_out += Decimal(item.get("quantity", 0))
                            break  # Found lovelace amount for this input

            # Outputs associated with the monitored address
            for tx_output in utxo_data.get("outputs", []):
                if tx_output.get("address") == address:
                    amount_list = tx_output.get("amount", [])
                    for item in amount_list:
                        if item.get("unit") == "lovelace":
                            lovelace_in += Decimal(item.get("quantity", 0))
                            break  # Found lovelace amount for this output

            net_change_lovelace = lovelace_in - lovelace_out
            abs_net_change_lovelace = abs(net_change_lovelace)

            if abs_net_change_lovelace >= threshold_lovelace and threshold_lovelace > 0:
                direction = (
                    "incoming"
                    if net_change_lovelace > 0
                    else ("outgoing" if net_change_lovelace < 0 else "internal")
                )
                value_ada_dec = net_change_lovelace / LOVELACE_PER_ADA
                large_tx_info = {
                    "chain": "ada",
                    "address": address,
                    "hash": tx_hash,
                    "timestamp_unix": block_time,
                    "timestamp_utc": datetime.fromtimestamp(
                        block_time, timezone.utc
                    ).isoformat()
                    if block_time
                    else None,
                    "net_value_native": str(value_ada_dec),
                    "net_value_smallest_unit": str(net_change_lovelace),
                    "direction": direction,
                    "block_height": block_height,
                }
                found_large_for_address.append(large_tx_info)
                print(
                    f"  Found large ADA TX (Net: {large_tx_info['net_value_native']} ADA), Dir: {direction}, Hash: {tx_hash[:10]}..."
                )

        if found_large_for_address:
            found_large_for_address.sort(
                key=lambda x: x.get("timestamp_unix", 0), reverse=True
            )
            large_txs_by_address[address] = found_large_for_address

    print("\n--- ADA Transfer Check Finished ---")
    return large_txs_by_address


def get_large_xrp_transfers(
    addresses: list, threshold_xrp: Decimal, limit: int = 50, **kwargs
) -> dict:
    """Fetches large XRP transfers using XRPScan."""
    print(f"\n--- Starting XRP Transfer Check (Threshold: {threshold_xrp} XRP) ---")
    large_txs_by_address = {}
    threshold_drops = threshold_xrp * DROPS_PER_XRP

    for address in addresses:
        print(f"\nChecking XRP address: {address}")
        endpoint = f"/accounts/{address}/transactions"
        params = {
            "limit": limit,
            "type": "Payment",
        }  # Focus on Payment type transactions
        response_data = _make_xrpscan_request(endpoint, params=params)

        if response_data["status"] != "success" or not response_data["result"]:
            error_msg = response_data.get("error", "No transactions found or API error")
            print(f"  Skipping XRP address {address}: {error_msg}")
            continue

        transactions = response_data.get("result", [])
        if not transactions:
            continue

        found_large_for_address = []
        for tx in transactions:
            try:
                tx_hash = tx.get("hash")
                tx_time_unix = tx.get("date", 0)
                meta = tx.get("meta", {})
                tx_result = tx.get("tx", {}).get(
                    "TransactionResult", ""
                )  # tesSUCCESS indicates success

                if tx_result != "tesSUCCESS":
                    continue  # Skip failed/non-validated txs

                # Amount is usually a string representing drops for XRP payments
                amount_str = tx.get("tx", {}).get("Amount")
                if (
                    not amount_str
                    or not isinstance(amount_str, str)
                    or not amount_str.isdigit()
                ):
                    continue

                amount_drops = Decimal(amount_str)
                account = tx.get("tx", {}).get("Account")  # Sender
                destination = tx.get("tx", {}).get("Destination")

                value_xrp_dec = amount_drops / DROPS_PER_XRP
                direction = "unknown"
                is_relevant = False

                if account == address:  # Outgoing
                    direction = "outgoing"
                    is_relevant = True
                elif destination == address:  # Incoming
                    direction = "incoming"
                    is_relevant = True

                if (
                    is_relevant
                    and amount_drops >= threshold_drops
                    and threshold_drops > 0
                ):
                    large_tx_info = {
                        "chain": "xrp",
                        "address": address,
                        "hash": tx_hash,
                        "timestamp_unix": tx_time_unix,
                        "timestamp_utc": datetime.fromtimestamp(
                            tx_time_unix, timezone.utc
                        ).isoformat(),
                        "from": account,
                        "to": destination,
                        "value_native": str(value_xrp_dec),
                        "value_smallest_unit": str(amount_drops),
                        "direction": direction,
                        "blockNumber": tx.get("tx", {}).get("ledger_index"),
                    }
                    found_large_for_address.append(large_tx_info)
                    print(
                        f"  Found large XRP {direction} TX: {large_tx_info['value_native']} XRP, Hash: {tx_hash[:10]}..."
                    )

            except Exception as e:
                print(f"  Error processing XRP tx {tx.get('hash', 'N/A')}: {e}")

        if found_large_for_address:
            # XRPScan API often returns oldest first, so sort descending
            found_large_for_address.sort(
                key=lambda x: x["timestamp_unix"], reverse=True
            )
            large_txs_by_address[address] = found_large_for_address

    print("\n--- XRP Transfer Check Finished ---")
    return large_txs_by_address


def get_large_doge_transfers(
    addresses: list, threshold_doge: Decimal, limit: int = 50, **kwargs
) -> dict:
    """Fetches large DOGE transfers using Blockchair."""
    print(f"\n--- Starting DOGE Transfer Check (Threshold: {threshold_doge} DOGE) ---")
    large_txs_by_address = {}
    threshold_smallest = threshold_doge * SMALLEST_UNIT_PER_DOGE

    for address in addresses:
        print(f"\nChecking DOGE address: {address}")
        # Blockchair dashboard endpoint includes recent transactions
        endpoint_suffix = f"/dashboards/address/{address}"
        params = {"limit": limit, "offset": 0}  # Limit controls tx count here
        response_data = _make_blockchair_request(
            "dogecoin", endpoint_suffix, params=params
        )

        if response_data["status"] != "success" or not response_data["result"]:
            error_msg = response_data.get(
                "error", "Address data not found or API error"
            )
            print(f"  Skipping DOGE address {address}: {error_msg}")
            continue

        # Transactions are usually in result['transactions']
        transactions = response_data.get("result", {}).get("transactions", [])
        if not transactions:
            print("  No DOGE transactions found in the checked range.")
            continue

        found_large_for_address = []
        # Need transaction details to calculate net change
        print(f"  Found {len(transactions)} tx hashes, fetching details...")
        for i, tx_hash in enumerate(transactions):
            if i > 0 and i % 10 == 0:
                print(f"    Fetched {i}/{len(transactions)} details...")  # Progress

            tx_detail_resp = _make_blockchair_request(
                "dogecoin", f"/dashboards/transaction/{tx_hash}"
            )
            if tx_detail_resp["status"] != "success" or not tx_detail_resp["result"]:
                print(
                    f"  Error fetching details for DOGE tx {tx_hash[:10]}...: {tx_detail_resp.get('error')}"
                )
                continue

            tx_data = tx_detail_resp.get("result", {}).get("transaction", {})
            if not tx_data:
                continue

            block_id = tx_data.get("block_id", -1)
            tx_time_str = tx_data.get("time", "")
            tx_time_unix = 0
            if tx_time_str:
                try:
                    # Example format: "2024-01-15 18:30:00"
                    dt_obj = datetime.strptime(
                        tx_time_str, "%Y-%m-%d %H:%M:%S"
                    ).replace(tzinfo=timezone.utc)
                    tx_time_unix = int(dt_obj.timestamp())
                except ValueError:
                    pass  # Ignore if time format is unexpected

            smallest_in = Decimal(0)
            smallest_out = Decimal(0)

            # Inputs
            for tx_input in tx_detail_resp.get("result", {}).get("inputs", []):
                if tx_input.get("recipient") == address:
                    smallest_out += Decimal(tx_input.get("value", 0))

            # Outputs
            for tx_output in tx_detail_resp.get("result", {}).get("outputs", []):
                if tx_output.get("recipient") == address:
                    smallest_in += Decimal(tx_output.get("value", 0))

            net_change_smallest = smallest_in - smallest_out
            abs_net_change_smallest = abs(net_change_smallest)

            if abs_net_change_smallest >= threshold_smallest and threshold_smallest > 0:
                direction = (
                    "incoming"
                    if net_change_smallest > 0
                    else ("outgoing" if net_change_smallest < 0 else "internal")
                )
                value_doge_dec = net_change_smallest / SMALLEST_UNIT_PER_DOGE
                large_tx_info = {
                    "chain": "doge",
                    "address": address,
                    "hash": tx_hash,
                    "timestamp_unix": tx_time_unix,
                    "timestamp_utc": datetime.fromtimestamp(
                        tx_time_unix, timezone.utc
                    ).isoformat()
                    if tx_time_unix
                    else None,
                    "net_value_native": str(value_doge_dec),
                    "net_value_smallest_unit": str(net_change_smallest),
                    "direction": direction,
                    "blockNumber": block_id,
                }
                found_large_for_address.append(large_tx_info)
                print(
                    f"  Found large DOGE TX (Net: {large_tx_info['net_value_native']} DOGE), Dir: {direction}, Hash: {tx_hash[:10]}..."
                )

        if found_large_for_address:
            found_large_for_address.sort(
                key=lambda x: x.get("timestamp_unix", 0), reverse=True
            )
            large_txs_by_address[address] = found_large_for_address

    print("\n--- DOGE Transfer Check Finished ---")
    return large_txs_by_address


def get_large_dot_transfers(
    addresses: list, threshold_dot: Decimal, row: int = 50, **kwargs
) -> dict:
    """Fetches large DOT transfers using Subscan."""
    if not SUBSCAN_API_KEY:
        print("Subscan API key missing. Skipping DOT check.")
        return {"error": "Subscan API key missing."}

    print(f"\n--- Starting DOT Transfer Check (Threshold: {threshold_dot} DOT) ---")
    large_txs_by_address = {}
    threshold_planck = threshold_dot * PLANCK_PER_DOT

    for address in addresses:
        print(f"\nChecking DOT address: {address}")
        endpoint = "/api/scan/transfers"
        # Subscan uses POST for queries, parameters go in data payload
        data = {
            "row": row,
            "page": 0,  # Start from first page
            "address": address,
        }
        response_data = _make_subscan_request(endpoint, data=data)

        if response_data["status"] != "success":
            error_msg = response_data.get("error", "API error")
            print(f"  Skipping DOT address {address}: {error_msg}")
            continue

        transfers = response_data.get("result", {}).get("transfers")
        if not transfers:
            print("  No DOT transfers found in the checked range.")
            continue

        found_large_for_address = []
        for tx in transfers:
            try:
                # Subscan provides transfer details directly
                amount_str = tx.get("amount", "0")
                amount_planck = (
                    Decimal(amount_str) * PLANCK_PER_DOT
                )  # Amount is in DOT, convert to Planck
                tx_hash = tx.get("hash")
                block_num = tx.get("block_num")
                block_ts = tx.get("block_timestamp", 0)
                from_addr = tx.get("from")
                to_addr = tx.get("to")
                success = tx.get("success", False)

                if not success:
                    continue  # Skip failed transfers

                direction = "unknown"
                is_relevant = False
                value_dot_dec = amount_planck / PLANCK_PER_DOT

                if from_addr == address:
                    direction = "outgoing"
                    is_relevant = True
                elif to_addr == address:
                    direction = "incoming"
                    is_relevant = True

                # Check threshold based on the transfer amount itself
                if (
                    is_relevant
                    and amount_planck >= threshold_planck
                    and threshold_planck > 0
                ):
                    large_tx_info = {
                        "chain": "dot",
                        "address": address,
                        "hash": tx_hash,
                        "timestamp_unix": block_ts,
                        "timestamp_utc": datetime.fromtimestamp(
                            block_ts, timezone.utc
                        ).isoformat(),
                        "from": from_addr,
                        "to": to_addr,
                        "value_native": str(value_dot_dec),
                        "value_smallest_unit": str(amount_planck),
                        "direction": direction,
                        "blockNumber": block_num,
                    }
                    found_large_for_address.append(large_tx_info)
                    print(
                        f"  Found large DOT {direction} TX: {large_tx_info['value_native']} DOT, Hash: {tx_hash[:10]}..."
                    )

            except Exception as e:
                print(f"  Error processing DOT tx {tx.get('hash', 'N/A')}: {e}")

        if found_large_for_address:
            # Already sorted by time descending by API
            large_txs_by_address[address] = found_large_for_address

    print("\n--- DOT Transfer Check Finished ---")
    return large_txs_by_address


# --- Main Dispatcher Function ---
SUPPORTED_CHAINS = {
    "eth": {
        "function": get_large_eth_transfers,
        "default_addresses": DEFAULT_ETH_ADDRESSES_TO_MONITOR,
        "default_threshold": DEFAULT_LARGE_TX_THRESHOLD_ETH,
        "requires_key": "ETHERSCAN_API_KEY",
    },
    "btc": {
        "function": get_large_btc_transfers,
        "default_addresses": DEFAULT_BTC_ADDRESSES_TO_MONITOR,
        "default_threshold": DEFAULT_LARGE_TX_THRESHOLD_BTC,
        "requires_key": None,
    },
    "sol": {
        "function": get_large_sol_transfers,
        "default_addresses": DEFAULT_SOL_ADDRESSES_TO_MONITOR,
        "default_threshold": DEFAULT_LARGE_TX_THRESHOLD_SOL,
        "requires_key": None,  # Relies on public RPC and solana library installation
    },
    "ada": {
        "function": get_large_ada_transfers,
        "default_addresses": DEFAULT_ADA_ADDRESSES_TO_MONITOR,
        "default_threshold": DEFAULT_LARGE_TX_THRESHOLD_ADA,
        "requires_key": "BLOCKFROST_API_KEY",
    },
    "xrp": {
        "function": get_large_xrp_transfers,
        "default_addresses": DEFAULT_XRP_ADDRESSES_TO_MONITOR,
        "default_threshold": DEFAULT_LARGE_TX_THRESHOLD_XRP,
        "requires_key": None,
    },
    "doge": {
        "function": get_large_doge_transfers,
        "default_addresses": DEFAULT_DOGE_ADDRESSES_TO_MONITOR,
        "default_threshold": DEFAULT_LARGE_TX_THRESHOLD_DOGE,
        "requires_key": None,
    },
    "dot": {
        "function": get_large_dot_transfers,
        "default_addresses": DEFAULT_DOT_ADDRESSES_TO_MONITOR,
        "default_threshold": DEFAULT_LARGE_TX_THRESHOLD_DOT,
        "requires_key": "SUBSCAN_API_KEY",
    },
    # Add other chains here as implemented
}


def get_large_transfers_for_chain(
    chain: str,
    addresses: list = None,
    threshold: float = None,  # Input threshold in native units (e.g., ETH, BTC)
    **kwargs,  # Pass other args like limit, offset, count to specific functions
) -> dict:
    """
    Dispatcher function to get large transfers for a supported blockchain.

    Args:
        chain: The blockchain identifier (e.g., 'eth', 'btc', 'sol', 'ada', 'xrp', 'doge', 'dot').
        addresses: Optional list of addresses to monitor. Uses chain default if None.
        threshold: Optional minimum transfer value in the chain's native unit (e.g., 100 ETH, 10 BTC). Uses chain default if None.
        **kwargs: Additional arguments specific to the chain's tracking function (e.g., limit, offset).

    Returns:
        A dictionary containing large transactions found, grouped by address,
        or an error dictionary if the chain is unsupported or prerequisites are missing.
    """
    chain_lower = chain.lower()
    if chain_lower not in SUPPORTED_CHAINS:
        return {
            "error": f"Unsupported chain: {chain}. Supported: {list(SUPPORTED_CHAINS.keys())}"
        }

    config = SUPPORTED_CHAINS[chain_lower]
    tracking_function = config["function"]

    # Check for required API key
    required_key_name = config.get("requires_key")
    if required_key_name:
        api_key = globals().get(
            required_key_name
        )  # Check if key exists globally (loaded from .env)
        if not api_key:
            return {
                "error": f"Missing required API key for chain '{chain_lower}': {required_key_name} not found in environment variables."
            }

    # Use default addresses if none provided
    if addresses is None:
        addresses = config["default_addresses"]

    # Use default threshold if none provided, convert to Decimal
    if threshold is None:
        threshold_native = config["default_threshold"]
    else:
        try:
            threshold_native = Decimal(threshold)
        except Exception:
            return {"error": f"Invalid threshold value: {threshold}. Must be a number."}

    # Special check for Solana library
    if chain_lower == "sol" and not SOLANA_AVAILABLE:
        return {"error": "Solana library not installed. Run 'pip install solana'"}

    # Call the specific tracking function
    try:
        # Pass the native threshold and addresses, plus any extra args
        results = tracking_function(
            addresses=addresses, threshold_native=threshold_native, **kwargs
        )
        return results
    except Exception as e:
        print(f"Error executing tracking function for chain {chain_lower}: {e}")
        # Include traceback for debugging if needed: import traceback; traceback.print_exc()
        return {
            "error": f"An unexpected error occurred while tracking {chain_lower}: {e}"
        }


# --- Example Usage ---
if __name__ == "__main__":
    print("--- Running Address Transaction Tracker Examples ---")

    # Define chains to test
    chains_to_test = ["eth", "btc", "sol", "ada", "xrp", "doge", "dot"]

    for chain_name in chains_to_test:
        print(f"\n===== Testing Chain: {chain_name.upper()} =====")
        # Use defaults for addresses and threshold by not passing them
        # Pass specific args like limit if needed, e.g., limit=10
        activity = get_large_transfers_for_chain(
            chain_name, limit=10
        )  # Example: limit recent check to 10 txs

        print(f"\n--- Summary for {chain_name.upper()} ---")
        if isinstance(activity, dict) and activity.get("error"):
            print(f"Error: {activity['error']}")
        elif activity:
            print(json.dumps(activity, indent=2))
        else:
            print(
                f"No large {chain_name.upper()} transactions found meeting default criteria, or API errors occurred during processing."
            )
        print(f"===== Finished Chain: {chain_name.upper()} =====")
        time.sleep(1)  # Pause between testing different chains

    print("\n--- Address Transaction Tracker Examples Finished ---")
