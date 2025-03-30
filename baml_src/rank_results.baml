// baml_src/rank_results.baml

// Define the structure of a single search result item
class ResultItem {
  content string?
  link string?
}

// Define the structure for a result with its relevance score
class RankedResultItem {
  content string?
  link string?
  relevance_score int @description("Relevance score from 0 (not relevant) to 10 (highly relevant)")
}

// Define the function to score and rank results
function RankResults(
  question: string,
  subqueries: string[], // Provides context on why results were fetched
  results: ResultItem[], // The raw results to be ranked
  top_k: int // Number of top results to return
) -> RankedResultItem[] { // Returns the top_k scored and ranked results

  client Gemini2FlashClient // Or your preferred LLM client

  prompt #"
Analyze the following search results based on their relevance and usefulness for answering the main question: "{{question}}".
The results were gathered based on these subqueries:
{% for sq in subqueries %}- {{ sq }}
{% endfor %}

Consider how well each result addresses the core intent of the question and subqueries.

For EACH result provided below, assign a relevance_score between 0 (not relevant) and 10 (highly relevant).

Then, return ONLY the top {{ top_k }} results, ordered from highest relevance_score to lowest.
Do not include results with a score below 3 (or adjust threshold if needed).
Do not add explanations or commentary outside the structured output.
Maintain the original content and link for each result you return, and include the assigned relevance_score.

Results to score and rank:
{% for item in results %}{% if item.content %}
Result Index: {{ loop.index0 }}
Content: {{ item.content }}
{% if item.link %}Link: {{ item.link }}{% endif %}

{% endif %}{% endfor %}

Output ONLY the ranked list of the top {{ top_k }} relevant results (score >= 3) in the specified BAML class format (list<RankedResultItem>).
Example output format for top_k=2:
[
  {
    content: "Highly relevant content snippet 1...",
    link: "http://example.com/link1",
    relevance_score: 9
  },
  {
    content: "Moderately relevant content snippet 2 (no link)...",
    link: null,
    relevance_score: 7
  }
]

{{ ctx.output_format }}
"#
}

// Optional: Add a test case
test TestRankResults {
  functions [RankResults]
  args {
    question "How to mine Bitcoin?"
    top_k 5
    subqueries ["Bitcoin mining process", "Bitcoin mining hardware", "Bitcoin mining software"]
    results [
      {
        content "Bitcoin mining is the process of adding transaction records...",
        link "http://example.com/bitcoin-mining-process"
      },
      {
        content "ASIC miners are specialized hardware for Bitcoin mining.",
        link "http://example.com/bitcoin-mining-hardware"
      },
      {
        content "Ethereum uses a different consensus mechanism.",
        link "http://example.com/ethereum-info"
      },
      {
        content "Popular Bitcoin mining software includes CGMiner and BFGMiner.",
        link "http://example.com/bitcoin-mining-software"
      },
       {
        content "Cloud mining allows you to rent hash power.",
        link "http://example.com/cloud-mining"
      },
      {
        content "Dogecoin price prediction for next year.",
        link "http://example.com/doge-price"
      },
       {
        content "Setting up a Bitcoin wallet is the first step.",
        link: "http://example.com/bitcoin-wallet"
       }
    ]
  }
  @@assert({{ this|length == 5 }})
} 