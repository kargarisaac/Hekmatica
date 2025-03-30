###############################################################################
#
#  Welcome to Baml! To use this generated code, please run the following:
#
#  $ pip install baml-py
#
###############################################################################

# This file was generated by BAML: please do not edit it. Instead, edit the
# BAML files and re-generate this code.
#
# ruff: noqa: E501,F401,F821
# flake8: noqa: E501,F401,F821
# pylint: disable=unused-import,line-too-long
# fmt: off

file_map = {
    
    "answer_question.baml": "// Define a class to represent a structured context item\nclass ContextItem {\n  content string\n  source string? // Source/link is optional\n}\n\nclass Source {\n  index int\n  source string\n  source_type string\n}\n// AnswerQuestion: Compose a final answer using the question and structured context info\nclass Answer {\n  cited_answer string @description(\"The final answer with inline citations like [0], [1] referring to the context items.\")\n  // Updated references to be a list of strings\n  references Source[] @description(\"A numerical list of source URLs/identifiers corresponding to the citations used in the answer.\")\n}\n\n// Updated function signature to accept a list of ContextItem objects\nfunction AnswerQuestion(question: string, context: ContextItem[]) -> Answer {\n  client Gemini2FlashClient\n\n  prompt #\"\"\"\n    You are an expert writing a detailed answer to the user's question using the provided structured context information.\n    Use the context items to ensure accuracy and completeness.\n    **Cite the context items used for each part of your answer using bracketed numbers corresponding to the list below (e.g., [0], [1]).**\n    Integrate the information naturally. Do not just list the context content verbatim.\n    If the context contains a current price or specific data, include it in the answer with its citation.\n    After generating the `cited_answer`, list all the `source` fields from the context items you actually cited in the `references` field. Only include sources that were cited. If a cited item has no source, omit it from the references list.\n    The answer should fully address the question.\n\n    Question: {{ question }}\n\n    Context Items:\n    // Updated context loop to iterate over ContextItem objects and access their fields\n    {% for item in context %}\n    [{{ loop.index0 }}] Content: {{ item.content }}\n       Source: {{ item.source or \"N/A\" }}\n    {% endfor %}\n\n    ----\n    {{ ctx.output_format }}\n  \"\"\"#\n}\n\n// Tests for AnswerQuestion\ntest answer_with_context {\n  functions [AnswerQuestion]\n  args {\n    question \"What are the benefits of blockchain in finance?\"\n    context [\n      { \n        content \"Blockchain allows decentralized transactions\" \n        source \"http://example.com/decentralized\" \n      }\n      { \n        content \"It increases transparency and security\" \n        source \"http://example.com/security\" \n      }\n      { \n        content \"Current Bitcoin price: $60,000\" \n        source null \n      } // Example with no source\n    ]\n  }\n  @@assert({{ this.cited_answer != \"\"}})\n  @@assert({{ \"transparency\" in this.cited_answer or \"security\" in this.cited_answer }})\n  @@assert({{ \"[0]\" in this.cited_answer or \"[1]\" in this.cited_answer or \"[2]\" in this.cited_answer }})\n}\n",
    "clarify_question.baml": "class Clarification {\n  needed bool\n  question string\n}\n\nfunction ClarifyQuestion(question: string) -> Clarification {\n  client Gemini2FlashClient\n\n  prompt #\"\"\"\n    You are a helpful assistant analyzing a user query for clarity.\n    Determine if the query needs clarification. \n\n    If the query is sufficiently clear and specific, output:\n    - needed: false \n    - question: \"\"  (empty string)\n\n    If the query is ambiguous or missing details, output:\n    - needed: true \n    - question: a single, concise clarifying question to ask the user.\n\n    Make sure to follow the output format strictly.\n    \n    User Query: \"{{ question }}\"\n    ----\n    {{ ctx.output_format }}\n  \"\"\"#\n}\n\ntest clarify_no_clarification_needed {\n  functions [ClarifyQuestion]\n  args { question \"What is Bitcoin?\" }\n  @@assert({{ this.needed == false }})\n  @@assert({{ this.question == \"\" }})\n}\n\ntest clarify_needs_clarification {\n  functions [ClarifyQuestion]\n  args { question \"How do I recover my wallet?\" }\n  @@assert({{ this.needed == true }})\n  @@assert({{ this.question|regex_match(\"(?i)wallet\") }})\n}\n",
    "clients.baml": "// Learn more about clients at https://docs.boundaryml.com/docs/snippets/clients/overview\n\nclient<llm> CustomGPT4o {\n  provider openai\n  options {\n    model \"gpt-4o\"\n    api_key env.OPENAI_API_KEY\n  }\n}\n\nclient<llm> CustomGPT4oMini {\n  provider openai\n  retry_policy Exponential\n  options {\n    model \"gpt-4o-mini\"\n    api_key env.OPENAI_API_KEY\n  }\n}\n\nclient<llm> CustomSonnet {\n  provider anthropic\n  options {\n    model \"claude-3-5-sonnet-20241022\"\n    api_key env.ANTHROPIC_API_KEY\n  }\n}\n\n\nclient<llm> CustomHaiku {\n  provider anthropic\n  retry_policy Constant\n  options {\n    model \"claude-3-haiku-20240307\"\n    api_key env.ANTHROPIC_API_KEY\n  }\n}\n\nclient<llm> Gemini2FlashClient {\n  provider \"google-ai\"\n  options {\n    model \"gemini-2.0-flash\"\n    api_key env.GEMINI_API_KEY\n  }\n}\n\n// https://docs.boundaryml.com/docs/snippets/clients/round-robin\nclient<llm> CustomFast {\n  provider round-robin\n  options {\n    // This will alternate between the two clients\n    strategy [CustomGPT4oMini, CustomHaiku]\n  }\n}\n\n// https://docs.boundaryml.com/docs/snippets/clients/fallback\nclient<llm> OpenaiFallback {\n  provider fallback\n  options {\n    // This will try the clients in order until one succeeds\n    strategy [CustomGPT4oMini, CustomGPT4oMini]\n  }\n}\n\n// https://docs.boundaryml.com/docs/snippets/clients/retry\nretry_policy Constant {\n  max_retries 3\n  // Strategy is optional\n  strategy {\n    type constant_delay\n    delay_ms 200\n  }\n}\n\nretry_policy Exponential {\n  max_retries 2\n  // Strategy is optional\n  strategy {\n    type exponential_backoff\n    delay_ms 300\n    multiplier 1.5\n    max_delay_ms 10000\n  }\n}",
    "critique_answer.baml": "// CritiqueAnswer: Verify the answer's quality and identify missing information if any\nclass Critique {\n  is_good bool\n  missing_info string\n}\n\nfunction CritiqueAnswer(question: string, answer: string) -> Critique {\n  client Gemini2FlashClient\n\n  prompt #\"\"\"\n    You are a critical evaluator of the assistant's answer.\n    Evaluate the answer against the question:\n    - If the answer is fully correct, addresses all parts of the question, and is sufficiently detailed, set is_good to true and missing_info to \"\".\n    - If something is missing, incorrect, or not thoroughly answered, set is_good to false and provide missing_info: a short phrase indicating what info is missing or needs correction (suitable for a search query). Do NOT write a full sentence, just keywords or a brief topic.\n\n    Question: \"{{ question }}\"\n    Answer: \"{{ answer }}\"\n    \n    {{ ctx.output_format }}\n  \"\"\"#\n}\n\n// Tests for CritiqueAnswer\ntest critique_complete_answer {\n  functions [CritiqueAnswer]\n  args { \n    question \"What is 2+2?\", \n    answer \"2+2 is 4.\" \n  }\n  @@assert({{ this.is_good == true }})\n  @@assert({{ this.missing_info == \"\" }})\n}\n\ntest critique_incomplete_answer {\n  functions [CritiqueAnswer]\n  args { \n    question \"What are the benefits and risks of Bitcoin?\", \n    answer \"Bitcoin's benefits include decentralization and fast transactions.\" \n  }\n  // The answer did not cover risks, expect critique to flag missing info about risks\n  @@assert({{ this.is_good == false }})\n  @@assert({{ \"risk\" in this.missing_info | lower() }})\n}\n",
    "generate_subqueries.baml": "// GenerateSubqueries: Create multiple search queries based on the question (and clarification if provided)\nfunction GenerateSubqueries(question: string, clarification_details: string) -> string[] {\n  client Gemini2FlashClient\n\n  prompt #\"\"\"\n    You are a query generation assistant. Create 2 to 5 diverse search queries to find information for answering the question.\n    If additional clarification is provided, incorporate that detail.\n    Make each query concise and focused on an aspect of the question.\n    \n    Question: \"{{ question }}\"\n    {% if clarification_details %}\n    Additional detail: \"{{ clarification_details }}\"\n    {% endif %}\n    \n    {{ ctx.output_format }}\n  \"\"\"#\n}\n\n// Tests for GenerateSubqueries\ntest generate_subqueries_basic {\n  functions [GenerateSubqueries]\n  args { question \"What is blockchain technology used for?\", clarification_details \"\" }\n  // Expect at least 2 subqueries returned\n  @@assert({{ this|length >= 2 }})\n  @@assert({{ this[0]|regex_match(\".*\") }})\n}\n\ntest generate_subqueries_with_clarification {\n  functions [GenerateSubqueries]\n  args { question \"How to mine cryptocurrency?\", clarification_details \"Bitcoin\" }\n  // Expect queries specifically about mining Bitcoin\n  @@assert({{ this[0]|regex_match(\".*Bitcoin.*\") or this[0]|regex_match(\".*BTC.*\") or this[1]|regex_match(\".*Bitcoin.*\") or this[1]|regex_match(\".*BTC.*\") }})\n}\n",
    "generators.baml": "// This helps use auto generate libraries you can use in the language of\n// your choice. You can have multiple generators if you use multiple languages.\n// Just ensure that the output_dir is different for each generator.\ngenerator target {\n    // Valid values: \"python/pydantic\", \"typescript\", \"ruby/sorbet\", \"rest/openapi\"\n    output_type \"python/pydantic\"\n\n    // Where the generated code will be saved (relative to baml_src/)\n    output_dir \"../\"\n\n    // The version of the BAML package you have installed (e.g. same version as your baml-py or @boundaryml/baml).\n    // The BAML VSCode extension version should also match this version.\n    version \"0.81.3\"\n\n    // Valid values: \"sync\", \"async\"\n    // This controls what `b.FunctionName()` will be (sync or async).\n    default_client_mode sync\n}\n",
    "plan_steps.baml": "// PlanSteps: Decide which tools and steps are needed to answer the question\nenum Tool {\n  WebSearch \n  PriceLookup\n}\n\nclass Step {\n  tool Tool\n  query string\n}\n\nclass Plan {\n  steps Step[]\n}\n\nfunction PlanSteps(question: string, subqueries: string[]) -> Plan {\n  client Gemini2FlashClient\n\n  prompt #\"\"\"\n    You are a planning assistant with access to the following tools:\n    - WebSearch: use this to search the web for information.\n    - PriceLookup: use this to get the current price of a cryptocurrency.\n    \n    Given the user question and potential subqueries, create a step-by-step plan using these tools to gather information.\n    - If the question explicitly asks for a current price or price-related info of a cryptocurrency, include a PriceLookup step for that coin.\n    - For other informational needs, use one or more WebSearch steps (one per subquery or topic aspect).\n    - Use at most 5 steps in total. Include only relevant steps.\n    \n    User Question: \"{{ question }}\"\n    Candidate Subqueries:\n    {% for q in subqueries %}\n    - {{ q }}\n    {% endfor %}\n    \n    ----\n    {{ ctx.output_format }}\n  \"\"\"#\n}\n\n// Tests for PlanSteps\ntest plan_steps_info_question {\n  functions [PlanSteps]\n  args { \n    question \"What is Ethereum and how does it differ from Bitcoin?\", \n    subqueries [\"what is Ethereum\", \"Ethereum vs Bitcoin differences\"] \n  }\n  // Expect only WebSearch steps (no PriceLookup needed)\n  @@assert({{ (this.steps|selectattr('tool', 'equalto', Tool.PriceLookup)|list)|length == 0 }})\n  @@assert({{ this.steps | length >= 1 }})\n}\n\ntest plan_steps_price_question {\n  functions [PlanSteps]\n  args { \n    question \"What is the current price of Bitcoin?\", \n    subqueries [\"Bitcoin price\"] \n  }\n  // Expect a PriceLookup step for Bitcoin\n  @@assert({{ (this.steps|selectattr('tool', 'equalto', Tool.PriceLookup)|list)|length > 0 }})\n}\n",
    "rank_results.baml": "// baml_src/rank_results.baml\n\n// Define the structure of a single search result item\nclass ResultItem {\n  content string?\n  link string?\n}\n\n// Define the structure for a result with its relevance score\nclass RankedResultItem {\n  content string?\n  link string?\n  relevance_score int @description(\"Relevance score from 0 (not relevant) to 10 (highly relevant)\")\n}\n\n// Define the function to score and rank results\nfunction RankResults(\n  question: string,\n  subqueries: string[], // Provides context on why results were fetched\n  results: ResultItem[], // The raw results to be ranked\n  top_k: int // Number of top results to return\n) -> RankedResultItem[] { // Returns the top_k scored and ranked results\n\n  client Gemini2FlashClient // Or your preferred LLM client\n\n  prompt #\"\nAnalyze the following search results based on their relevance and usefulness for answering the main question: \"{{question}}\".\nThe results were gathered based on these subqueries:\n{% for sq in subqueries %}- {{ sq }}\n{% endfor %}\n\nConsider how well each result addresses the core intent of the question and subqueries.\n\nFor EACH result provided below, assign a relevance_score between 0 (not relevant) and 10 (highly relevant).\n\nThen, return ONLY the top {{ top_k }} results, ordered from highest relevance_score to lowest.\nDo not include results with a score below 3 (or adjust threshold if needed).\nDo not add explanations or commentary outside the structured output.\nMaintain the original content and link for each result you return, and include the assigned relevance_score.\n\nResults to score and rank:\n{% for item in results %}{% if item.content %}\nResult Index: {{ loop.index0 }}\nContent: {{ item.content }}\n{% if item.link %}Link: {{ item.link }}{% endif %}\n\n{% endif %}{% endfor %}\n\nOutput ONLY the ranked list of the top {{ top_k }} relevant results (score >= 3) in the specified BAML class format (list<RankedResultItem>).\nExample output format for top_k=2:\n[\n  {\n    content: \"Highly relevant content snippet 1...\",\n    link: \"http://example.com/link1\",\n    relevance_score: 9\n  },\n  {\n    content: \"Moderately relevant content snippet 2 (no link)...\",\n    link: null,\n    relevance_score: 7\n  }\n]\n\n{{ ctx.output_format }}\n\"#\n}\n\n// Optional: Add a test case\ntest TestRankResults {\n  functions [RankResults]\n  args {\n    question \"How to mine Bitcoin?\"\n    top_k 5\n    subqueries [\"Bitcoin mining process\", \"Bitcoin mining hardware\", \"Bitcoin mining software\"]\n    results [\n      {\n        content \"Bitcoin mining is the process of adding transaction records...\",\n        link \"http://example.com/bitcoin-mining-process\"\n      },\n      {\n        content \"ASIC miners are specialized hardware for Bitcoin mining.\",\n        link \"http://example.com/bitcoin-mining-hardware\"\n      },\n      {\n        content \"Ethereum uses a different consensus mechanism.\",\n        link \"http://example.com/ethereum-info\"\n      },\n      {\n        content \"Popular Bitcoin mining software includes CGMiner and BFGMiner.\",\n        link \"http://example.com/bitcoin-mining-software\"\n      },\n       {\n        content \"Cloud mining allows you to rent hash power.\",\n        link \"http://example.com/cloud-mining\"\n      },\n      {\n        content \"Dogecoin price prediction for next year.\",\n        link \"http://example.com/doge-price\"\n      },\n       {\n        content \"Setting up a Bitcoin wallet is the first step.\",\n        link: \"http://example.com/bitcoin-wallet\"\n       }\n    ]\n  }\n  @@assert({{ this|length == 5 }})\n} ",
}

def get_baml_files():
    return file_map