import argparse
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table

from .rag_pipeline import RAGPipeline

console = Console()


def main():
    parser = argparse.ArgumentParser(description="Simple offline-first RAG demo")
    parser.add_argument("query", type=str, help="Your question")
    parser.add_argument("--data", type=str, default=str(Path(__file__).parents[2] / "data"), help="Path to data dir")
    parser.add_argument("--k", type=int, default=4, help="Top-k chunks")
    parser.add_argument("--provider", type=str, choices=["offline", "openai"], default="offline")
    parser.add_argument("--model", type=str, default="gpt-4o-mini")
    parser.add_argument("--json", action="store_true", help="Print JSON output")

    args = parser.parse_args()
    use_openai = args.provider == "openai"

    pipe = RAGPipeline(args.data, use_openai=use_openai, model=args.model)
    pipe.build()
    res = pipe.query(args.query, k=args.k)

    if args.json:
        print(json.dumps(res, indent=2))
        return

    console.rule("RAG Answer")
    console.print(res["answer"])

    table = Table(title="Top Sources", show_lines=True)
    table.add_column("Rank")
    table.add_column("Doc")
    table.add_column("Chunk")
    table.add_column("Score")
    table.add_column("Preview")

    for i, s in enumerate(res["sources"], start=1):
        table.add_row(str(i), s["doc"], str(s["chunk"]), f"{s['score']:.3f}", s["preview"])
    console.print(table)


if __name__ == "__main__":
    main()
