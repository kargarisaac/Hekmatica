from typing import List, Optional, Dict, Tuple
from langgraph.graph import StateGraph, END

from baml_client.sync_client import b
from baml_client.types import (
    # ResultItem, # Removed unused import
    # RankedResultItem, # Removed unused import
    ContextItem,
    ToolName,
    Critique,
    Answer,
    FilteredItem,  # Add import for FilteredItem used in filter_and_accumulate_node
)

# Import tools
from tools.get_price import get_current_price
from tools.web_search import web_search, extract_content_from_url
from tools.address_transaction_tracker import get_large_transfers_for_chain
from tools.get_on_chain_data import get_comprehensive_on_chain_data
import json

# Import AgentState and the local AgentAction definition
from agents.deep_research.state import AgentState, AgentAction


# Define node functions for each step in the workflow:
def clarify_node(state: AgentState):
    """Use LLM to determine if clarification is needed, UNLESS an answer was already provided."""

    # Check if clarification was already provided/skipped via input state
    if state.clarification_answer is not None:
        print(
            "Clarification answer provided in initial state. Skipping clarification check."
        )
        # Reset loop state but preserve the provided clarification details
        return {
            "clarification": state.clarification,  # Keep the potentially dummy clarification object
            "clarification_answer": state.clarification_answer,  # Keep the provided answer
            "current_react_loop": 0,
            "agent_history": [],
            "accumulated_results": [],
            "final_relevant_results": [],
            "current_observation": None,
            "action": None,
            "answer": None,
            "critique": None,
            "critique_feedback": None,
            "attempt_count": 1,
        }

    print("No clarification answer provided. Checking if clarification is needed.")
    # Reset state for a new run (including clearing any potential stale clarification)
    state.current_react_loop = 0
    state.agent_history = []
    state.accumulated_results = []
    state.final_relevant_results = []
    state.current_observation = None
    state.action = None
    state.answer = None
    state.critique = None
    state.critique_feedback = None
    state.attempt_count = 1

    state.clarification = b.ClarifyQuestion(question=state.question)
    return {
        "clarification": state.clarification,
        "current_react_loop": 0,
        "agent_history": [],
        "accumulated_results": [],
        "final_relevant_results": [],
        "current_observation": None,
        "action": None,
        "answer": None,
        "critique": None,
        "critique_feedback": None,
        "attempt_count": 1,
    }


def ask_user_node(state: AgentState):
    """Ask the user for clarification."""
    if state.clarification and state.clarification.needed:
        user_input = input(f"Agent: {state.clarification.question} ")
        state.clarification_answer = user_input.strip()
    return {"clarification_answer": state.clarification_answer}


def reason_node(state: AgentState):
    """Reason about the next action based on history and critique feedback, or decide to finish."""
    if state.critique_feedback:
        print("\n--- Reasoning Step (Addressing Critique Feedback) ---")
        state.attempt_count += 1
        print(f"Starting Answer Attempt {state.attempt_count}")
    else:
        print(
            f"\n--- Reasoning Step (Loop {state.current_react_loop + 1}/{state.max_react_loops}) ---"
        )

    if state.current_react_loop >= state.max_react_loops:
        print("Max ReAct loops reached. Finishing.")
        state.action = AgentAction(finish=True, thought="Max ReAct loops reached.")
        state.critique_feedback = None
        return {
            "action": state.action,
            "critique_feedback": None,
            "attempt_count": state.attempt_count,
        }

    history_for_baml = [
        {"thought": t, "action": a, "observation": o} for t, a, o in state.agent_history
    ]

    feedback_to_pass = state.critique_feedback
    state.critique_feedback = None

    reasoning_result = b.ReasonAct(
        question=state.question,
        clarification_details=state.clarification_answer,
        history=history_for_baml,
        critique_feedback=feedback_to_pass,
    )

    if isinstance(reasoning_result, dict):
        state.action = AgentAction(
            tool_name=reasoning_result.get("tool_name"),
            query=reasoning_result.get("query"),
            finish=reasoning_result.get("finish", False),
            thought=reasoning_result.get("thought", ""),
        )
    elif hasattr(reasoning_result, "finish") and hasattr(reasoning_result, "thought"):
        state.action = AgentAction(
            tool_name=getattr(reasoning_result, "tool_name", None),
            query=getattr(reasoning_result, "query", None),
            finish=getattr(reasoning_result, "finish", False),
            thought=getattr(reasoning_result, "thought", ""),
        )
    else:
        print(
            f"Warning: Unexpected return type from b.ReasonAct: {type(reasoning_result)}. Forcing finish."
        )
        state.action = AgentAction(finish=True, thought="Error in reasoning step.")

    print(f"Thought: {state.action.thought}")
    if state.action.finish:
        print("Action: Finish")
    elif state.action.tool_name:
        tool_name_str = (
            state.action.tool_name.value
            if hasattr(state.action.tool_name, "value")
            else str(state.action.tool_name)
        )
        print(f"Action: Use Tool '{tool_name_str}' with Query '{state.action.query}'")
    else:
        print("Action: No tool specified but not finishing. Forcing finish.")
        state.action.finish = True

    return {
        "action": state.action,
        "critique_feedback": state.critique_feedback,
        "attempt_count": state.attempt_count,
    }


