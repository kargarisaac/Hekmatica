from pydantic import BaseModel
from baml_client.types import (
    Clarification,
    # Plan, # Removed Plan
    Critique,
    Answer,
    ToolName,  # Import ToolName if needed for Action
)
from typing import List, Optional, Dict, Tuple


# Define a structure for the agent's action
class AgentAction(BaseModel):
    tool_name: Optional[ToolName] = None  # Tool to use
    query: Optional[str] = None  # Query for the tool
    finish: bool = (
        False  # Signal to stop the ReAct loop and proceed to answer generation
    )
    thought: str = ""  # The reasoning behind the action


# Define the shared state for the agent's workflow
class AgentState(BaseModel):
    question: str
    clarification: Optional[Clarification] = None
    clarification_answer: Optional[str] = None
    # subqueries: List[str] = [] # Removed subqueries

    # --- ReAct Loop State ---
    # Stores the output of the ReasonAct BAML function
    action: Optional[AgentAction] = None
    # Holds the raw output of the *last* tool execution before filtering
    current_observation: Optional[Dict[str, Optional[str]]] = None
    # History of thoughts, actions, and *filtered* observation summaries
    agent_history: List[Tuple[str, str, str]] = []

    # --- Accumulated Results ---
    # Accumulates *filtered* results (observations) over the ReAct loop
    accumulated_results: List[Dict[str, Optional[str]]] = []

    # --- Final Output State ---
    # Holds the final filtered results used for the answer after the loop finishes
    final_relevant_results: List[Dict[str, Optional[str]]] = []
    answer: Optional[Answer] = None
    critique: Optional[Critique] = None
    # Holds feedback from the critique node to guide the next reasoning step
    critique_feedback: Optional[str] = None

    # --- Control Flow ---
    attempt_count: int = 1  # number of answer attempts made (for critique loop)
    max_react_loops: int = 7  # Increased safety limit slightly
    current_react_loop: int = 0  # Counter for ReAct loops
