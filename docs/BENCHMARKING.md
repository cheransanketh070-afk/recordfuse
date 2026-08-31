# Benchmarking and Calibration

A high-quality entity-resolution deployment should evaluate both pair classification and final clusters on labeled data.

Recommended pair metrics: precision, recall, F1, false-merge rate, and candidate-pair recall before scoring. For cluster quality, measure pairwise cluster precision/recall or B-cubed metrics. Track the blocking reduction ratio alongside recall; a large reduction ratio is only useful if true candidate pairs survive blocking.

For threshold calibration, split labeled examples into calibration and holdout sets. Favor precision when false merges are expensive. Record the exact rules, thresholds, source-priority map, and dataset version with each benchmark so results are reproducible.
