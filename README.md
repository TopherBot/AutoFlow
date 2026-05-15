# AutoFlow 🚀

**AutoFlow** is a modular, Python‑only automation platform that lets you define, schedule, and optimise workflows at runtime.  It ships with:

- 🧩 **Plugin architecture** – drop a new ``.py`` file into ``src/plugins`` and it becomes instantly available.
- 🤖 **AI hints** – optional lightweight heuristics (via ``scikit‑learn``) that bias the scheduler toward faster paths.
- 📡 **FastAPI REST layer** – start an HTTP server to submit jobs, monitor progress, or trigger ad‑hoc tasks.
- ⚡ **Asyncio powered** – full non‑blocking execution, ready for high‑throughput environments.
- 📦 **Docker‑friendly** – run the engine anywhere, with a single ``docker run`` command.

## Quick Start
```bash
# Clone & install
git clone https://github.com/yourname/AutoFlow.git && cd AutoFlow
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run the API (development mode)
uvicorn src.api:app --reload
```

Now you can POST a workflow definition to ``http://localhost:8000/workflows``.

## Project Structure
```
AutoFlow/
├─ src/
│  ├─ __init__.py
│  ├─ engine.py          # Core scheduler & executor
│  ├─ api.py             # FastAPI entry‑point
│  └─ plugins/
│     ├─ __init__.py
│     ├─ base.py         # Abstract plugin class
│     └─ example.py      # Sample plugin implementation
├─ requirements.txt
├─ README.md
├─ LICENSE
├─ .gitignore
└─ SECURITY.md
```

## Contributing
Feel free to submit PRs, add new plugins, or improve the AI‑hinting logic.  All contributions should follow the **PEP 8** style guide and include unit tests.

---
*Built with ❤️ for automation lovers, by a Python‑enthusiast who’s still slightly bored.*
