class Clarification {
  needed bool
  question string
}

function ClarifyQuestion(question: string) -> Clarification {
  client Gemini2FlashClient

  prompt #"""
    You are a helpful assistant analyzing a user query for clarity.
    Determine if the query needs clarification. 

    If the query is sufficiently clear and specific, output:
    - needed: false 
    - question: ""  (empty string)

    If the query is ambiguous or missing details, output:
    - needed: true 
    - question: a single, concise clarifying question to ask the user.

    Make sure to follow the output format strictly.
    
    User Query: "{{ question }}"
    ----
    {{ ctx.output_format }}
  """#
}

test clarify_no_clarification_needed {
  functions [ClarifyQuestion]
  args { question "What is Bitcoin?" }
  @@assert({{ this.needed == false }})
  @@assert({{ this.question == "" }})
}

test clarify_needs_clarification {
  functions [ClarifyQuestion]
  args { question "How do I recover my wallet?" }
  @@assert({{ this.needed == true }})
  @@assert({{ this.question|regex_match("(?i)wallet") }})
}
