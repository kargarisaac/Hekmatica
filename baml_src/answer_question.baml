// Define a class to represent a structured context item
class ContextItem {
  content string
  source string? // Source/link is optional
}

class Source {
  index int
  source string
  source_type string
}
// AnswerQuestion: Compose a final answer using the question and structured context info
class Answer {
  cited_answer string @description("The final answer with inline citations like [0], [1] referring to the context items.")
  // Updated references to be a list of strings
  references Source[] @description("A numerical list of source URLs/identifiers corresponding to the citations used in the answer.")
}

// Updated function signature to accept a list of ContextItem objects
function AnswerQuestion(question: string, context: ContextItem[]) -> Answer {
  client Gemini2FlashClient

  prompt #"""
    You are an expert writing a detailed answer to the user's question using the provided structured context information.
    Use the context items to ensure accuracy and completeness.
    **Cite the context items used for each part of your answer using bracketed numbers corresponding to the list below (e.g., [0], [1]).**
    Integrate the information naturally. Do not just list the context content verbatim.
    If the context contains a current price or specific data, include it in the answer with its citation.
    After generating the `cited_answer`, list all the `source` fields from the context items you actually cited in the `references` field. Only include sources that were cited. If a cited item has no source, omit it from the references list.
    The answer should fully address the question.

    Question: {{ question }}

    Context Items:
    // Updated context loop to iterate over ContextItem objects and access their fields
    {% for item in context %}
    [{{ loop.index0 }}] Content: {{ item.content }}
       Source: {{ item.source or "N/A" }}
    {% endfor %}

    ----
    {{ ctx.output_format }}
  """#
}

// Tests for AnswerQuestion
test answer_with_context {
  functions [AnswerQuestion]
  args {
    question "What are the benefits of blockchain in finance?"
    context [
      { 
        content "Blockchain allows decentralized transactions" 
        source "http://example.com/decentralized" 
      }
      { 
        content "It increases transparency and security" 
        source "http://example.com/security" 
      }
      { 
        content "Current Bitcoin price: $60,000" 
        source null 
      } // Example with no source
    ]
  }
  @@assert({{ this.cited_answer != ""}})
  @@assert({{ "transparency" in this.cited_answer or "security" in this.cited_answer }})
  @@assert({{ "[0]" in this.cited_answer or "[1]" in this.cited_answer or "[2]" in this.cited_answer }})
}
