// PlanSteps: Decide which tools and steps are needed to answer the question
enum Tool {
  WebSearch 
  PriceLookup
}

class Step {
  tool Tool
  query string
}

class Plan {
  steps Step[]
}

function PlanSteps(question: string, subqueries: string[]) -> Plan {
  client Gemini2FlashClient

  prompt #"""
    You are a planning assistant with access to the following tools:
    - WebSearch: use this to search the web for general information.
    - PriceLookup: use this to get the current price of a specific item (e.g., a stock ticker, a known commodity, a cryptocurrency). Check if the query seems to be asking for a specific item's price.
    
    Given the user question and potential subqueries, create a step-by-step plan using these tools to gather information.
    - If the question explicitly asks for a current price or price-related info of a specific, named item, consider using a PriceLookup step for that item.
    - For other informational needs, use one or more WebSearch steps (one per subquery or topic aspect).
    - Use at most 5 steps in total. Include only relevant steps.
    
    User Question: "{{ question }}"
    Candidate Subqueries:
    {% for q in subqueries %}
    - {{ q }}
    {% endfor %}
    
    ----
    {{ ctx.output_format }}
  """#
}

// Tests for PlanSteps
test plan_steps_general_info_question {
  functions [PlanSteps]
  args { 
    question "What is the main function of the mitochondria?", 
    subqueries ["mitochondria function", "cellular respiration"] 
  }
  // Expect only WebSearch steps (no PriceLookup needed)
  @@assert({{ (this.steps|selectattr('tool', 'equalto', Tool.PriceLookup)|list)|length == 0 }})
  @@assert({{ this.steps | length >= 1 }})
}

test plan_steps_potential_price_question {
  functions [PlanSteps]
  args { 
    question "What is the current price of GOOGL stock?", // Example price query
    subqueries ["GOOGL stock price"] 
  }
  // Expect a PriceLookup step (even if the tool might not support it yet, the plan should reflect intent)
  @@assert({{ (this.steps|selectattr('tool', 'equalto', Tool.PriceLookup)|list)|length > 0 }})
}

test plan_steps_crypto_price_still_works {
  functions [PlanSteps]
  args { 
    question "What is the current price of Bitcoin?", 
    subqueries ["Bitcoin price"] 
  }
  // Expect a PriceLookup step for Bitcoin (ensure original functionality retained)
  @@assert({{ (this.steps|selectattr('tool', 'equalto', Tool.PriceLookup)|list)|length > 0 }})
}
