"""
Dashboard Agent — CLI Entry Point
Run: python generate.py --file data.csv
"""

import sys
import os
import logging
import click

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from config.settings import GROQ_API_KEY, OUTPUT_FILE
from utils.data_loader import load_dataset, DataLoadError
from agent.profiler import profile_dataset
from agent.kpi_extractor import extract_kpis
from agent.chart_selector import select_charts
from agent.html_builder import build_dashboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--file", "-f", required=True, help="Path to dataset (CSV, XLSX, JSON)")
@click.option("--output", "-o", default=OUTPUT_FILE, help="Output HTML file path")
@click.option("--theme", "-t", default=None, type=click.Choice(["dark", "light"]), help="Default theme")
def main(file, output, theme):
    """AI-powered Dashboard Agent — generates a Power BI-style interactive HTML dashboard."""

    click.echo()
    click.echo("━" * 60)
    click.echo("  🚀  Dashboard Agent — AI-Powered Report Generator")
    click.echo("━" * 60)
    click.echo()

    api_key = GROQ_API_KEY
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        click.echo("❌  GROQ_API_KEY not found. Set it in .env or as environment variable.")
        sys.exit(1)

    from groq import Groq
    groq_client = Groq(api_key=api_key)

    if theme:
        import config.settings as cfg
        cfg.DEFAULT_THEME = theme

    # Step 1 — Load dataset
    click.echo(f"📂  Loading dataset: {file}")
    try:
        df = load_dataset(file)
    except DataLoadError as e:
        click.echo(f"❌  {e}")
        sys.exit(1)
    click.echo(f"   ✅  Loaded {len(df):,} rows × {len(df.columns)} columns")

    # Step 2 — Profile dataset
    click.echo("🔍  Profiling dataset & detecting domain...")
    profile = profile_dataset(df, groq_client)
    click.echo(f"   ✅  Domain: {profile.domain} ({profile.domain_confidence}% confidence)")
    click.echo(f"   ✅  Numeric: {len(profile.numeric_cols)}, Categorical: {len(profile.categorical_cols)}, "
               f"Datetime: {len(profile.datetime_cols)}")

    # Step 3 — Extract KPIs
    click.echo("📊  Extracting KPI metrics...")
    kpis = extract_kpis(profile)
    click.echo(f"   ✅  {len(kpis)} KPIs: {', '.join(k.label for k in kpis)}")

    # Step 4 — Select charts
    click.echo("📈  Selecting charts via AI...")
    charts = select_charts(profile, groq_client)
    click.echo(f"   ✅  {len(charts)} charts selected")
    for c in charts:
        marker = "★" if c.is_primary else "·"
        click.echo(f"       {marker} {c.title} ({c.chart_type})")

    # Step 5 — Build dashboard
    click.echo("🏗️  Building interactive dashboard...")
    output_path = build_dashboard(profile, kpis, charts, output)
    click.echo()
    click.echo("━" * 60)
    click.echo(f"  ✅  Dashboard saved to: {output_path}")
    click.echo(f"  🌐  Open in any browser — no server needed!")
    click.echo("━" * 60)
    click.echo()


if __name__ == "__main__":
    main()
