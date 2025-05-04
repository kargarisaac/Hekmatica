// Define the available tools as an enum
// Ensure these names match the keys used in the execute_tool_node in graph.py
enum ToolName {
  WebSearch
  PriceLookup
  AddressTracker
  OnChainMetrics
  UrlExtractor
}

// Define the output structure for the agent's action
// This should match the AgentAction class in agents/deep_research/state.py
class AgentAction {
  tool_name ToolName? // Tool to use, null if finishing
  query string?       // Query for the tool, null if finishing
  finish bool         // True if the agent should stop searching and generate an answer
  thought string      // The reasoning process leading to this action/decision
}

// Define an input structure for history items
class HistoryItem {
  thought string
  action string // Summary of the previous action (e.g., "WebSearch('AI fairness')")
  observation string // Summary of the *filtered* observation from the action
}

// The main reasoning function
function ReasonAct(
  question: string,
  clarification_details: string?,
  history: HistoryItem[],
  critique_feedback: string? // Added input for critique feedback
) -> AgentAction {
  // Use your preferred LLM client that supports function calling/structured output
  // Ensure the client is configured in your BAML project settings
  client Gemini2FlashClient // Example client

  prompt #"
You are a helpful research assistant following the ReAct framework (Reason, Act, Observe). Your goal is to answer the user's question thoroughly by reasoning about the required information, acting by selecting the appropriate tool, and observing the filtered results from the tool execution.

User Question: {{question}}
{% if clarification_details %}
User Clarification: {{clarification_details}}
{% endif %}

Available Tools:
- WebSearch(query: string): Searches the web for general knowledge, recent events, opinions, or specific documents. Returns snippets and links.
- PriceLookup(coin_name: string): Gets the current price of a cryptocurrency (e.g., 'bitcoin', 'ethereum', 'solana'). Returns the price string (e.g., '$65000.00') or an error.
- AddressTracker(query: string): Tracks recent large transactions for a specific blockchain address. Query format: 'chain:address' (e.g., 'eth:0x123...', 'sol:abc...', 'btc:bc1q...'). Returns a summary of activity or an error.
- OnChainMetrics(asset_name: string): Gets recent on-chain metrics (like active addresses, transaction count) for an asset (e.g., 'btc', 'eth', 'sol'). Returns a data summary or an error.
- UrlExtractor(url: string): Extracts the main text content from a given URL. Use this *after* a WebSearch finds a promising link. Returns the extracted text or an error.

ReAct History (Thought -> Action -> Filtered Observation):
{% for item in history %}
Thought: {{ item.thought }}
Action: {{ item.action }}
Observation: {{ item.observation }}
---
{% endfor %}

{% if critique_feedback %}
Critique Feedback from Last Attempt:
"{{ critique_feedback }}"
**You MUST prioritize addressing this feedback in your next action.** Analyze the critique and decide how to best gather the missing information or correct the previous approach using the available tools.
{% endif %}

Current Task: Based on the original question, the history, and **especially any critique feedback provided**, decide the next best action.

Your thought process should be:
1. Analyze the original question, the information gathered so far (history), and **critically evaluate any critique feedback**.
2. If critique feedback exists: Determine the core issue (e.g., missing data point, wrong comparison, insufficient detail). Select the best tool and formulate a query to *directly address* that critique.
3. If no critique feedback: Identify the *most important* piece of missing information needed to answer the original question comprehensively based on the current history.
4. Choose the *single best tool* from the available list to acquire that specific piece of information. Formulate a precise and effective query for the chosen tool.
5. If you are confident that you have gathered sufficient information (considering the history and having addressed any critique) to construct a complete and accurate final answer, decide to finish. Avoid redundant tool calls unless necessary to get updated information (like price).

Output Format:
Provide your step-by-step reasoning in the 'thought' field. Explain *why* you are choosing a specific tool/query or deciding to finish, referencing the history and critique feedback as needed.
Then, specify the 'tool_name' and 'query' if taking an action.
Set 'finish' to true ONLY if you are ready to generate the final answer. Otherwise, set 'finish' to false.

Thought: (Your reasoning here...)
Action: (Set tool_name/query OR set finish=true)
"""#
}
