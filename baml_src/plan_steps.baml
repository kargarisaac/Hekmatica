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
    - WebSearch: use this to search the web for information.
    - PriceLookup: use this to get the current price of a cryptocurrency.
    
    Given the user question and potential subqueries, create a step-by-step plan using these tools to gather information.
    - If the question explicitly asks for a current price or price-related info of a cryptocurrency, include a PriceLookup step for that coin.
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
test plan_steps_info_question {
  functions [PlanSteps]
  args { 
    question "What is Ethereum and how does it differ from Bitcoin?", 
    subqueries ["what is Ethereum", "Ethereum vs Bitcoin differences"] 
  }
  // Expect only WebSearch steps (no PriceLookup needed)
  @@assert({{ (this.steps|selectattr('tool', 'equalto', Tool.PriceLookup)|list)|length == 0 }})
  @@assert({{ this.steps | length >= 1 }})
}

test plan_steps_price_question {
  functions [PlanSteps]
  args { 
    question "What is the current price of Bitcoin?", 
    subqueries ["Bitcoin price"] 
  }
  // Expect a PriceLookup step for Bitcoin
  @@assert({{ (this.steps|selectattr('tool', 'equalto', Tool.PriceLookup)|list)|length > 0 }})
}
