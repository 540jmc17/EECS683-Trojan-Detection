# EECS 683 — Hardware Trojan Detection

**University of Kansas — Fall 2026**

**Project:** Gate-Level Security Analysis and Adversarial Trojan Evasion

## Project Overview

Our goal is to build a Python program that analyzes digital circuits to identify potentially malicious hardware Trojans.

We will extract security-related features, develop a Trojan detection method, and test how modifying a Trojan affects detection.

## Team Responsibilities

| Member | Responsibility |
|---|---|
| Jake | Netlist Parser — Read circuit files and identify gates, wires, and connections |
| Bryant | Structural Features — Calculate fan-in, fan-out, logic depth, etc. |
| Person 3 | Security Features & Validation — Calculate controllability, observability, rarity, and verify results |
| Person 4 | Trojan Detection — Implement unsupervised detection and evaluate performance |
| Person 5 | Trojan Modification & Simulation — Modify Trojan logic and test circuit behavior |

Everyone will contribute to integration, debugging, adversarial testing, and the final report.

## Project Requirements

- [ ] Extract at least 10 features per net across at least 6 netlists
- [ ] Include at least 2 security-motivated features
- [ ] Manually validate selected features for at least 3 nets
- [ ] Implement unsupervised Trojan detection
- [ ] Evaluate false positives, false negatives, precision, and recall
- [ ] Modify and simulate at least one Trojan design
- [ ] Compare original and modified detection results
- [ ] Complete final report and demonstration

## Project Files

- `src/` — Python implementation
- `tests/` — Testing and validation
- `netlists/` — Circuit input files
- `simulation/` — Simulation files
- `results/` — Feature CSV files and detection results
- `docs/` — Documentation and reports

## Collaboration

Each team member should:

1. Work on their own GitHub branch.
2. Push their code and changes regularly.
3. Open a pull request when their work is ready.
4. Review and test code before merging into `main`.
5. Update their assigned GitHub Issue as work progresses.

## Important Links

**Team Google Doc:** [Add Shared Google Doc Link]

**Example Netlists:** https://github.com/santoshsmalagi/Benchmarks/tree/main/ISCAS89

**Project Deadline:** TBD

## Current Progress

Project setup is underway. Individual implementation work will begin after the team confirms assignments and shared code interfaces.
