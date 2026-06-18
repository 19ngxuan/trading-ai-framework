import ast
from pathlib import Path


AGENT_MODULE_DIR = Path("app/modules/agents")

FORBIDDEN_IMPORT_PREFIXES = (
    "app.modules.broker",
    "app.modules.scheduler",
    "app.modules.execution",
    "app.modules.market_data.alpaca_provider",
    "app.modules.market_data.factory",
    "app.persistence",
    "httpx",
    "requests",
    "urllib",
    "openai",
    "anthropic",
    "langchain",
    "langgraph",
    "pydantic_settings",
)

FORBIDDEN_CONFIG_IMPORTS = {
    "app.core.config",
}


def _agent_python_files() -> list[Path]:
    provider_boundary_files = {
        "provider_factory.py",
        "scads_provider.py",
    }
    return sorted(
        path
        for path in AGENT_MODULE_DIR.glob("*.py")
        if path.name not in provider_boundary_files
    )


def test_agent_modules_do_not_import_broker_persistence_network_or_llm_modules() -> None:
    violations: list[str] = []
    for path in _agent_python_files():
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(FORBIDDEN_IMPORT_PREFIXES):
                        violations.append(f"{path}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith(FORBIDDEN_IMPORT_PREFIXES) or module in FORBIDDEN_CONFIG_IMPORTS:
                    violations.append(f"{path}: from {module} import ...")

    assert violations == []


def test_agent_modules_do_not_access_environment_or_settings() -> None:
    violations: list[str] = []
    for path in _agent_python_files():
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                if (
                    isinstance(node.value, ast.Name)
                    and node.value.id == "os"
                    and node.attr in {"environ", "getenv"}
                ):
                    violations.append(f"{path}: os.{node.attr}")
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in {
                    "getenv",
                    "get_settings",
                    "BaseSettings",
                }:
                    violations.append(f"{path}: {func.id}()")

    assert violations == []
