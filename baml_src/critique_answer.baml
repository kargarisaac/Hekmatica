// CritiqueAnswer: Verify the answer's quality and identify missing information if any
class Critique {
  is_good bool
  missing_info string @description("If is_good is false, a short phrase indicating what info is missing or needs correction (suitable for a search query). Empty if is_good is true.")
  critique string @description("A brief explanation for why the answer is good or bad.")
}

function CritiqueAnswer(question: string, answer: string) -> Critique {
  client Gemini2FlashClient

  prompt #"""
    You are a critical evaluator of the assistant's answer.
    Evaluate the answer against the question:
    - If the answer is fully correct, addresses all parts of the question, and is sufficiently detailed:
      - Set is_good to true.
      - Set missing_info to "".
      - Set critique to a brief confirmation (e.g., "Answer is complete and accurate.").
    - If something is missing, incorrect, or not thoroughly answered:
      - Set is_good to false.
      - Provide missing_info: a short phrase indicating what info is missing or needs correction (suitable for a search query). Do NOT write a full sentence, just keywords or a brief topic.
      - Set critique to a brief explanation of the main issue (e.g., "Answer does not mention risks.", "Comparison is incomplete.").

    Question: "{{ question }}"
    Answer: "{{ answer }}"
    
    {{ ctx.output_format }}
  """#
}

// Tests for CritiqueAnswer
test critique_complete_answer {
  functions [CritiqueAnswer]
  args { 
    question "What is 2+2?", 
    answer "2+2 is 4." 
  }
  @@assert({{ this.is_good == true }})
  @@assert({{ this.missing_info == "" }})
  @@assert({{ this.critique | length > 5 }})
}

test critique_incomplete_answer {
  functions [CritiqueAnswer]
  args { 
    question "What are the benefits and risks of Bitcoin?", 
    answer "Bitcoin's benefits include decentralization and fast transactions." 
  }
  // The answer did not cover risks, expect critique to flag missing info about risks
  @@assert({{ this.is_good == false }})
  @@assert({{ "risk" in this.missing_info | lower() }})
  @@assert({{ "risk" in this.critique | lower() }})
}

test critique_incomplete_general_answer {
  functions [CritiqueAnswer]
  args { 
    question "Describe the water cycle, including evaporation and precipitation.", 
    answer "The water cycle involves water evaporating from the surface due to heat." 
  }
  // The answer only mentioned evaporation, not precipitation. Expect critique to flag missing info about precipitation.
  @@assert({{ this.is_good == false }})
  @@assert({{ "precipitation" in this.missing_info | lower() or "rainfall" in this.missing_info | lower() }})
  @@assert({{ "precipitation" in this.critique | lower() or "rainfall" in this.critique | lower() }})
}
