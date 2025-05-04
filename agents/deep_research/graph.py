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
    """Use LLM to determine if clarification is needed."""
    # Reset state for a new run
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
    """Filters the current_observation, updates history, and accumulates results."""
    print("\n--- Filtering and Accumulating Result ---")
    current_obs = state.current_observation
    filtered_summary = "No observation to filter."
    filtered_results_for_accumulation = []

    if current_obs and current_obs.get("content"):
        # Prepare input for RankResults - needs a list
        obs_item = ResultItem(
            content=current_obs.get("content"), link=current_obs.get("link")
        )
        top_k_to_request = 1  # We only want to know if this *one* result is relevant

        try:
            # Use RankResults to assess relevance of the single observation
            ranked_results: List[RankedResultItem] = b.RankResults(
                question=state.question,
                results=[obs_item],  # Filter the single current observation
                top_k=top_k_to_request,
            )

            # Check if the observation was ranked (i.e., deemed relevant)
            if ranked_results:
                ranked_item = ranked_results[0]
                # You might add a score threshold check here if needed: ranked_item.relevance_score >= 3
                filtered_results_for_accumulation.append(
                    {"content": ranked_item.content, "link": ranked_item.link}
                )
                filtered_summary = f"Relevant: {ranked_item.content[:150]}..."
                print(f"  Observation deemed relevant.")
            else:
                # If RankResults returns empty, it means the item wasn't relevant enough
                filtered_summary = f"Filtered out: {obs_item.content[:150]}..."
                print(f"  Observation filtered out as irrelevant.")

        except Exception as e:
            print(
                f"Error during BAML RankResults call: {e}. Assuming observation is relevant."
            )
            # Fallback: Assume relevant on error? Or filter out? Let's assume relevant for now.
            filtered_results_for_accumulation.append(
                {"content": obs_item.content, "link": obs_item.link}
            )
            filtered_summary = f"Relevant (fallback): {obs_item.content[:150]}..."

    elif current_obs and current_obs.get("error"):
        filtered_summary = f"Error from tool: {current_obs.get('error')}"
        # Optionally add errors to accumulated results or history if needed
        # filtered_results_for_accumulation.append({"error": current_obs.get('error')})
        print(f"  Tool execution resulted in error: {current_obs.get('error')}")
    else:
        print("  No valid observation content found to filter.")

    # Update history with the *filtered* observation summary
    thought = state.action.thought if state.action else "N/A"
    action_summary = "Finish"  # Default if action is None or finish=True
    if state.action and not state.action.finish and state.action.tool_name:
        tool_name_str = (
            state.action.tool_name.value
            if hasattr(state.action.tool_name, "value")
            else str(state.action.tool_name)
        )
        action_summary = f"{tool_name_str}('{state.action.query}')"

    state.agent_history.append((thought, action_summary, filtered_summary))

    # Append the *filtered* results to the accumulated list
    if filtered_results_for_accumulation:
        state.accumulated_results.extend(filtered_results_for_accumulation)
        print(
            f"  Added {len(filtered_results_for_accumulation)} item(s) to accumulated results."
        )

    # Increment loop counter *after* filtering and history update
    state.current_react_loop += 1

    print(f"Filtered Observation Summary: {filtered_summary}")
    print(f"Total Accumulated Results: {len(state.accumulated_results)}")

    # Return updates needed for the next reasoning step
    return {
        "agent_history": state.agent_history,
        "accumulated_results": state.accumulated_results,
        "current_react_loop": state.current_react_loop,
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


def answer_node(state: AgentState):
    """Generate final answer from the final set of relevant results."""
    print("\n--- Generating Final Answer ---")
    # Use final_relevant_results if final_filter_node is used,
    # otherwise use accumulated_results directly.
    # context_dicts = state.final_relevant_results or [] # If using final_filter_node
    context_dicts = state.accumulated_results or []  # If NOT using final_filter_node

    if not context_dicts:
        print("No relevant context found to generate answer.")
        # Set a default answer or let BAML handle empty context
        state.answer = Answer(
            cited_answer="I could not find sufficient information to answer the question.",
            references=[],
        )
        return {"answer": state.answer}

    context_items: List[ContextItem] = [
        ContextItem(content=d.get("content", ""), source=d.get("link"))
        for d in context_dicts
        if d.get("content")
    ]

    try:
        state.answer = b.AnswerQuestion(question=state.question, context=context_items)
        print(f"Generated Answer: {state.answer.cited_answer[:200]}...")
    except Exception as e:
        print(f"Error during BAML AnswerQuestion call: {e}")
        state.answer = Answer(
            cited_answer=f"Error generating answer: {e}", references=[]
        )  # Provide error in answer

    return {"answer": state.answer}


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
    graph_builder.add_node(
        "filter_and_accumulate", filter_and_accumulate_node
    )  # Renamed
    # graph_builder.add_node("final_filter", final_filter_node) # Optional final filter
    graph_builder.add_node("generate_answer", answer_node)
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
            return "reason"  # Go directly to reason after clarification

    graph_builder.add_conditional_edges(
        "clarify",
        decide_clarification_path,
        {"ask_user": "ask_user", "reason": "reason"},
    )
    graph_builder.add_edge("ask_user", "reason")  # Ask user also goes to reason

    # ReAct Loop Logic
    def decide_react_action(state: AgentState):
        if state.action and state.action.finish:
            # If ReasonAct decided to finish, exit loop to generate answer
            # return "final_filter" # Go to final filter if using it
            return "generate_answer"  # Go directly to answer if not using final filter
        elif state.action and state.action.tool_name:
            # If ReasonAct chose a tool, execute it
            return "execute_tool"
        else:
            # Should not happen if reason_node forces finish on invalid action
            print("Warning: Invalid action state in decide_react_action. Finishing.")
            # return "final_filter"
            return "generate_answer"

    graph_builder.add_conditional_edges(
        "reason",
        decide_react_action,
        # {"execute_tool": "execute_tool", "final_filter": "final_filter"}, # If using final filter
        {
            "execute_tool": "execute_tool",
            "generate_answer": "generate_answer",
        },  # If not using final filter
    )

    # Tool -> Filter -> Reason
    graph_builder.add_edge("execute_tool", "filter_and_accumulate")
    graph_builder.add_edge("filter_and_accumulate", "reason")  # Loop back to reason

    # Optional Final Filter -> Answer
    # graph_builder.add_edge("final_filter", "generate_answer")

    # Answer -> Critique
    graph_builder.add_edge("generate_answer", "generate_critique")

    # Critique Loop Logic
    def decide_critique_path(state: AgentState):
        if state.attempt_count >= 2:  # Check attempt count FIRST
            print(f"Max answer attempts ({state.attempt_count}) reached. Ending.")
            return END
        if state.critique and state.critique.is_good:
            print("Critique passed. Ending.")
            return END
        elif state.critique and not state.critique.is_good:
            print("Critique failed. Looping back to reason with feedback.")
            return "reason"
        else:
            print("Warning: Critique missing or invalid state. Ending.")
            return END

    graph_builder.add_conditional_edges(
        "generate_critique",
        decide_critique_path,
        {
            END: END,
            "reason": "reason",
        },
    )

    # Compile the graph
    agent_graph = graph_builder.compile()
    return agent_graph
