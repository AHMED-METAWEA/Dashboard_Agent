# 🚀 Dashboard Agent — AI-Powered Interactive Dashboard Generator

An AI-powered system that reads any cleaned dataset and produces a single self-contained interactive HTML dashboard file that looks and feels like a professional Power BI executive report.

## Features

- **AI-Powered Analysis**: Uses Groq (Llama 3.3 70B) to detect dataset domain and select optimal chart configurations
- **Self-Contained Output**: Single HTML file — no server needed, opens in any browser
- **Dark/Light Theme Toggle**: Professional Power BI-style theming
- **Interactive Cross-Filtering**: Sidebar filters update all charts and KPIs simultaneously
- **Smart KPI Extraction**: Rule-based detection of 4–6 key performance indicators
- **6–10 Charts**: Automatically selected based on data characteristics
- **Large Dataset Support**: Automatic sampling for datasets > 100K rows

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your Groq API key

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 3. Run the agent

```bash
python generate.py --file your_data.csv
```

### 4. Open the dashboard

Open `dashboard_output.html` in any browser.

## Supported File Formats

| Format | Extensions |
|--------|-----------|
| CSV/TSV | `.csv`, `.tsv` |
| Excel | `.xlsx`, `.xls` |
| JSON | `.json` |

## CLI Options

```
python generate.py --file DATA_FILE [--output OUTPUT.html] [--theme dark|light]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--file`, `-f` | Path to dataset file (required) | — |
| `--output`, `-o` | Output HTML file path | `dashboard_output.html` |
| `--theme`, `-t` | Default theme (`dark` or `light`) | `dark` |

## Project Structure

```
dashboard_agent/
├── generate.py              ← CLI entry point
├── agent/
│   ├── profiler.py          ← Column type detection + domain detection via Groq
│   ├── chart_selector.py    ← Groq-powered chart selection + validation
│   ├── kpi_extractor.py     ← Rule-based KPI detection
│   ├── html_builder.py      ← Assembles the final HTML file
│   └── html_template.py     ← Jinja2 HTML template string
├── utils/
│   ├── data_loader.py       ← CSV/XLSX/JSON loader with validation
│   ├── json_parser.py       ← Robust Groq JSON response extractor
│   └── formatters.py        ← Number formatters: K/M/B, %, currency
├── config/
│   └── settings.py          ← Constants, Groq model config, thresholds
├── requirements.txt
├── .env.example
└── README.md
```

## Configuration

All settings are in `config/settings.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq LLM model |
| `SAMPLE_THRESHOLD` | `100,000` | Row count to trigger sampling |
| `MIN_CHARTS` | `6` | Minimum charts in dashboard |
| `MAX_CHARTS` | `10` | Maximum charts in dashboard |
| `DEFAULT_THEME` | `dark` | Initial theme |

## License

MIT
# Dashboard_Agent
