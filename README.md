# Hekmatica

`Hekmat` means wisdom and philosophy in Persian.

Hekmatica is a deep research and conversational agent designed to answer questions on various topics by leveraging web search, external tools (like price lookups), and large language models (LLMs).

## Overview

This agent uses a structured workflow orchestrated by LangGraph to:
1.  Understand and potentially clarify the user's question.
2.  Break down the question into searchable subqueries.
3.  Plan which tools (web search, price lookup) to use.
4.  Gather information using the selected tools.
5.  Filter and rank the gathered information for relevance.
6.  Synthesize a comprehensive answer based on the relevant information.
7.  Critique its own answer and potentially refine it by performing additional searches.

The agent leverages BAML (Boundary Markup Language) to define and manage interactions with LLMs for tasks like planning, ranking, and generation.

## Architecture

*   **Orchestration:** LangGraph (`agent.py`, `graph.py`) manages the flow of execution through different states and nodes.
*   **LLM Interaction:** BAML (`baml_src/`) defines the prompts, functions, and data structures for interacting with LLMs reliably.
*   **Tools:** Custom Python functions (`tools/`) provide capabilities like web search, cryptocurrency price lookups, on-chain data fetching, address transaction tracking, and URL content extraction.
*   **State Management:** A Pydantic model (`AgentState` in `state.py`) holds the data passed between steps in the LangGraph workflow.

## Components

### `agent.py`
*   Defines the `AgentState` class to track the agent's progress.
*   Implements the core agent logic using a `langgraph.StateGraph` built in `graph.py`.
*   Contains node functions for each step of the workflow (defined in `graph.py`):
    *   `clarify_node`: Checks if the question needs clarification.
    *   `ask_user_node`: Prompts the user for clarification (interactive).
    *   `generate_subqueries_node`: Breaks the question into subqueries (using BAML).
    *   `plan_node`: Plans tool usage for subqueries (using BAML).
    *   `gather_info_node`: Executes the plan using tools from the `tools/` directory.
    *   `filter_results_node`: Ranks and filters search results (using BAML).
    *   `answer_node`: Generates the final answer (using BAML).
    *   `critique_node`: Critiques the generated answer (using BAML).
    *   `additional_search_node`: Performs follow-up searches based on critique.
*   Includes the `DeepResearchAgent` class to encapsulate the graph and execution logic.
*   Provides a `main` block to run the agent from the command line.

### `tools/` Directory
*   `web_search.py`:
    *   `web_search(query, max_results)`: Performs a general web search using Tavily and returns a list of results (content and link).
    *   `extract_content_from_url(url)`: Extracts the main textual content from a given URL using Tavily's extraction API. Requires `TAVILY_API_KEY`.
*   `get_price.py`:
    *   `get_current_price(coin_name)`: Fetches the current price of a specific cryptocurrency (using CoinGecko API) in USD. Supports common crypto names and symbols.
*   `address_transaction_tracker.py`:
    *   `get_large_transfers_for_chain(chain, addresses, threshold, **kwargs)`: Monitors specified addresses on supported blockchains (ETH, BTC, SOL, ADA, XRP, DOGE, DOT) for recent large transactions exceeding a threshold. Requires API keys for certain chains (see Setup).
*   `get_on_chain_data.py`:
    *   `get_comprehensive_on_chain_data(asset_name, **kwargs)`: Fetches timeseries metrics (e.g., active addresses, transaction counts, fees) and recent transaction status updates for a given crypto asset using the Coin Metrics Community API.

### `baml_src/` (BAML Definitions)
This directory contains the BAML files that define the structure and logic for interacting with LLMs:
*   `clients.baml`: Configures the LLM clients (e.g., API keys, model names).
*   `generators.baml`: May contain reusable BAML code snippets or configurations.
*   `clarify_question.baml`: Defines the LLM function to analyze the user's question and ask for clarification if needed.
*   `generate_subqueries.baml`: Defines the LLM function to generate relevant search subqueries.
*   `plan_steps.baml`: Defines the LLM function to create a step-by-step plan involving tool usage (including WebSearch, PriceLookup, AddressTracker, OnChainMetrics, UrlExtractor).
*   `rank_results.baml`: Defines the LLM function to rank search results based on relevance to the query.
*   `answer_question.baml`: Defines the LLM function to synthesize a final, cited answer from the gathered context.
*   `critique_answer.baml`: Defines the LLM function to evaluate the generated answer for quality and completeness.

