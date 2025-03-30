// GenerateSubqueries: Create multiple search queries based on the question (and clarification if provided)
function GenerateSubqueries(question: string, clarification_details: string) -> string[] {
  client Gemini2FlashClient

  prompt #"""
    You are a query generation assistant. Create 2 to 5 diverse search queries to find information for answering the question.
    If additional clarification is provided, incorporate that detail.
    Make each query concise and focused on an aspect of the question.
    
    Question: "{{ question }}"
    {% if clarification_details %}
    Additional detail: "{{ clarification_details }}"
    {% endif %}
    
    {{ ctx.output_format }}
  """#
}

// Tests for GenerateSubqueries
test generate_subqueries_basic {
  functions [GenerateSubqueries]
  args { question "What is blockchain technology used for?", clarification_details "" }
  // Expect at least 2 subqueries returned
  @@assert({{ this|length >= 2 }})
  @@assert({{ this[0]|regex_match(".*") }})
}

test generate_subqueries_with_clarification {
  functions [GenerateSubqueries]
  args { question "How to mine cryptocurrency?", clarification_details "Bitcoin" }
  // Expect queries specifically about mining Bitcoin
  @@assert({{ this[0]|regex_match(".*Bitcoin.*") or this[0]|regex_match(".*BTC.*") or this[1]|regex_match(".*Bitcoin.*") or this[1]|regex_match(".*BTC.*") }})
}
