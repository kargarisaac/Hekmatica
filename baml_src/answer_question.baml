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
test answer_with_general_context {
  functions [AnswerQuestion]
  args {
    question "How does photosynthesis work in plants?"
    context [
      { 
        content "Photosynthesis uses sunlight, water, and carbon dioxide to create glucose (sugar) and oxygen.", 
        source "http://example.com/photosynthesis-basics" 
      },
      { 
        content "Chlorophyll, the green pigment in leaves, absorbs sunlight.", 
        source "http://example.com/chlorophyll-role"
      },
      { 
        content "The process primarily occurs in chloroplasts within plant cells.", 
        source "http://example.com/chloroplasts" 
      },
      { 
        content "Oxygen is released as a byproduct.", 
        source null // Example with no source
      }
    ]
  }
  @@assert({{ this.cited_answer != ""}})
  @@assert({{ "glucose" in this.cited_answer or "oxygen" in this.cited_answer or "chlorophyll" in this.cited_answer }})
  @@assert({{ "[0]" in this.cited_answer or "[1]" in this.cited_answer or "[2]" in this.cited_answer or "[3]" in this.cited_answer }})
  // Check if references are generated correctly (at least the ones with sources)
  @@assert({{ this.references | length >= 2 }})
  @@assert({{ "http://example.com/photosynthesis-basics" in (this.references | map(attribute='source') | list) }})
}
