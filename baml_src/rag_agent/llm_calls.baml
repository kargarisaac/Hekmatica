// baml_src/rag_agent/__init__.baml
class SubQuestions {
  questions string[]
}

// Function to rewrite the query using HyDE principle
function RewriteQuery(question: string) -> string {
  client Gemini2_5FlashClient
  prompt #"
    Write a detailed possible answer to the user question so the answer itself works as a search query.
    Question: {{ question }}
    Answer:
  "#
}

// Function to answer the question based on context
function AnswerQuestionWithContext(question: string, context: string) -> string {
  client Gemini2_5FlashClient
  prompt #"
    Use the context to answer accurately. If the answer isn't there, say 'I don't know'.
    Context:
    {{ context }}

    Question: {{ question }}
    Answer:
  "#
}

// Function to decompose a question into sub-questions for self-ask
function DecomposeQuestion(question: string) -> SubQuestions {
  client Gemini2_5FlashClient
  prompt #"
    Decompose the following question into 2-3 self-contained sub-questions that would help answer the main question. Respond ONLY with a JSON object containing a single key \"questions\" which is a list of strings.

    Example Question: What are the main features of LangGraph and how do they compare to BAML?
    Example Output:
    ```json
    {
      \"questions\": [
        \"What are the main features of LangGraph?\".
        \"What are the main features of BAML?\".
        \"How do LangGraph and BAML features compare?\"
      ]
    }
    ```

    Question: {{ question }}

    Output:
  "#
}

// Function to synthesize answers to sub-questions into a final answer
function SynthesizeAnswers(question: string, sub_answers: string[]) -> string {
  client Gemini2_5FlashClient
  prompt #"
    You are given a main question and several context passages gathered from answering sub-questions derived from the main question. Synthesize these passages into a single, comprehensive answer to the main question.

    Main Question: {{ question }}

    Context Passages (from sub-answers):
    {% for ans in sub_answers %}
    - {{ ans }}
    {% endfor %}

    Synthesized Answer:
  "#
}
