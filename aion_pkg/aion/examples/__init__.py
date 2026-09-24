"""AION examples — copy-paste runnable starters.

Run via CLI:
    aion example quickstart
    aion example langchain_agent
    aion example crewai_agent
Or browse the source of these files to copy into your own agent.
"""

from importlib import resources


EXAMPLES = ("quickstart", "langchain_agent", "crewai_agent")


def _load(name):
    return (resources.files("aion.examples") / f"{name}.py").read_text(encoding="utf-8")


def run_example(name):
    if name not in EXAMPLES:
        print(f"Unknown example: {name}")
        print(f"Available: {', '.join(EXAMPLES)}")
        return {"error": "UNKNOWN_EXAMPLE"}

    source = _load(name)
    print(f"--- {name}.py " + "-" * (50 - len(name)))
    print(source)
    print("-" * 62)
    print(f"Copy this into your project, or run it directly:")
    print(f"  python -c \"import aion.examples.{name} as m; m.main()\"")
    return {"example": name, "lines": len(source.splitlines())}
