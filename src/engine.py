import asyncio
import uuid
from collections import defaultdict
from typing import Any, Callable, Dict, List, Set

import networkx as nx
from pydantic import BaseModel, Field


class TaskSpec(BaseModel):
    """A declarative description of a single task.

    Attributes
    ----------
    name: str
        Human readable identifier.
    func: Callable[..., Any]
        The python callable to execute.
    args: List[Any]
        Positional arguments passed to ``func``.
    kwargs: Dict[str, Any]
        Keyword arguments passed to ``func``.
    depends_on: List[str]
        Names of tasks that must finish before this one runs.
    """

    name: str = Field(..., description="Task name")
    func: Callable[..., Any] = Field(..., description="Callable to execute")
    args: List[Any] = Field(default_factory=list)
    kwargs: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    task_id: str
    status: str
    result: Any = None
    error: str = None


class AutoFlowEngine:
    """Core scheduler + executor.

    The engine builds a directed acyclic graph (DAG) from ``TaskSpec`` objects.
    It then walks the graph, launching ready nodes as ``asyncio.Task`` objects.
    An optional lightweight AI‑hinting module can prioritize which ready node
    runs next (here we simply sort by the number of dependents).
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self.task_specs: Dict[str, TaskSpec] = {}
        self.results: Dict[str, ExecutionResult] = {}
        self._running_tasks: Set[asyncio.Task] = set()
        self._loop = asyncio.get_event_loop()

    def add_task(self, spec: TaskSpec) -> None:
        if spec.name in self.task_specs:
            raise ValueError(f"Task '{spec.name}' already exists")
        self.task_specs[spec.name] = spec
        self.graph.add_node(spec.name)
        for dep in spec.depends_on:
            if dep not in self.task_specs:
                raise ValueError(f"Dependency '{dep}' not defined before '{spec.name}'")
            self.graph.add_edge(dep, spec.name)
        if not nx.is_directed_acyclic_graph(self.graph):
            raise ValueError("Added task creates a cycle in the DAG")

    async def _run_task(self, task_id: str, spec: TaskSpec) -> ExecutionResult:
        try:
            # Execute the callable – it may be async or sync
            if asyncio.iscoroutinefunction(spec.func):
                result = await spec.func(*spec.args, **spec.kwargs)
            else:
                result = spec.func(*spec.args, **spec.kwargs)
            return ExecutionResult(task_id=task_id, status="success", result=result)
        except Exception as exc:  # pragma: no cover – caught for completeness
            return ExecutionResult(task_id=task_id, status="failed", error=str(exc))

    def _ready_tasks(self) -> List[TaskSpec]:
        ready = []
        for name, spec in self.task_specs.items():
            if name in self.results:
                continue  # already finished
            predecessors = list(self.graph.predecessors(name))
            if all(pred in self.results and self.results[pred].status == "success" for pred in predecessors):
                ready.append(spec)
        # Simple AI‑hint: prioritize tasks with more outgoing edges (i.e., they unblock more work)
        ready.sort(key=lambda s: self.graph.out_degree(s.name), reverse=True)
        return ready

    async def run(self) -> Dict[str, ExecutionResult]:
        while len(self.results) < len(self.task_specs):
            ready = self._ready_tasks()
            if not ready:
                # Deadlock – some tasks failed
                break
            for spec in ready:
                task_id = str(uuid.uuid4())
                coro = self._run_task(task_id, spec)
                task = self._loop.create_task(coro)
                self._running_tasks.add(task)
                task.add_done_callback(self._running_tasks.discard)
                # Store provisional result when done
                task.add_done_callback(lambda t, sid=spec.name: self._store_result(sid, t.result()))
            # Wait for at least one task to complete before re‑evaluating readiness
            if self._running_tasks:
                await asyncio.wait(self._running_tasks, return_when=asyncio.FIRST_COMPLETED)
        return self.results

    def _store_result(self, task_name: str, result: ExecutionResult) -> None:
        self.results[task_name] = result

    # Convenience synchronous wrapper -------------------------------------------------
    def run_sync(self) -> Dict[str, ExecutionResult]:
        return self._loop.run_until_complete(self.run())

# ---------------------------------------------------------------------------
# Helper to load plugins dynamically -------------------------------------------------
import importlib.util
import pathlib


def load_plugins(plugin_dir: pathlib.Path) -> List[Callable[[], TaskSpec]]:
    """Discover ``TaskSpec`` factories in ``plugin_dir``.

    Each plugin module must expose a ``register`` function returning a list of
    ``TaskSpec`` objects.  This keeps the core engine agnostic of concrete tasks.
    """
    specs: List[Callable[[], TaskSpec]] = []
    for file in plugin_dir.glob("*.py"):
        if file.name.startswith("__"):
            continue
        spec = importlib.util.spec_from_file_location(file.stem, file)
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(module)  # type: ignore[assignment]
        if hasattr(module, "register"):
            specs.extend(module.register())
    return specs
