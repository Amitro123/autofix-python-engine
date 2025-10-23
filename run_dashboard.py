import subprocess
from pathlib import Path

dashboard_path = Path(__file__).parent / "autofix_core" / "infrastructure" / "integrations" / "reflex_dashboard"
print(f" Starting Dashboard from: {dashboard_path}")
subprocess.run(["reflex", "run"], cwd=dashboard_path)
