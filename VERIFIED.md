# Release verification

September 28, 2026, from a new clone of public commit `5220f88` and a new
Python 3.12 environment:

- Package installation resolved the pinned ACI Patch Agent dependency.
- All four fault-behavior tests passed.
- Both pilot and full reports regenerated from the committed traces without a
  Git diff. Report generation requires no model key and makes no model calls.
- GitHub Actions passed the installation and unit checks on Linux/Python 3.11.
- Gitleaks found no secrets in the publication history.

The 70 original live attempts exercised the Docker evaluator and hosted model.
The fresh-clone report check verifies reproducibility of the saved tables; it does
not claim to reproduce the same model trajectories or independently rerun every
live attempt. All original successes, failures, and API errors remain committed.
