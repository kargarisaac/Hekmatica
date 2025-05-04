from agents.deep_research.agent import DeepResearchAgent
from agents.deep_research.graph import build_agent_graph

agent_graph = build_agent_graph()
agent = DeepResearchAgent(agent_graph)


def main():
    question = input("Enter a question: ")
    # Provide a dummy clarification answer to bypass the interactive input() in ask_user_node
    # This signals to the agent logic that clarification (if needed) has already been "provided".
    # Use a non-empty string; an empty string might be interpreted differently depending on logic.
    dummy_clarification = "[Clarification skipped in Studio]"
    answer = agent.run(question, clarification_answer=dummy_clarification)
    print(answer)


if __name__ == "__main__":
    main()
