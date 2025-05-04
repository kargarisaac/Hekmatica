// Define the structure for a raw result/observation item
// Matches the format produced by execute_tool_node
class ObservationItem {
  content string?
  link string?
  error string? // Include error field if tools can return errors
}

// Define the structure for a filtered, relevant result item
// This is what will be accumulated in the state
class FilteredItem {
  content string
  source string? // Use 'source' to align with AnswerQuestion context
}

// Function to filter raw observations for relevance
function FilterResults(
  question: string,
  results: ObservationItem[] // Takes a list, even if usually just one observation
) -> FilteredItem[] { // Returns a list of relevant items

  client Gemini2FlashClient // Use a fast and capable client

  prompt #"
You are an information filter. Your task is to analyze the provided observation(s) based on their relevance to the original user question.

User Question: "{{ question }}"

Observation(s) to Filter:
{% for item in results %}
--- Observation {{ loop.index0 }} ---
{% if item.content %}Content: {{ item.content }}{% endif %}
{% if item.link %}Link: {{ item.link }}{% endif %}
{% if item.error %}Error: {{ item.error }}{% endif %}
{% if not item.content and not item.link and not item.error %} [Empty Observation] {% endif %}
--- End Observation {{ loop.index0 }} ---
{% endfor %}

Instructions:
1. Evaluate each observation's content (or error message) for direct relevance to answering the user's question.
2. Ignore observations that are errors unrelated to the question (e.g., API timeouts) or content that is clearly off-topic.
3. For relevant observations:
    - Extract the core information relevant to the question from the 'content' field. Summarize slightly if necessary, but retain key facts/data.
    - Use the 'link' field as the 'source' if available. If there's an error message that *is* relevant (e.g., "Price not found for XYZ coin"), use the error message as the content and set source to null.
4. Return ONLY the relevant items as a list of FilteredItem objects.
5. If NO observations are relevant, return an empty list: [].

Output ONLY the list of FilteredItem objects.

{{ ctx.output_format }}
"#
}

// Test case: Relevant content
test FilterRelevantContent {
  functions [FilterResults]
  args {
    question "What is the price of Bitcoin?"
    results [
      { 
        content "The current price of Bitcoin is $65,000."
        link "http://price-api.com/btc" 
      }
    ]
  }
  @@assert( {{ this | length == 1 }} )
  @@assert( {{ "$65,000" in this[0].content }} )
  @@assert( {{ this[0].source == "http://price-api.com/btc" }} )
}

// Test case: Irrelevant content
test FilterIrrelevantContent {
  functions [FilterResults]
  args {
    question "What is the price of Bitcoin?"
    results [
      { 
        content "Ethereum is a popular altcoin."
        link "http://crypto-info.com/eth" 
      }
    ]
  }
  @@assert( {{ this | length == 0 }} ) // Expect empty list
}

// Test case: Relevant error
test FilterRelevantError {
  functions [FilterResults]
  args {
    question "What is the price of NonExistentCoin?"
    results [
      { 
        error "Could not find price data for NonExistentCoin" 
      }
    ]
  }
   @@assert( {{ this | length == 1 }} )
   @@assert( {{ "Could not find price data" in this[0].content }} )
   @@assert( {{ this[0].source == null }} )
}

// Test case: Irrelevant error
test FilterIrrelevantError {
  functions [FilterResults]
  args {
    question "What is the price of Bitcoin?"
    results [
      { 
        error "API connection timeout" 
      }
    ]
  }
   @@assert( {{ this | length == 0 }} ) // Expect empty list
}

// Test case: Mixed results
test FilterMixedResults {
  functions [FilterResults]
  args {
    question "Compare Bitcoin and Ethereum prices."
    results [
      { 
        content "Bitcoin price: $65,000"
        link "http://price.com/btc" 
      }
      { 
        content "Ethereum price: $3,500"
        link "http://price.com/eth" 
      }
      { 
        content "Solana is fast."
        link "http://sol.com" 
      }
    ]
  }
  @@assert( {{ this | length == 2 }} ) // Expect BTC and ETH results
  @@assert( {{ this | map(attribute='source') | contains("http://price.com/btc") }} )
  @@assert( {{ this | map(attribute='source') | contains("http://price.com/eth") }} )
} 