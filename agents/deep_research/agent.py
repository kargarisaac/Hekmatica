import argparse

# Import BAML-generated client and types
from baml_client.sync_client import b  # BAML synchronous client
from baml_client.types import (
    Clarification,
)

from agents.deep_research.graph import build_agent_graph
from agents.deep_research.state import AgentState
from langgraph.graph import StateGraph


class DeepResearchAgent:
    def __init__(self, graph: StateGraph, max_attempt_count: int = 2):
        self.graph = graph
        self.max_attempt_count = max_attempt_count

    def run(self, question: str, clarification_answer: str = None) -> str:
        # Initialize state with the question and optional pre-provided clarification answer
        state = AgentState(question=question, clarification_answer=clarification_answer)
        if clarification_answer:
            # If clarification answer is given, assume clarification was needed
            state.clarification = Clarification(
                needed=True, question=""
            )  # dummy Clarification since user provided detail
        # Execute the graph
        final_state: AgentState = self.graph.invoke(
            state
        )  # Use invoke() instead of run()

        # Return the actual answer string from the 'cited_answer' field
        # Also include references if available (optional, depending on use case)
        final_answer_text = ""
        references_list = []
        if final_state["answer"]:
            final_answer_text = final_state["answer"].cited_answer
            if (
                hasattr(final_state["answer"], "references")
                and final_state["answer"].references
            ):
                # Create a list of tuples (index, formatted_string) for sorting
                raw_references = []
                for ref in final_state["answer"].references:
                    if ref.source:
                        # Store index as integer for proper sorting
                        raw_references.append(
                            (ref.index, f"[{ref.index}] {ref.source}")
                        )

                # Sort based on the index (the first element of the tuple)
                raw_references.sort(key=lambda item: item[0])

                # Extract the sorted formatted strings
                references_list = [item[1] for item in raw_references]

        # Combine answer and references for output (adjust formatting as needed)
        output = final_answer_text
        if references_list:
            # The join part remains the same, just using the sorted list
            output += "\n\nReferences:\n" + "\n".join(
                f"- {ref_source}" for ref_source in references_list
            )

        return output or "No answer generated."  # Return the combined string


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Deep Research Agent")
    parser.add_argument("--question", type=str, help="The question to research")
    args = parser.parse_args()

    agent_graph = build_agent_graph()
    agent = DeepResearchAgent(agent_graph)
    user_question = (
        args.question
        or "What were the key factors leading to the fall of the Roman Empire?"
    )
    print(f"User: {user_question}")
    # Run the agent (this will ask for clarification interactively if needed)
    final_output_string = agent.run(
        user_question
    )  # Returns a string with answer + references
    # Print the final output string
    print(f"Agent Output:\n{final_output_string}")