def execute_tool_node(state: AgentState):
    """Executes the planned tool and stores the raw output in current_observation."""
    action = state.action
    observation_result: Dict[str, Optional[str]] = {
        "error": "Tool execution skipped."
    }  # Default error

    if not action or action.finish or not action.tool_name or not action.query:
        print("  Skipping tool execution (finish signal or invalid action).")
        # Keep default error observation
    else:
        tool_name = (
            action.tool_name.value
            if hasattr(action.tool_name, "value")
            else str(action.tool_name)
        )
        query = action.query
        print(f"  Executing Tool: {tool_name}, Query: '{query}'")

        try:
            # --- Tool Execution Logic (Simplified - store result in observation_result) ---
            if tool_name == ToolName.WebSearch:
                search_res = web_search(query, max_results=3)
                if search_res:
                    # Combine results for observation, keep individual links if needed later
                    combined_content = "\n".join(
                        [
                            f"[{i + 1}] {res['content']}"
                            for i, res in enumerate(search_res)
                        ]
                    )
                    links = [res["link"] for res in search_res if res.get("link")]
                    observation_result = {
                        "content": combined_content,
                        "link": ", ".join(links) if links else None,
                    }  # Store combined content/links
                else:
                    observation_result = {
                        "content": "No web search results found.",
                        "link": None,
                    }

            elif tool_name == ToolName.PriceLookup:
                price_str = get_current_price(query)
                content = (
                    f"Current {query} price: {price_str}"
                    if price_str
                    else f"Could not find price for {query}."
                )
                observation_result = {"content": content, "link": None}

            elif tool_name == ToolName.AddressTracker:
                parts = query.split(":", 1)
                if len(parts) == 2:
                    chain, address = parts[0].strip(), parts[1].strip()
                    tracker_results = get_large_transfers_for_chain(
                        chain=chain, addresses=[address], limit=5
                    )
                    if tracker_results and not tracker_results.get("error"):
                        summary = f"Found {len(tracker_results.get(address, []))} large transfers for {query}."
                        observation_result = {
                            "content": summary,
                            "link": None,
                            "full_data": tracker_results,
                        }  # Keep full data if needed
                    elif tracker_results.get("error"):
                        observation_result = {
                            "content": f"AddressTracker failed: {tracker_results['error']}",
                            "link": None,
                            "error": tracker_results["error"],
                        }
                    else:
                        observation_result = {
                            "content": f"No significant activity found for {query}.",
                            "link": None,
                        }
                else:
                    observation_result = {
                        "content": f"Invalid query format for AddressTracker: '{query}'.",
                        "link": None,
                        "error": "Invalid query format",
                    }

            elif tool_name == ToolName.OnChainMetrics:
                asset_name = query.strip().lower()
                metrics_data = get_comprehensive_on_chain_data(asset_name=asset_name)
                if (
                    metrics_data
                    and not metrics_data.get("error")
                    and metrics_data.get("results")
                ):
                    asset_metrics = metrics_data.get("results", {}).get(
                        "asset_metrics", {}
                    )
                    summary = f"On-chain metrics for {asset_name}: "
                    if (
                        asset_metrics
                        and not asset_metrics.get("error")
                        and asset_metrics.get("data")
                    ):
                        summary += f"Found {len(asset_metrics['data'])} days data (e.g., AdrActCnt, TxCnt)."
                    else:
                        summary += "No recent metric data found."
                    observation_result = {
                        "content": summary.strip(),
                        "link": None,
                        "full_data": metrics_data,
                    }
                elif metrics_data.get("error"):
                    observation_result = {
                        "content": f"OnChainMetrics failed: {metrics_data['error']}",
                        "link": None,
                        "error": metrics_data["error"],
                    }
                else:
                    observation_result = {
                        "content": f"Could not retrieve metrics for {asset_name}.",
                        "link": None,
                    }

            elif tool_name == ToolName.UrlExtractor:
                url_to_extract = query.strip()
                extracted_content = extract_content_from_url(url_to_extract)
                if extracted_content:
                    # Store full content, maybe summarize later if needed
                    observation_result = {
                        "content": extracted_content,
                        "link": url_to_extract,
                    }
                else:
                    observation_result = {
                        "content": f"Failed to extract content from URL: {url_to_extract}",
                        "link": url_to_extract,
                        "error": "Extraction failed",
                    }

            else:
                print(f"  Warning: Unknown tool '{tool_name}' encountered.")
                observation_result = {
                    "content": f"Error: Unknown tool '{tool_name}'.",
                    "link": None,
                    "error": "Unknown tool",
                }

        except Exception as e:
            error_message = (
                f"Error executing tool '{tool_name}' with query '{query}': {e}"
            )
            print(f"  {error_message}")
            observation_result = {
                "content": error_message,
                "link": None,
                "error": str(e),
            }

    # Store the raw observation before filtering
    state.current_observation = observation_result
    print(
        f"  Raw Observation: {str(observation_result.get('content', 'N/A'))[:200]}..."
    )

    # Return only the observation to be passed to the filter node
    return {"current_observation": state.current_observation}


