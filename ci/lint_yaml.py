"""Lint all project YAML without a pipeline/subshell exit-status bug."""
from pathlib import Path
import sys
from yamllint.config import YamlLintConfig
from yamllint import linter

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".venv", ".local", "output", "__pycache__"}
CONFIG = YamlLintConfig("""extends: default
rules:
  document-start: disable
  line-length:
    max: 180
    level: warning
  truthy:
    allowed-values: ['true', 'false']
    check-keys: false
""")

def problems(path):
    return list(linter.run(path.read_text(encoding="utf-8"), CONFIG))

def main():
    errors = 0
    paths = sorted(p for p in ROOT.rglob("*") if p.suffix in {".yml", ".yaml"} and not EXCLUDED.intersection(p.relative_to(ROOT).parts))
    for path in paths:
        for issue in problems(path):
            print(f"{path.relative_to(ROOT)}:{issue.line}:{issue.column}: {issue.level}: {issue.desc}")
            errors += issue.level == "error"
    print(f"Checked {len(paths)} YAML files; {errors} errors")
    return int(errors > 0)

if __name__ == "__main__":
    sys.exit(main())
