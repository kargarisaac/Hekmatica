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
test TestRankResultsGeneral {
  functions [RankResults]
  args {
    question "What are the benefits of renewable energy sources?"
    top_k 3
    subqueries ["advantages of solar power", "benefits of wind energy", "renewable energy vs fossil fuels"]
    results [
      {
        content "Solar power significantly reduces electricity bills and carbon footprint.",
        link "http://example.com/solar-benefits"
      },
      {
        content "Wind turbines can be noisy and impact bird populations.",
        link "http://example.com/wind-drawbacks"
      },
      {
        content "Fossil fuels are a major contributor to climate change.",
        link "http://example.com/fossil-fuel-impacts"
      },
      {
        content "Renewable energy sources like wind and solar offer long-term sustainability.",
        link "http://example.com/renewable-sustainability"
      },
       {
        content "Geothermal energy provides a constant power supply.",
        link "http://example.com/geothermal-info"
      },
      {
        content "The process of installing solar panels on a home.",
        link "http://example.com/solar-installation"
      }
    ]
  }
  // Assert that we get the requested number of results (top_k)
  @@assert({{ this|length == 3 }})
  // Assert that the top result has a high score (e.g., >= 7)
  @@assert({{ this[0].relevance_score >= 7 }})
  // Assert that the last result returned still has a reasonable score (e.g., >= 3)
  @@assert({{ this[-1].relevance_score >= 3 }})
} 