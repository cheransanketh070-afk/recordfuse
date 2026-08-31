# Algorithm

RecordFuse uses a deterministic eight-stage pipeline.

1. **Normalize** values without replacing the original raw values used in audit output.
2. **Block** on selective keys so most impossible pairs are never scored.
3. **Score** each available configured field and retain field-level evidence.
4. **Veto** explicit strong-identifier contradictions unless another exact identifier provides a bridge.
5. **Decide** `match`, `ambiguous`, or `rejected` using configurable thresholds.
6. **Constrained cluster** accepted edges with union-find, refusing unions that would introduce incompatible strong identifiers through transitivity.
7. **Merge** fields using source priority only after identity clustering.
8. **Report** canonical entities, provenance, conflicts, confidence, warnings, and metrics.

## Similarity

Names use the better of normalized Levenshtein ratio and token Jaccard similarity. Email and phone are exact identifiers by default. Only fields present on both sides contribute to a pair's denominator, which avoids treating missing data as contradictory evidence.

## Blocking complexity

An unconditional pair scan costs O(n²). RecordFuse builds inverted buckets and compares records only inside buckets. Expected work is approximately O(n + Σbᵢ²), bounded further by `max_bucket_size`; oversized buckets are skipped and counted in metrics. Blocking is a recall/compute trade-off, so deployments should measure candidate recall on labeled data.

## Constrained clustering

A standard union-find graph can over-merge transitively. For example, A may match B by email while B matches C by phone even though A and C have different emails. Before each union, RecordFuse inspects identifier sets already present in both components. A union can be blocked when those sets contradict without a bridge in the current decision.

## Determinism

Input order does not control IDs or output order. Candidate pairs are sorted, high-confidence edges are processed first, union roots are tie-broken deterministically, run IDs hash canonicalized input, and cluster IDs hash sorted member IDs.
