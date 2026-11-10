"""Install only the reusable skill resources, without overwriting an existing skill."""
from pathlib import Path
import os
import shutil
import argparse
import tempfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--codex-home', type=Path, default=Path(os.environ.get('CODEX_HOME', Path.home()/'.codex')))
    a = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    parent = a.codex_home.resolve()/'skills'
    target = parent/'scientific-figure-optimizer'
    if target.exists():
        p.error('Target already exists; review or choose a separate home')
    parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.sfo-install-', dir=parent))
    try:
        shutil.copyfile(root/'SKILL.md', staging/'SKILL.md')
        for name in ['requirements-lock.txt', 'LICENSE']:
            shutil.copyfile(root/name, staging/name)
        for folder in ['scripts', 'references', 'assets']:
            shutil.copytree(root/folder, staging/folder, ignore=shutil.ignore_patterns('__pycache__'))
        staging.rename(target)
    except BaseException:
        shutil.rmtree(staging)
        raise
    print(target)


if __name__ == '__main__':
    main()
