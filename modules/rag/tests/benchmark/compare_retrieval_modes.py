"""A/B evaluation: single-pass retrieval vs the bounded agentic loop.

Both paths stay in the codebase; this measures them against the same suites,
the same documents and the same ground truth so the agentic loop can be adopted
(or rejected) on evidence rather than on principle.

Run:
    python -m modules.rag.tests.benchmark.compare_retrieval_modes
    python -m modules.rag.tests.benchmark.compare_retrieval_modes --suite multilingual
    python -m modules.rag.tests.benchmark.compare_retrieval_modes --json out.json

No LLM and no network: refinement is deterministic and embeddings run locally.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Dict, List

from modules.rag.tests.benchmark.benchmark_engine import BenchmarkEngine
from modules.rag.tests.benchmark.metrics import BenchmarkReport
from modules.rag.tests.benchmark.test_suites import ALL_SUITES

MODES = ("single_pass", "agentic")

# Higher is better for everything except latency. Ranking metrics need labelled
# relevant chunks; without them they are vacuous (recall/nDCG are 1.0 because
# nothing was expected, precision/MRR are 0.0), so they are hidden rather than
# printed as if they measured something.
_ALWAYS_ROWS = [
    ("grounded_rate", "Grounded rate", "share of queries that ended up usable"),
    ("risk_accuracy", "Risk accuracy", "risk level matched expectation"),
]
_GROUND_TRUTH_ROWS = [
    ("mrr", "MRR", "rank of the first relevant chunk"),
    ("mean_precision", "Precision@K", ""),
    ("mean_recall", "Recall@K", ""),
    ("mean_ndcg", "nDCG@K", ""),
]


def _fmt_delta(single: float, agentic: float, higher_is_better: bool = True) -> str:
    delta = agentic - single
    if abs(delta) < 1e-9:
        return "   ="
    better = delta > 0 if higher_is_better else delta < 0
    return f"{delta:+.3f} {'✓' if better else '✗'}"


def _print_suite(suite_key: str, reports: Dict[str, BenchmarkReport]) -> None:
    single, agentic = reports["single_pass"], reports["agentic"]

    print(f"\n{'=' * 78}")
    print(f"  {single.suite_name}  ({single.num_queries} queries)")
    print(f"{'=' * 78}")
    print(f"  {'metric':<16}{'single-pass':>14}{'agentic':>12}{'delta':>14}   note")
    print(f"  {'-' * 72}")

    has_ground_truth = any(q.expected_chunk_ids for q in single.query_results)
    rows = _ALWAYS_ROWS + (_GROUND_TRUTH_ROWS if has_ground_truth else [])

    for attr, label, note in rows:
        s_val, a_val = getattr(single, attr), getattr(agentic, attr)
        print(f"  {label:<16}{s_val:>14.3f}{a_val:>12.3f}{_fmt_delta(s_val, a_val):>14}   {note}")

    if not has_ground_truth:
        print(f"  {'Precision/MRR/':<16}{'n/a':>14}{'n/a':>12}{'':>14}   "
              "this suite ships no labelled")
        print(f"  {'nDCG/Recall':<16}{'':>14}{'':>12}{'':>14}   "
              "expected_chunk_ids")

    print(f"  {'-' * 72}")
    for attr, label in [("latency_p50", "Latency p50 ms"), ("latency_p95", "Latency p95 ms")]:
        s_val, a_val = getattr(single, attr), getattr(agentic, attr)
        cost = (a_val / s_val - 1) * 100 if s_val else 0.0
        print(f"  {label:<16}{s_val:>14.1f}{a_val:>12.1f}{cost:>13.1f}%   cost of refinement")

    refined = [q for q in agentic.query_results if q.attempts > 1]
    print(f"  {'-' * 72}")
    print(f"  Refined {len(refined)}/{agentic.num_queries} queries "
          f"({agentic.refinement_rate * 100:.0f}%)")

    # The point of the loop: queries that were unusable single-pass and became
    # grounded after one refinement.
    by_query = {q.query_text: q for q in single.query_results}
    rescued, unchanged = [], []
    for q in refined:
        before = by_query.get(q.query_text)
        if before is None:
            continue
        (rescued if (q.has_sufficient_context and not before.has_sufficient_context) else unchanged).append(q)

    for q in rescued:
        print(f"    ✓ RESCUED  {q.query_text[:46]!r}")
        print(f"               → {q.refined_query!r}")
    for q in unchanged:
        print(f"    · no gain  {q.query_text[:46]!r} (fell back to single-pass result)")

    # A cross-domain query that becomes "grounded" after refinement would be a
    # hallucination risk, not a win — call it out loudly.
    regressions = [
        q for q in agentic.query_results
        if q.expected_risk_level and not q.risk_match
        and (rq := by_query.get(q.query_text)) and rq.risk_match
    ]
    if regressions:
        print("\n  ⚠ RISK REGRESSIONS (agentic weakened rejection):")
        for q in regressions:
            print(f"    ✗ {q.query_text[:50]!r} expected={q.expected_risk_level} got={q.risk_level}")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", action="append", choices=sorted(ALL_SUITES),
                        help="suite to run (repeatable); default: all")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", metavar="PATH", help="write the full comparison as JSON")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    suites = args.suite or sorted(ALL_SUITES)
    engine = BenchmarkEngine()
    everything: Dict[str, Dict[str, dict]] = {}

    for suite_key in suites:
        reports: Dict[str, BenchmarkReport] = {}
        for mode in MODES:
            print(f"running {suite_key} [{mode}] …", file=sys.stderr, flush=True)
            # run_suite re-initialises the service, so each mode gets a cold
            # retrieval cache and the latency comparison stays honest.
            reports[mode] = engine.run_suite(suite_key, top_k=args.top_k, mode=mode)
        _print_suite(suite_key, reports)
        everything[suite_key] = {mode: report.to_dict() for mode, report in reports.items()}

    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(everything, handle, indent=2)
        print(f"\nFull comparison written to {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
