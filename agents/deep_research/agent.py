import argparse

# Import BAML-generated client and types
from baml_client.sync_client import b
from baml_client.types import (
    Clarification,
)

from agents.deep_research.graph import build_agent_graph
from agents.deep_research.state import AgentState
from langgraph.graph import StateGraph


class DeepResearchAgent:
    def __init__(self, graph: StateGraph, max_answer_attempts: int = 2):
        self.graph = graph
        self.max_answer_attempts = max_answer_attempts

    def run(self, question: str, clarification_answer: str = None) -> str:
        # Initialize state
        initial_state_dict = {
            "question": question,
            "clarification_answer": clarification_answer,
            "attempt_count": 1,
            "max_react_loops": 7,  # Match state default or make configurable
            "current_react_loop": 0,
            "agent_history": [],
            "accumulated_results": [],  # Initialize new field
            "final_relevant_results": [],  # Initialize new field
            "current_observation": None,  # Initialize new field
            "critique_feedback": None,  # Initialize critique feedback
            # No subqueries needed
        }

        if clarification_answer:
            initial_state_dict["clarification"] = Clarification(
                needed=True, question=""
            )

        state = AgentState(**initial_state_dict)

        # Execute the graph
        final_state_dict = self.graph.invoke(
            state,
            config={
                "recursion_limit": 25
            },  # Increased recursion limit due to tighter loop
        )

        final_state = AgentState(**final_state_dict)

        # Return the final answer string and references
        final_answer_text = ""
        references_list = []
        final_answer_obj = final_state.answer

        if final_answer_obj:
            final_answer_text = final_answer_obj.cited_answer
            if hasattr(final_answer_obj, "references") and final_answer_obj.references:
                raw_references = []
                for ref in final_answer_obj.references:
                    if hasattr(ref, "source") and ref.source and hasattr(ref, "index"):
                        raw_references.append(
                            (ref.index, f"[{ref.index}] {ref.source}")
                        )
                raw_references.sort(key=lambda item: item[0])
                references_list = [item[1] for item in raw_references]

        output = final_answer_text
        if references_list:
            output += "\n\nReferences:\n" + "\n".join(
                f"- {ref_source}" for ref_source in references_list
            )

        if not output and final_state.critique:
            output = f"Agent stopped. Reason: {final_state.critique.critique}"
        elif not output:
            output = "Agent finished, but no final answer was generated."

        return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Deep Research Agent")
    parser.add_argument("--question", type=str, help="The question to research")
    args = parser.parse_args()

    agent_graph = build_agent_graph()
    agent = DeepResearchAgent(agent_graph, max_answer_attempts=2)
    user_question = (
        args.question
        or "Compare the on-chain activity (transaction count, active addresses) of Bitcoin and Ethereum over the last month. What are their current prices?"
    )
    print(f"User: {user_question}")

    final_output_string = agent.run(user_question)
    print(f"\n===== Agent Final Output =====")
    print(final_output_string)
    print(f"==============================")