def filter_and_accumulate_node(state: AgentState):
    """Filters the current_observation using b.FilterResults, updates history, and accumulates results."""
    print("\n--- Filtering and Accumulating Result ---")
    current_obs = state.current_observation
    filtered_results_for_accumulation = []
    observation_summary = "No observation processed."  # Default summary

    # Prepare the observation list for BAML FilterResults
    observation_list = []
    if current_obs:
        # Wrap the single observation dict in a list for the BAML function
        # BAML function expects ObservationItem[], but the client often handles dicts.
        # Ensure keys match ObservationItem definition in filter_results.baml (content, link, error)
        observation_list.append(current_obs)
        print(f"  Filtering observation: {current_obs}")
    else:
        print("  No observation content found to filter.")
        observation_summary = "No observation content received."

    if observation_list:
        try:
            # Call BAML to filter the observation based on the question
            filtered_items: List[FilteredItem] = b.FilterResults(
                question=state.question,
                results=observation_list,  # Pass the list containing the single observation dict
            )
            print(
                f"  BAML FilterResults returned {len(filtered_items)} relevant item(s)."
            )

            if filtered_items:
                summaries = []
                for item in filtered_items:
                    # Add relevant info as dict to accumulated_results list
                    filtered_results_for_accumulation.append(
                        {"content": item.content, "link": item.source}
                    )
                    # Create summary for history
                    summary = f"Relevant: {item.content[:150]}..."
                    if item.source:
                        summary += f" (Source: {item.source})"
                    summaries.append(summary)
                    print(f"    - {summary}")

                observation_summary = "; ".join(summaries)
            else:
                # If FilterResults returns empty, it means the item wasn't relevant
                obs_content = current_obs.get(
                    "content", current_obs.get("error", "[No Content/Error]")
                )
                observation_summary = (
                    f"Filtered out as irrelevant: {str(obs_content)[:150]}..."
                )
                print(f"  Observation filtered out as irrelevant.")

        except Exception as e:
            print(f"Error during BAML FilterResults call: {e}. Observation not added.")
            observation_summary = f"Error during filtering: {e}"
            # Decide if you want to add raw observation on error, currently it's skipped.

    # --- Update History and Accumulated Results ---

    # Update history using the action from the *previous* step (reason_node)
    # and the observation_summary generated above
    thought = state.action.thought if state.action else "N/A"
    action_summary = "Finish"  # Default if action is None or finish=True
    if state.action and not state.action.finish and state.action.tool_name:
        tool_name_str = (
            state.action.tool_name.value
            if hasattr(state.action.tool_name, "value")
            else str(state.action.tool_name)
        )
        query_str = f"('{state.action.query}')" if state.action.query else ""
        action_summary = f"{tool_name_str}{query_str}"

    new_history = list(state.agent_history)
    new_history.append((thought, action_summary, observation_summary))

    # Append the *filtered* results to the accumulated list
    new_accumulated = list(state.accumulated_results)
    if filtered_results_for_accumulation:
        new_accumulated.extend(filtered_results_for_accumulation)
        print(
            f"  Added {len(filtered_results_for_accumulation)} item(s) to accumulated results."
        )

    print(
        f"History Updated: Thought='{thought}', Action='{action_summary}', Observation='{observation_summary}'"
    )
    print(f"Total Accumulated Results: {len(new_accumulated)}")

    # Increment loop counter *after* filtering and history update
    current_loop = state.current_react_loop + 1

    # Return updates needed for the next reasoning step
    return {
        "agent_history": new_history,
        "accumulated_results": new_accumulated,
        "current_react_loop": current_loop,
        "current_observation": None,  # Clear current observation after processing
    }