## Workflow

![Agent Architecture](images/agent_arch.png)

The agent follows these steps, managed by LangGraph:

1.  **Clarify:** Analyze the input question. If ambiguous, generate a clarifying question.
2.  **Ask User (Conditional):** If clarification is needed, prompt the user and wait for input.
3.  **Generate Subqueries:** Break down the (potentially clarified) question into smaller, searchable queries.
4.  **Plan:** Determine which tool (`WebSearch`, `PriceLookup`, `AddressTracker`, `OnChainMetrics`, `UrlExtractor`) to use for each subquery or information need.
5.  **Gather Info:** Execute the plan, calling the appropriate tools.
6.  **Filter Results:** Use an LLM to rank the gathered information (search results, prices, transaction data, metrics summaries, extracted text) and select the most relevant items.
7.  **Generate Answer:** Synthesize a comprehensive answer based on the filtered, relevant information, including citations/sources where available.
8.  **Critique:** Evaluate the generated answer.
9.  **Refine (Conditional):** If the critique identifies missing information and the attempt limit hasn't been reached, perform an additional web search (or potentially other tool calls based on critique - *current implementation primarily uses web search*) for the missing details and loop back to generate an improved answer.
10. **End:** Return the final answer.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone git@github.com:kargarisaac/crypto_deep_research_agent.git
    cd crypto_deep_research_agent
    ```
2.  **Install dependencies:** This project uses `uv` for dependency management and virtual environments.
    *   First, ensure you have `uv` installed. If not, follow the instructions at [https://github.com/astral-sh/uv#installation](https://github.com/astral-sh/uv#installation).
    *   Create a virtual environment and install dependencies:
        ```bash
        # Create a virtual environment (e.g., named .venv)
        uv venv
        # Activate the virtual environment (syntax depends on your shell)
        # Linux/macOS bash/zsh:
        source .venv/bin/activate
        # Windows cmd:
        # .venv\Scripts\activate.bat
        # Windows PowerShell:
        # .venv\Scripts\Activate.ps1

        # Install dependencies from pyproject.toml
        uv pip install -r requirements.txt
        # Or if you have dev dependencies defined:
        # uv pip install -r requirements.txt -r requirements-dev.txt
        ```
        *(Ensure your `pyproject.toml` is configured correctly for `uv` or you have `requirements.txt` files generated)*
3.  **Configure BAML:**
    *   Ensure your BAML `clients.baml` (or equivalent configuration in `baml_src/`) is set up with the necessary LLM API keys (e.g., Gemini, OpenAI, Anthropic). Refer to BAML documentation for configuration details.
    *   Generate/update the BAML client code if you haven't already or if you modify BAML files:
        ```bash
        # Make sure your virtual environment is active
        baml-cli generate
        ```
        *(You may need `baml-cli init` first if it's a fresh setup)*
4.  **Environment Variables:** Create a `.env` file in the project root or ensure the following environment variables are available in your shell session:
    *   `TAVILY_API_KEY`: Required for `web_search` and `extract_content_from_url`. Get one from [Tavily AI](https://tavily.com/).
    *   `ETHERSCAN_API_KEY`: Required by `address_transaction_tracker` for ETH. Get one from [Etherscan](https://etherscan.io/apis).
    *   `BLOCKFROST_API_KEY`: Required by `address_transaction_tracker` for ADA. Get one from [Blockfrost](https://blockfrost.io/).
    *   `SUBSCAN_API_KEY`: Required by `address_transaction_tracker` for DOT. Get one from [Subscan](https://docs.subscan.io/api-key-creation-retrieval).
    *   *(Optional)* Keys for your chosen LLM provider if configured via environment variables in `clients.baml`.

## Usage

Run the agent script directly from your terminal, providing your question:

```bash
python agent.py --question "<your question>"
```

The script will execute with the provided question (or a default general question if none is provided). It will prompt you for input if clarification is needed and then print the final answer generated by the agent.

You can also modify the default `user_question` within the `if __name__ == "__main__":` block in `agent.py`.

## Development & Cursor Integration (Optional)

The following instructions are for setting up MCP (Model Context Protocol) servers for interacting with BAML and LangGraph documentation within the Cursor IDE during development. This is *not* required to simply run the agent.

### Activate MCP servers for BAML/LangGraph Documentations

- Run the BAML MCP server:
  ```bash
  poetry run mcpdoc --urls BAMLDocs:https://docs.boundaryml.com/llms.txt \
    --transport sse \
    --port 8083 \
    --host localhost \
    --allowed-domains 'https://docs.boundaryml.com'
  ```

- Run the LangGraph MCP server:
  ```bash
  poetry run mcpdoc --urls LangGraphDocs:https://langchain-ai.github.io/langgraph/llms.txt \
    --transport sse \
    --port 8084 \
    --host localhost \
    --allowed-domains 'https://langchain-ai.github.io/'
  ```

- Inspect the server and test:
  ```bash
  npx @modelcontextprotocol/inspector
  ```

### Set MCP Servers on Cursor
- Add the following to your Cursor `mcp.json` file (usually found via `Cmd/Ctrl + Shift + P` -> `Open User Settings (JSON)` -> Search for `mcp.json`):
  ```json
  {
    "mcpServers": {
      "baml-docs": {
        "url": "http://localhost:8083/sse"
      },
      "langgraph-docs": {
        "url": "http://localhost:8084/sse"
      }
    }
  }
  ```
- Ensure the servers are running in your terminal and enabled in Cursor (check the AI settings / MCP Server status).

### Cursor Rules
Use these rules in Cursor's agent prompt when asking questions about BAML or LangGraph development in this project:

```txt
# BAML
When asked about BAML, use the "baml-docs" MCP server:
- Call the list_doc_sources tool to find available documentation sources.
- Call the fetch_docs tool to open the BAML docs index (baml_llms.txt).
- Examine the list of documentation topics for relevance.
- Call fetch_docs on the relevant documentation URL(s) to get details.
- Use the retrieved documentation content to answer the question.
```

```txt
# LangGraph
When asked about LangGraph, use the "langgraph-docs" MCP server:
- Call the list_doc_sources tool to find available documentation sources.
- Call the fetch_docs tool to open the LangGraph docs index (https://langchain-ai.github.io/langgraph/llms.txt).
- Examine the list of documentation topics for relevance.
- Call fetch_docs on the relevant documentation URL(s) to get details.
- Use the retrieved documentation content to answer the question.
```

## TODO

- [ ] Add template for output and check in the critique
- [ ] Explore [browser use](https://github.com/browser-use/browser-use).
- [ ] Expand Toolset: Integrate more tools (calculator, specific APIs like arXiv, etc.).
- [ ] Generalize `PriceLookup`: Modify the tool/mapping to handle more item types (stocks, products) or create a system for adding new lookups.
- [ ] Enhance Planning: Improve tool selection logic in `plan_steps.baml` for a larger toolset.
- [ ] Dynamic Planning: Allow the execution plan to adapt based on intermediate results.
- [ ] Multi-step Reasoning: Enable more complex sequences of tool use and information synthesis.
- [ ] Robust Tool Error Handling: Improve error handling in `gather_info_node` (retries, alternatives).
- [ ] LLM Output Validation: Add validation/retries for BAML function calls.
- [ ] Contradiction Detection: Add logic to identify and handle conflicting information from sources.
- [ ] Nuanced Critique: Make `critique_answer.baml` check for accuracy, style, specific constraints.
- [ ] Confidence Scoring: Have the agent output a confidence score for its final answer.
- [ ] Conversational Memory: Add state/logic to handle follow-up questions and conversational context.
- [ ] Streaming Output: Implement streaming for the final answer generation.
- [ ] Enhanced Evaluation Suite: Develop a comprehensive test suite for diverse questions.
- [ ] Integrate Robust Scraping Service (e.g., Firecrawl): For reliable extraction from complex/dynamic pages identified by search.
- [ ] Add Crawl4AI tool for scraping
- [ ] Add Twitter Tool: Integrate a tool to search recent tweets or user timelines.
- [ ] Add Reddit Tool: Integrate a tool to search Reddit posts/comments.
- [ ] Expand On-Chain Data Tools: Add more sources or specific metrics (e.g., DeFi protocol data, NFT activity).
