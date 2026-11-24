# Failure
A naive LLM-only approach can report 7.2 months for $250,000 cash / $36,500 burn.
# Why it failed
The model was used as the arithmetic engine.
# Impact
A plausible but wrong runway can distort liquidity interpretation.
# Investigation
Deterministic calculation gives 6.8493 months.
# Fix
Move arithmetic to `calculate_runway()` and add a golden test with tolerance.
# Result
The source of truth is reproducible and regression-tested.
# Learning
LLMs should interpret financial calculations, not be the source of truth for arithmetic.
