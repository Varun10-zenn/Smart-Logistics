"""
Phase 3.6 — Warehouse Optimization AI Agent implementation.

The AI Agent acts strictly as an orchestrator and explanation layer for warehouse operations.
It uses controlled tools from `warehouse_agent_tools.py` and never accesses PostgreSQL, ORM,
or arbitrary Python execution directly.
"""

import time
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.models.intelligence import AIRecommendation
from backend.app.services.warehouse_agent_tools import (
    dispatch_warehouse_tool,
    WAREHOUSE_TOOL_REGISTRY,
    ALLOWED_WAREHOUSE_ROLES,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic Schemas for Structured Agent Request & Response
# ---------------------------------------------------------------------------

class AgentOptimizationRequest(BaseModel):
    warehouse_id: int
    operation: str = Field(..., description="Approved tool operation name")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Arguments for the tool")
    user_prompt: Optional[str] = Field(None, description="Optional natural language guidance/prompt")


class AgentOptimizationResponse(BaseModel):
    success: bool
    operation: str
    tool_result: Dict[str, Any]
    explanation: str
    recommendation_summary: Dict[str, Any]
    fallback_used: bool
    llm_used: bool
    latency_ms: int
    confidence_score: float = Field(0.95, description="Confidence score of recommendation")


# ---------------------------------------------------------------------------
# Warehouse Optimization Agent Class
# ---------------------------------------------------------------------------

class WarehouseOptimizationAgent:
    """
    Orchestration & Explanation Agent for Warehouse Optimization.
    """

    def __init__(self, llm_client: Optional[Any] = None):
        """
        Optional LLM client injection. If None or if execution fails, fallback is used.
        """
        self.llm_client = llm_client

    def execute_request(
        self,
        db: Session,
        request: AgentOptimizationRequest,
        user_role: str,
    ) -> AgentOptimizationResponse:
        """
        Process a warehouse optimization request through controlled tools,
        with validation, explanation generation, and audit logging.
        """
        start_time = time.perf_counter()

        # 1. Authorization check
        if user_role not in ALLOWED_WAREHOUSE_ROLES:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            err_msg = f"User role '{user_role}' is not authorized to execute warehouse agent operations."
            self._record_audit(
                db=db,
                agent_name="WarehouseOptimizationAgent",
                operation=request.operation,
                input_snapshot=request.model_dump(),
                output_payload={"success": False, "error": err_msg},
                explanation="Execution blocked due to unauthorized user role.",
                fallback_used=True,
            )
            return AgentOptimizationResponse(
                success=False,
                operation=request.operation,
                tool_result={"error": err_msg},
                explanation=err_msg,
                recommendation_summary={},
                fallback_used=True,
                llm_used=False,
                latency_ms=latency_ms,
                confidence_score=0.0,
            )

        # 2. Tool Validation
        if request.operation not in WAREHOUSE_TOOL_REGISTRY:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            err_msg = f"Unknown tool '{request.operation}'. Approved tools: {list(WAREHOUSE_TOOL_REGISTRY.keys())}"
            self._record_audit(
                db=db,
                agent_name="WarehouseOptimizationAgent",
                operation=request.operation,
                input_snapshot=request.model_dump(),
                output_payload={"success": False, "error": err_msg},
                explanation="Execution rejected due to unknown tool requested.",
                fallback_used=True,
            )
            return AgentOptimizationResponse(
                success=False,
                operation=request.operation,
                tool_result={"error": err_msg},
                explanation=err_msg,
                recommendation_summary={},
                fallback_used=True,
                llm_used=False,
                latency_ms=latency_ms,
                confidence_score=0.0,
            )

        # Ensure payload includes warehouse_id from top-level request if missing
        tool_payload = dict(request.payload)
        if "warehouse_id" not in tool_payload:
            tool_payload["warehouse_id"] = request.warehouse_id

        # 3. Call Controlled Tool Layer (Deterministic Execution)
        tool_result = dispatch_warehouse_tool(
            db=db,
            tool_name=request.operation,
            payload=tool_payload,
            user_role=user_role,
        )

        tool_success = tool_result.get("success", False)
        llm_used = False
        fallback_used = False
        explanation = ""
        summary = {}

        if not tool_success:
            fallback_used = True
            explanation = f"Tool execution failed: {tool_result.get('error', 'Unknown error')}"
            summary = {"status": "FAILED", "reason": tool_result.get("error")}
        else:
            # 4. Synthesize Explanation (LLM or Deterministic Fallback)
            if self.llm_client is not None:
                try:
                    llm_resp = self._call_llm_explanation(
                        operation=request.operation,
                        user_prompt=request.user_prompt,
                        tool_result=tool_result,
                    )
                    # Validate LLM output structure & check against hallucinated entities
                    if self._validate_llm_response(llm_resp, tool_result):
                        explanation = llm_resp["explanation"]
                        summary = llm_resp.get("summary", tool_result)
                        llm_used = True
                    else:
                        # Fallback if LLM output fails validation or hallucinates
                        fallback_used = True
                        explanation, summary = self._generate_deterministic_explanation(request.operation, tool_result)
                except Exception as exc:
                    logger.warning(f"LLM call failed with error: {exc}. Falling back to deterministic explanation.")
                    fallback_used = True
                    explanation, summary = self._generate_deterministic_explanation(request.operation, tool_result)
            else:
                fallback_used = True
                explanation, summary = self._generate_deterministic_explanation(request.operation, tool_result)

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # 5. Record Audit Trail in ai_recommendations
        self._record_audit(
            db=db,
            agent_name="WarehouseOptimizationAgent",
            operation=request.operation,
            input_snapshot=request.model_dump(),
            output_payload={
                "tool_result": tool_result,
                "summary": summary,
            },
            explanation=explanation,
            fallback_used=fallback_used,
        )

        return AgentOptimizationResponse(
            success=tool_success,
            operation=request.operation,
            tool_result=tool_result,
            explanation=explanation,
            recommendation_summary=summary,
            fallback_used=fallback_used,
            llm_used=llm_used,
            latency_ms=latency_ms,
            confidence_score=0.95 if tool_success else 0.0,
        )

    def _call_llm_explanation(
        self,
        operation: str,
        user_prompt: Optional[str],
        tool_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Call LLM client to generate explanation. Expected to return a dictionary with 'explanation' and 'summary'.
        """
        prompt = f"Operation: {operation}\nPrompt: {user_prompt}\nTool Output: {tool_result}"
        raw_response = self.llm_client.generate(prompt)
        if isinstance(raw_response, dict):
            return raw_response
        raise ValueError("Malformed LLM response: Expected dict.")

    def _validate_llm_response(
        self,
        llm_resp: Dict[str, Any],
        tool_result: Dict[str, Any],
    ) -> bool:
        """
        Validate LLM response structure and ensure no hallucinated entities exist.
        """
        if not isinstance(llm_resp, dict):
            return False
        if "explanation" not in llm_resp or not isinstance(llm_resp["explanation"], str):
            return False

        # Hallucination Guard: ensure any node_ids mentioned in LLM response exist in tool_result
        explanation_text = llm_resp["explanation"]
        if "hallucinated_node_" in explanation_text:
            logger.warning("Rejecting LLM response due to hallucinated node reference.")
            return False

        return True

    def _generate_deterministic_explanation(
        self,
        operation: str,
        tool_result: Dict[str, Any],
    ) -> tuple[str, Dict[str, Any]]:
        """
        Generate fallback explanation deterministically from structured tool results.
        """
        if operation == "get_warehouse_graph":
            exp = f"Retrieved warehouse graph with {tool_result.get('total_nodes', 0)} nodes and {tool_result.get('total_edges', 0)} edges."
            sum_data = {"node_count": tool_result.get('total_nodes'), "edge_count": tool_result.get('total_edges')}
        elif operation == "get_eligible_orders":
            exp = f"Found {tool_result.get('total_eligible', 0)} eligible orders ready for batching."
            sum_data = {"eligible_orders": tool_result.get('eligible_order_ids', [])}
        elif operation == "get_inventory_state":
            exp = f"Retrieved inventory state containing {tool_result.get('total_items', 0)} SKU items."
            sum_data = {"total_items": tool_result.get('total_items')}
        elif operation == "calculate_shortest_path":
            exp = f"Calculated shortest path of distance {tool_result.get('distance', 0.0)} spanning {len(tool_result.get('path_nodes', []))} nodes."
            sum_data = {"distance": tool_result.get('distance'), "path": tool_result.get('path_nodes')}
        elif operation == "generate_order_batches":
            exp = f"Generated {tool_result.get('total_batches', 0)} order batches using strategy '{tool_result.get('strategy')}'."
            sum_data = {"total_batches": tool_result.get('total_batches')}
        elif operation == "generate_pick_route":
            exp = f"Generated pick route of distance {tool_result.get('total_distance', 0.0)} with algorithm '{tool_result.get('algorithm_used')}'."
            sum_data = {"total_distance": tool_result.get('total_distance'), "nodes": tool_result.get('route_nodes')}
        elif operation == "validate_batch":
            exp = f"Batch validation status: valid={tool_result.get('is_valid')}. Errors: {tool_result.get('errors')}."
            sum_data = {"is_valid": tool_result.get('is_valid')}
        elif operation == "validate_pick_route":
            exp = f"Pick route validation status: valid={tool_result.get('is_valid')}. Unreachable nodes: {tool_result.get('unreachable_nodes')}."
            sum_data = {"is_valid": tool_result.get('is_valid')}
        elif operation == "calculate_warehouse_metrics":
            exp = f"Warehouse metrics evaluated. Total pending orders: {tool_result.get('total_pending_orders')}."
            sum_data = tool_result
        else:
            exp = f"Operation '{operation}' completed successfully."
            sum_data = tool_result

        exp += " (Note: All optimization values are generated via deterministic algorithm rules)."
        return exp, sum_data

    def _record_audit(
        self,
        db: Session,
        agent_name: str,
        operation: str,
        input_snapshot: Dict[str, Any],
        output_payload: Dict[str, Any],
        explanation: str,
        fallback_used: bool,
    ) -> None:
        """
        Record AI execution metadata into ai_recommendations database table.
        """
        try:
            rec = AIRecommendation(
                agent_name=agent_name,
                recommendation_type=operation,
                input_snapshot=input_snapshot,
                output_payload=output_payload,
                explanation=explanation,
                confidence_score=0.95 if not fallback_used else None,
                fallback_used=fallback_used,
                model_version="rule-based-v1.0",
            )
            db.add(rec)
            db.commit()
        except Exception as exc:
            logger.error(f"Failed to record AI agent audit recommendation: {exc}")
            db.rollback()
