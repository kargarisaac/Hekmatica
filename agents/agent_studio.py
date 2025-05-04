from agents.deep_research.agent import DeepResearchAgent
from agents.deep_research.graph import build_agent_graph

agent_graph = build_agent_graph()
agent = DeepResearchAgent(agent_graph)


def main():
    question = input("Enter a question: ")
    answer = agent.run(question)
    print(answer)


if __name__ == "__main__":
    main()