def final_filter_node(state: AgentState):
    """Optional: Final ranking/filtering of all accumulated results before generating the answer."""
    print("\n--- Performing Final Filtering/Ranking ---")
    # This node is optional. If the per-step filtering is sufficient,
    # answer_node can directly use state.accumulated_results.
    # If you want a final re-ranking of everything gathered:
    if not state.accumulated_results:
        state.final_relevant_results = []
        print("No accumulated results for final filtering.")
        return {"final_relevant_results": []}

    print(
        f"Performing final ranking on {len(state.accumulated_results)} accumulated items."
    )
    accumulated_items = [
        ResultItem(content=d.get("content"), link=d.get("link"))
        for d in state.accumulated_results
        if d.get("content")
    ]

    if not accumulated_items:
        state.final_relevant_results = []
        print("No valid accumulated items for final filtering.")
        return {"final_relevant_results": []}

    top_k_final = 5  # How many top results for the final answer

    try:
        ranked_final_items: List[RankedResultItem] = b.RankResults(
            question=state.question,
            results=accumulated_items,
            top_k=top_k_final,
        )
        state.final_relevant_results = [
            {"content": item.content, "link": item.link} for item in ranked_final_items
        ]
    except Exception as e:
        print(
            f"Error during final BAML RankResults call: {e}. Using top {top_k_final} accumulated results."
        )
        # Fallback: just take the last N accumulated results
        state.final_relevant_results = state.accumulated_results[-top_k_final:]

    print(f"Final relevant results count: {len(state.final_relevant_results)}")
    return {"final_relevant_results": state.final_relevant_results}


def generate_answer_node(state: AgentState):
    """Generate the final answer using accumulated relevant results."""
    print("\n--- Generating Final Answer ---")
    context_dicts = state.accumulated_results  # Use accumulated results directly

    if not context_dicts:
        print("Warning: No accumulated results to generate answer from.")
        state.answer = Answer(
            cited_answer="I could not find enough information to answer the question.",
            references=[],
        )
        # Store empty list in final_relevant_results as well
        return {"answer": state.answer, "final_relevant_results": []}

    # Convert accumulated results (List[Dict]) to ContextItem list for BAML
    context_items: List[ContextItem] = [
        # Ensure content is always a string, handle potential None from dict.get
        ContextItem(content=d.get("content", ""), source=d.get("link"))
        for d in context_dicts
        if d.get("content")  # Only include items with actual content
    ]

    # Store the final relevant results used for the answer
    final_results_for_state = context_dicts  # Store the list of dicts

    try:
        state.answer = b.AnswerQuestion(question=state.question, context=context_items)
        print(f"Generated Answer: {state.answer.cited_answer[:200]}...")
    except Exception as e:
        print(f"Error during BAML AnswerQuestion call: {e}")
        state.answer = Answer(
            cited_answer=f"Error generating answer: {e}", references=[]
        )  # Provide error in answer

    # Return the answer and the list of dicts used to generate it
    return {"answer": state.answer, "final_relevant_results": final_results_for_state}


