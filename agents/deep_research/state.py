from pydantic import BaseModel
from baml_client.types import (
    Clarification,
    Plan,
    Critique,
    Answer,
)
from typing import List, Optional, Dict


# Define the shared state for the agent's workflow
class AgentState(BaseModel):
    question: str
    clarification: Optional[Clarification] = None
    clarification_answer: Optional[str] = None
    subqueries: List[str] = []
    plan: Optional[Plan] = None
    raw_results: List[Dict[str, Optional[str]]] = []
    relevant_results: List[Dict[str, Optional[str]]] = []
    answer: Optional[Answer] = None
    critique: Optional[Critique] = None
    attempt_count: int = 1  # number of answer attempts made (for loop control)
