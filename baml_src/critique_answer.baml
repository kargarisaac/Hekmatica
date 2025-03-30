// CritiqueAnswer: Verify the answer's quality and identify missing information if any
class Critique {
  is_good bool
  missing_info string
}

function CritiqueAnswer(question: string, answer: string) -> Critique {
  client Gemini2FlashClient

  prompt #"""
    You are a critical evaluator of the assistant's answer.
    Evaluate the answer against the question:
    - If the answer is fully correct, addresses all parts of the question, and is sufficiently detailed, set is_good to true and missing_info to "".
    - If something is missing, incorrect, or not thoroughly answered, set is_good to false and provide missing_info: a short phrase indicating what info is missing or needs correction (suitable for a search query). Do NOT write a full sentence, just keywords or a brief topic.

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
}