def critique_node(state: AgentState):
    """Critique the generated answer and set feedback if needed."""
    print("\n--- Critiquing Answer ---")
    critique_feedback = None
    answer_text = ""
    if state.answer and hasattr(state.answer, "cited_answer"):
        answer_text = state.answer.cited_answer

    if not answer_text:
        print("No answer generated to critique.")
        state.critique = Critique(
            is_good=False,
            critique="No answer was generated.",
            missing_info="The entire answer is missing.",
        )
        critique_feedback = (
            "No answer was generated. Need to retry information gathering."
        )
    else:
        try:
            state.critique = b.CritiqueAnswer(
                question=state.question, answer=answer_text
            )
            print(
                f"Critique: Good={state.critique.is_good}. Reason: {state.critique.critique}"
            )
            if not state.critique.is_good:
                print(f"Missing Info: {state.critique.missing_info}")
                critique_feedback = f"Critique: {state.critique.critique}. Missing Info: {state.critique.missing_info}"
        except Exception as e:
            print(f"Error during BAML CritiqueAnswer call: {e}")
            state.critique = Critique(
                is_good=False,
                critique=f"Error during critique generation: {e}",
                missing_info="Unknown",
            )
            critique_feedback = f"Error during critique: {e}. Need to retry."

    return {"critique": state.critique, "critique_feedback": critique_feedback}


def build_agent_graph():
    graph_builder = StateGraph(AgentState)

    # Add nodes
    graph_builder.add_node("clarify", clarify_node)
    graph_builder.add_node("ask_user", ask_user_node)
    graph_builder.add_node("reason", reason_node)
    graph_builder.add_node("execute_tool", execute_tool_node)
    graph_builder.add_node("filter_and_accumulate", filter_and_accumulate_node)
    # Ensure the answer node name matches the function name used
    graph_builder.add_node(
        "generate_answer", generate_answer_node
    )  # Use generate_answer_node here
    graph_builder.add_node("generate_critique", critique_node)

    # --- Define Edges ---
    graph_builder.set_entry_point("clarify")

    # Clarification Path -> Reason
    def decide_clarification_path(state: AgentState):
        if (
            state.clarification
            and state.clarification.needed
            and not state.clarification_answer
        ):
            return "ask_user"
        else:
            return "reason"

    graph_builder.add_conditional_edges(
        "clarify",
        decide_clarification_path,
        {"ask_user": "ask_user", "reason": "reason"},
    )
    graph_builder.add_edge("ask_user", "reason")

    # ReAct Loop Logic
    def decide_react_action(state: AgentState):
        if state.action and state.action.finish:
            return "generate_answer"  # Point to the correct answer node name
        elif state.action and state.action.tool_name:
            return "execute_tool"
        else:
            print("Warning: Invalid action state in decide_react_action. Finishing.")
            return "generate_answer"  # Point to the correct answer node name

    graph_builder.add_conditional_edges(
        "reason",
        decide_react_action,
        {
            "execute_tool": "execute_tool",
            "generate_answer": "generate_answer",  # Point to the correct answer node name
        },
    )

    # Tool -> Filter -> Reason
    graph_builder.add_edge("execute_tool", "filter_and_accumulate")
    graph_builder.add_edge("filter_and_accumulate", "reason")

    # Answer -> Critique
    graph_builder.add_edge(
        "generate_answer", "generate_critique"
    )  # Point from the correct answer node name

    # Critique Loop Logic
    def decide_critique_path(state: AgentState):
        # Check attempt count FIRST (using >= max_attempts, e.g., >= 2 for 1 retry)
        # Ensure max_answer_attempts is accessible or defined (e.g., 2 for one retry)
        max_answer_attempts = 2
        if state.attempt_count >= max_answer_attempts:
            print(f"Max answer attempts ({state.attempt_count}) reached. Ending.")
            return END
        # Then check critique status
        if state.critique and state.critique.is_good:
            print("Critique passed. Ending.")
            return END
        elif state.critique and not state.critique.is_good:
            print("Critique failed. Looping back to reason with feedback.")
            # Pass critique feedback back to reason node
            return "reason"
        else:
            # Fallback if critique is missing or invalid
            print("Warning: Critique missing or invalid state. Ending.")
            return END

    graph_builder.add_conditional_edges(
        "generate_critique",
        decide_critique_path,
        {
            END: END,
            "reason": "reason",  # Route back to reason on failure
        },
    )

    # Compile the graph
    agent_graph = graph_builder.compile()
    return agent_graph
