# DART

DART is a Streamlit-based dashboard and Python package for exploring ComEd real-time electricity pricing data through the [ComEd Hourly Pricing API](https://hourlypricing.comed.com/hp-api/).

The project is organized as a layered application with a modular visualization layer:

- `dart.api` handles ComEd API requests with retries and error handling
- `dart.services` contains business logic, aggregation workflows, and pure calculation helpers
- `dart.models` defines typed result objects (`PricePoint`, `PriceResponse`, `PriceStats`, `CustomRangeResult`)
- `dart.visualization` provides the Streamlit UI, split into independent section modules
- `dart.utils` contains shared helpers, audit logging, analytics tracking, and share-link utilities
- `dart.config` centralizes runtime settings with environment variable overrides

## What the App Does

DART focuses on a few practical pricing workflows:

- Shows the current hour average price from ComEd with context against the recent 24-hour range
- Displays the latest 24 hours of raw 5-minute pricing data with trend charts and hourly patterns
- Supports custom date range analysis with hourly aggregation, daily summaries, and sparkline profiles
- Exposes the raw records used to build each hourly aggregate for audit and verification
- Optionally writes structured audit logs for troubleshooting

## Requirements

- Python `3.10+`
- Internet access to reach the ComEd pricing API

## Installation

### Option 1: Install runtime dependencies only

```bash
git clone <repo-url>
cd DART-main
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Option 2: Install as a local package

This is the better option if you want the `dart` package available for imports and local development.

```bash
git clone <repo-url>
cd DART-main
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

For local development with test dependencies:

```bash
pip install -e ".[dev]"
```

Or using the dev requirements file:

```bash
pip install -r requirements-dev.txt
```

## Running the Application

### Launch the dashboard

```bash
python -m dart
```

Or run the Streamlit app directly:

```bash
streamlit run dart/visualization/app.py
```

### Test API connectivity from the CLI

```bash
python -m dart --test-api
```

The CLI connectivity check will:

- verify the ComEd API is reachable
- print the current hour average price
- print summary statistics for the latest 24-hour window

## Package Usage

### Low-level API client

Use `ComEdClient` if you want direct access to the ComEd endpoints.

```python
from datetime import datetime

from dart.api.comed_client import ComEdClient

client = ComEdClient()

latest = client.get_five_minute_prices()
print(f"Fetched {len(latest)} price points")
print(f"Average: {latest.average_price:.2f} cents/kWh")

start = datetime(2024, 1, 15, 8, 0)
end = datetime(2024, 1, 15, 17, 0)
historical = client.get_five_minute_prices_range(start, end)

current = client.get_current_hour_average()
print(current.timestamp, current.price)
```

### Service layer

Use `PricingService` if you want DataFrame-ready outputs and higher-level workflows.

```python
from datetime import date

from dart.services.pricing_service import PricingService

service = PricingService()

raw_df = service.get_last_24_hours()
timestamp, price = service.get_current_price()
stats = service.get_price_statistics()

result = service.get_custom_range_analysis(
    start_date=date(2024, 1, 15),
    end_date=date(2024, 1, 17),
)

print(result.hourly_data.head())
print(result.raw_stats.count, result.hourly_stats.average_price)
```

## Architecture Overview

```text
dart/
  __init__.py
  __main__.py
  api/
    comed_client.py          # ComEd HTTP client with retries
  config/
    settings.py              # Centralized env-var configuration
  models/
    pricing.py               # Typed data models
  services/
    pricing_calculations.py  # Pure aggregation / statistics helpers
    pricing_service.py       # High-level orchestration and audit logging
  utils/
    analytics.py             # Lightweight event tracking
    helpers.py               # Logging setup, retry decorator
    logger_util.py           # Streamlit log buffer
    pricing_audit_logger.py  # JSONL audit logger
    share_links.py           # Share URL builders
  visualization/
    app.py                   # Streamlit entry point and page orchestrator
    charts.py                # Reusable Altair chart builders
    data_layer.py            # Cached data access (Streamlit caching)
    formatting.py            # Price / timestamp display formatters
    ui_helpers.py            # View-model builders (highlights, narratives, profiles)
    sections/
      sidebar.py             # Sidebar controls and guidance
      header.py              # Page introduction
      live_snapshot.py       # Current-hour price section
      recent_prices.py       # Last 24-hour section
      custom_range.py        # Custom date-range analysis section
tests/
  conftest.py                # Shared test fixtures
  test_analytics.py
  test_comed_client.py
  test_formatting.py
  test_models.py
  test_package_layout.py
  test_pricing_audit_logger.py
  test_pricing_calculations.py
  test_pricing_service.py
  test_share_links.py
  test_ui_helpers.py
```

### Responsibilities by layer

- **`dart.api.comed_client`** wraps ComEd HTTP calls, retries, and response parsing
- **`dart.services.pricing_calculations`** contains pure aggregation and statistics helpers
- **`dart.services.pricing_service`** orchestrates data fetches, transforms, and audit logging
- **`dart.models.pricing`** provides `PricePoint`, `PriceResponse`, `PriceStats`, and `CustomRangeResult`
- **`dart.visualization.app`** configures the Streamlit page and orchestrates section renderers
- **`dart.visualization.data_layer`** manages Streamlit-cached data access
- **`dart.visualization.charts`** provides reusable Altair chart components
- **`dart.visualization.formatting`** handles price, timestamp, and delta display formatting
- **`dart.visualization.ui_helpers`** builds view-model objects (window highlights, price narratives, profiles)
- **`dart.visualization.sections.*`** each module renders one dashboard section independently

### Data flow

```text
ComEd API  →  ComEdClient  →  PricingService  →  data_layer (cached)  →  section renderers
                  ↓                 ↓
             PriceResponse    CustomRangeResult
                  ↓                 ↓
           pricing_calculations (pure functions)
```

## Configuration

Runtime configuration is centralized in `dart/config/settings.py` and can be overridden with environment variables.

| Variable | Default | Description |
|----------|---------|-------------|
| `COMED_API_BASE_URL` | `https://hourlypricing.comed.com/api` | Base URL for the ComEd pricing API |
| `COMED_REQUEST_TIMEOUT` | `30` | Request timeout in seconds |
| `RETRY_ATTEMPTS` | `3` | Number of retry attempts for API calls |
| `RETRY_DELAY` | `2` | Delay between retries in seconds |
| `DASHBOARD_TITLE` | `ComEd Real-Time Pricing Dashboard` | Browser/page title for the Streamlit app |
| `AUTO_REFRESH_SECONDS` | `300` | Refresh interval shown in the dashboard sidebar |
| `DASHBOARD_SHARE_BASE_URL` | `http://localhost:8501` | Base URL used by share-link helpers |
| `ANALYTICS_EVENTS_FILE` | `.dart/analytics_events.jsonl` | JSONL file for lightweight analytics events |
| `PRICING_AUDIT_ENABLED` | `true` | Enables structured audit logging for custom-range analysis |
| `PRICING_AUDIT_FILE` | `.dart/pricing_audit.jsonl` | JSONL output path for pricing audit events |
| `PRICING_AUDIT_SAMPLE_LIMIT` | `500` | Maximum number of records included per audit section |

## Audit Logging

When `PRICING_AUDIT_ENABLED=true`, custom range analysis writes a JSONL event to `PRICING_AUDIT_FILE`.

Each event includes:

- requested start and end dates
- expanded datetime bounds used for the fetch
- raw 5-minute values included in the calculation
- computed hourly averages
- per-hour reconciliation context, including raw bucket counts and timestamp bounds
- raw and hourly summary statistics

This is useful when validating aggregation behavior or investigating unexpected pricing results.

## Testing

Run the test suite with:

```bash
pytest tests -v
```

If you want coverage output, install `pytest-cov` separately and run:

```bash
pytest tests -v --cov=dart
```

Shared test fixtures are defined in `tests/conftest.py` and automatically available to all test modules.

## API Endpoints

DART currently uses these ComEd API endpoints:

1. `?type=5minutefeed` for the most recent 24-hour 5-minute feed
2. `?type=5minutefeed&datestart=...&dateend=...` for historical range queries
3. `?type=currenthouraverage` for the current hour average price

See the official [ComEd Hourly Pricing API documentation](https://hourlypricing.comed.com/hp-api/) for endpoint details and response semantics.

## Notes

- The installable package name is `dart-pricing-pipeline`
- The importable Python package is `dart`
- Packaging is managed via `pyproject.toml` (PEP 621)
- Runtime artifacts such as audit logs are written under `.dart/` by default
- Production dependencies are listed in `requirements.txt`; dev dependencies (including pytest) are in `requirements-dev.txt`

## License

MIT
