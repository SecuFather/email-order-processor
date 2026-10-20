# Agent Guidelines & Rules

## Code Philosophy

- **No Defensive Programming**: Do not add speculative fallbacks, unnecessary `try/except` blocks, null checks where types or contracts guarantee values, or wrapper shims unless explicitly asked.
- **No Redundant Code**: Avoid duplicate operations, redundant method calls (e.g. repeated `.lower()`), and dead or repetitive logic. Keep implementations minimal, direct, and concise.
