"""LangGraph runtime for the existing pedagogical FSM.

This is a *runtime substitution*, not a rewrite. The graph's topology mirrors
`VALID_TRANSITIONS` exactly, every node body delegates to the existing
`TeacherOrchestrator` (so Planner/Explainer/Questioner/Adaptation/Assessment
logic is reused verbatim), and routing is decided by the state the orchestrator
returns — never by a model. The pedagogical state names are unchanged.

Two constraints from `instructions/task_agentic_ai_modernization.md` shape this:

* **No prompt-driven routing.** §4.1.G calls that out as the thing that would
  undermine the explicit-FSM design; edges here are deterministic functions of
  the returned `TeacherState`.
* **SQLite stays authoritative.** §4.1.D says to treat LangGraph state as a
  transient runtime concern rather than forking persistence, so `SessionState`
  remains the system of record and the graph carries only routing data. That
  also keeps the state trivially serialisable for the checkpointer.

The lesson loop is driven from outside (the WebSocket layer pumps one step at a
time, interleaving rendering and waiting for the learner), so the graph is
stepped one node per call and exposes the same `step()` signature as
`TeacherOrchestrator`. That keeps it a drop-in alternative behind
`ORCHESTRATION_RUNTIME`, with the original dispatcher untouched as the default.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from typing_extensions import TypedDict

from modules.ai_agent_orchestration.src.state_machine.orchestrator import TeacherOrchestrator
from modules.ai_agent_orchestration.src.state_machine.session_state import SessionState
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState
from modules.ai_agent_orchestration.src.state_machine.transitions import VALID_TRANSITIONS

logger = logging.getLogger(__name__)


class GraphState(TypedDict, total=False):
    """Routing data only — the pedagogical state itself lives in SessionState."""

    session_id: str
    current: str          # TeacherState.name being executed
    next: str             # TeacherState.name the orchestrator routed to
    payload: Any          # what that step produced, returned to the caller


# Terminal states have no outgoing work; everything else is a graph node.
_NODE_STATES = [state for state in TeacherState if VALID_TRANSITIONS.get(state)]
_TERMINAL_STATES = [state for state in TeacherState if not VALID_TRANSITIONS.get(state)]


def _node_name(state: TeacherState) -> str:
    return state.name.lower()


class LangGraphOrchestrator:
    """Executes the pedagogical FSM as a LangGraph graph.

    Exposes the same `step()` contract as `TeacherOrchestrator`, so the service
    layer and the WebSocket loop are unchanged.
    """

    def __init__(self, fsm: TeacherOrchestrator):
        self._fsm = fsm
        self._inputs: Dict[str, Any] = {}
        self._session: Optional[SessionState] = None
        self.graph = self._build_graph()

    # -- graph construction --------------------------------------------------

    def _build_graph(self):
        """Mirror VALID_TRANSITIONS as LangGraph nodes and conditional edges."""
        from langgraph.graph import END, StateGraph

        builder = StateGraph(GraphState)

        for state in _NODE_STATES:
            builder.add_node(_node_name(state), self._make_node(state))

        # A terminal state still needs a node so the graph can route into it and
        # stop there; its body is a no-op that records the state.
        for state in _TERMINAL_STATES:
            builder.add_node(_node_name(state), self._make_terminal_node(state))

        builder.set_entry_point(_node_name(TeacherState.UNDERSTAND))

        for state in _NODE_STATES:
            allowed = VALID_TRANSITIONS[state]
            # The mapping is exhaustive over the transitions the FSM declares, so
            # an unexpected target raises rather than silently routing somewhere.
            builder.add_conditional_edges(
                _node_name(state),
                self._route,
                {_node_name(target): _node_name(target) for target in allowed},
            )

        for state in _TERMINAL_STATES:
            builder.add_edge(_node_name(state), END)

        return builder.compile()

    def _make_node(self, state: TeacherState):
        """A node that runs exactly the orchestrator's logic for this state."""

        def run(graph_state: GraphState) -> GraphState:
            next_state, payload = self._fsm.step(state, self._session, self._inputs)
            return {
                "session_id": graph_state.get("session_id", ""),
                "current": state.name,
                "next": next_state.name,
                "payload": payload,
            }

        run.__name__ = f"node_{_node_name(state)}"
        return run

    def _make_terminal_node(self, state: TeacherState):
        def run(graph_state: GraphState) -> GraphState:
            next_state, payload = self._fsm.step(state, self._session, self._inputs)
            return {
                "session_id": graph_state.get("session_id", ""),
                "current": state.name,
                "next": next_state.name,
                "payload": payload,
            }

        run.__name__ = f"terminal_{_node_name(state)}"
        return run

    @staticmethod
    def _route(graph_state: GraphState) -> str:
        """Deterministic edge: follow the state the orchestrator returned."""
        return _node_name(TeacherState[graph_state["next"]])

    # -- the TeacherOrchestrator contract ------------------------------------

    def step(
        self, current_state: TeacherState, session: SessionState, inputs: Dict[str, Any]
    ) -> Tuple[TeacherState, Any]:
        """Advance one node, returning `(next_state, payload)`.

        The classroom drives the loop itself — it renders video and waits for the
        learner between steps — so a single node is executed per call rather than
        letting the graph run to completion.
        """
        node = self.graph.nodes.get(_node_name(current_state))
        if node is None:
            raise ValueError(f"No graph node for state {current_state}")

        # The session and inputs belong to this step, not to graph state: they
        # hold live objects (agents' Pydantic models) that must not be
        # serialised into a checkpoint.
        self._session, self._inputs = session, inputs
        try:
            result = node.invoke(
                {"session_id": session.session_id, "current": current_state.name}
            )
        finally:
            self._session, self._inputs = None, {}

        next_state = TeacherState[result["next"]]
        logger.debug(
            "LangGraph step %s -> %s (session %s)",
            current_state.name, next_state.name, session.session_id,
        )
        return next_state, result["payload"]

    # -- passthroughs so this is a drop-in for TeacherOrchestrator -----------

    # Everything else belongs to the wrapped orchestrator, not to this wrapper.
    _OWN_ATTRS = frozenset({"_fsm", "_inputs", "_session", "graph"})

    def __getattr__(self, item: str) -> Any:
        """Expose the wrapped orchestrator's agents/clients (planner, rag_client…)."""
        return getattr(self._fsm, item)

    def __setattr__(self, item: str, value: Any) -> None:
        """Forward assignments to the wrapped orchestrator.

        Read-only passthrough is not enough: node bodies execute against
        `self._fsm`, so an assignment like `orchestrator.ml_core = client` that
        landed on the wrapper would be silently ignored at run time while
        appearing to have worked.
        """
        if item in self._OWN_ATTRS or "_fsm" not in self.__dict__:
            object.__setattr__(self, item, value)
        else:
            setattr(self._fsm, item, value)


def build_orchestration_runtime(fsm: TeacherOrchestrator, runtime: str = "fsm"):
    """Return the orchestrator to drive lessons with.

    `runtime="langgraph"` executes the same graph through LangGraph; anything
    else keeps the original dispatcher. Falls back to the dispatcher (with a
    warning) if LangGraph is not installed, so a deploy can never be bricked by
    a missing optional dependency.
    """
    if (runtime or "fsm").strip().lower() != "langgraph":
        return fsm

    try:
        orchestrator = LangGraphOrchestrator(fsm)
    except Exception:
        logger.exception(
            "ORCHESTRATION_RUNTIME=langgraph requested but the graph could not be "
            "built; falling back to the built-in FSM dispatcher."
        )
        return fsm

    logger.info("Orchestration runtime: LangGraph (%d nodes)", len(orchestrator.graph.nodes))
    return orchestrator
