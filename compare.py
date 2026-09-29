"""Compare Jev and gpt-4o-mini triage results."""
import json
import os

from dotenv import load_dotenv

from common import RESULTS_DIR, save

load_dotenv()

JEV_INPUT_PER_M = 0.042   # docs.typesafe.ai/models: $0.042 per 1M input tokens, output free
# Published per-1M-token list prices for the comparison LLM (defaults: OpenAI gpt-4o-mini).
# For a free-tier model, set these to its paid-tier list price so cost is comparable.
GPT_INPUT_PER_M = float(os.getenv("LLM_INPUT_PER_M", "0.15"))
GPT_OUTPUT_PER_M = float(os.getenv("LLM_OUTPUT_PER_M", "0.60"))
FIELDS = ["category", "priority", "needs_more_info", "duplicate_likely"]


def load(name):
    rows = json.loads((RESULTS_DIR / name).read_text(encoding="utf-8"))
    return {r["number"]: r for r in rows}


def fmt(r):
    if r.get("parse_error"):
        return "PARSE-ERR"
    yn = lambda b: "Y" if b else "N"
    return (f"{r['category'][:4]} p{r['priority']} "
            f"i={yn(r['needs_more_info'])} d={yn(r['duplicate_likely'])}")


def main():
    jev, llm = load("jev_results.json"), load("llm_results.json")
    numbers = sorted(set(jev) & set(llm))

    llm_model = next(iter(llm.values())).get("model", "LLM")
    print(f"{'Issue':<8}{'Title':<44}{'Jev':<20}{llm_model[:19]:<20}Disagree")
    print("-" * 110)
    disagreements = []
    for n in numbers:
        j, l = jev[n], llm[n]
        if l.get("parse_error"):
            diff = ["(LLM parse failure)"]
        else:
            diff = [f for f in FIELDS if j[f] != l[f]]
        if diff:
            disagreements.append({
                "number": n, "title": j["title"], "fields": diff,
                "jev": {f: j.get(f) for f in FIELDS},
                "llm": {f: l.get(f) for f in FIELDS},
            })
        print(f"#{n:<7}{j['title'][:42]:<44}{fmt(j):<20}{fmt(l):<20}{', '.join(diff) or '-'}")

    jev_cost = sum(r["input_tokens"] for r in jev.values()) * JEV_INPUT_PER_M / 1e6
    llm_cost = sum(r["input_tokens"] * GPT_INPUT_PER_M + r["output_tokens"] * GPT_OUTPUT_PER_M
                   for r in llm.values()) / 1e6
    summary = {
        "llm_model": llm_model,
        "issues_compared": len(numbers),
        "jev_avg_latency_s": sum(r["latency_s"] for r in jev.values()) / len(jev),
        "llm_avg_latency_s": sum(r["latency_s"] for r in llm.values()) / len(llm),
        "jev_total_input_tokens": sum(r["input_tokens"] for r in jev.values()),
        "llm_total_input_tokens": sum(r["input_tokens"] for r in llm.values()),
        "llm_total_output_tokens": sum(r["output_tokens"] for r in llm.values()),
        "jev_total_cost_usd": jev_cost,
        "llm_total_cost_usd": llm_cost,
        "llm_parse_failures": sum(1 for r in llm.values() if r.get("parse_error")),
        "issues_with_disagreement": len(disagreements),
        "per_field_disagreements": {f: sum(f in d["fields"] for d in disagreements) for f in FIELDS},
        "disagreements": disagreements,
    }
    save("summary.json", summary)

    print("\n=== SUMMARY ===")
    for k, v in summary.items():
        if k != "disagreements":
            print(f"{k}: {v:.6f}" if isinstance(v, float) else f"{k}: {v}")


if __name__ == "__main__":
    main()
