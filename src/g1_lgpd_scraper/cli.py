"""Interface de linha de comando. Ver README.md para exemplos de uso."""

import argparse
from pathlib import Path

from g1_lgpd_scraper.config import ScraperConfig
from g1_lgpd_scraper.pipeline import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Coleta resultados de busca do G1.")
    parser.add_argument("--query", default="lgpd", help="Termo de busca (default: lgpd)")
    parser.add_argument("--start-page", type=int, default=1, help="Primeira pagina a coletar (default: 1)")
    parser.add_argument("--max-pages", type=int, default=5, help="Numero maximo de paginas (default: 5)")
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--request-delay-seconds", type=float, default=1.0)
    parser.add_argument("--request-timeout-seconds", type=float, default=30.0)
    parser.add_argument("--max-retries", type=int, default=3)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = ScraperConfig(
        query=args.query,
        start_page=args.start_page,
        max_pages=args.max_pages,
        output_dir=args.output_dir,
        request_delay_seconds=args.request_delay_seconds,
        request_timeout_seconds=args.request_timeout_seconds,
        max_retries=args.max_retries,
    )
    summary = run(config)
    print(
        f"Execucao {summary.run_id}: {summary.total_collected} coletados, "
        f"{summary.total_after_dedup} apos dedup, {summary.total_duplicate_of_previous_run} "
        f"ja vistos em execucao anterior.\nCSV: {summary.csv_path}\nJSON: {summary.json_path}"
    )


if __name__ == "__main__":
    main()
