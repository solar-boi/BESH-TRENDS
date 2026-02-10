# DART - ComEd Real-Time Pricing Dashboard

A real-time electricity pricing dashboard using the [ComEd Hourly Pricing API](https://hourlypricing.comed.com/hp-api/).

## Features

- **Real-time pricing**: View current hour average electricity prices
- **5-minute granularity**: Access 5-minute interval pricing data for the last 24 hours
- **Custom date ranges**: Query historical pricing data for any time period
- **Price statistics**: View min, max, average prices and distributions
- **Interactive charts**: Visualize pricing trends with Plotly

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd DART-main

# Install dependencies
pip install -r requirements.txt
```

### Test API Connectivity

```bash
python -m src --test-api
```

### Run the Dashboard

```bash
python -m src
# or directly:
streamlit run src/visualization/app.py
```

## Project Structure

```
src/
  __init__.py           # Package exports
  __main__.py           # CLI entry point
  api/
    comed_client.py     # ComEd API client
  config/
    settings.py         # Configuration
  models/
    pricing.py          # Data models (PricePoint, PriceResponse)
  services/
    pricing_service.py  # Business logic layer
  utils/
    helpers.py          # Utility functions
  visualization/
    app.py              # Streamlit dashboard
tests/
  test_comed_client.py  # API client tests
  test_models.py        # Data model tests
  test_pricing_service.py # Service layer tests
```

## API Reference

### ComEdClient

The main API client for interacting with the ComEd Hourly Pricing API.

```python
from src.api.comed_client import ComEdClient

client = ComEdClient()

# Get 5-minute prices for last 24 hours
response = client.get_five_minute_prices()
print(f"Got {len(response)} price points")
print(f"Average: {response.average_price:.2f}¢/kWh")

# Get prices for a custom time range
from datetime import datetime
start = datetime(2024, 1, 15, 8, 0)
end = datetime(2024, 1, 15, 17, 0)
response = client.get_five_minute_prices_range(start, end)

# Get current hour average
price_point = client.get_current_hour_average()
print(f"Current price: {price_point.price:.2f}¢/kWh")
```

### PricingService

High-level service for common operations with DataFrame outputs.

```python
from src.services.pricing_service import PricingService

service = PricingService()

# Get last 24 hours as DataFrame
df = service.get_last_24_hours()

# Get current price
timestamp, price = service.get_current_price()

# Get statistics
stats = service.get_price_statistics()
print(f"Min: {stats['min']:.2f}¢, Max: {stats['max']:.2f}¢")
```

## Configuration

Configuration is managed via environment variables or `src/config/settings.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `COMED_API_BASE_URL` | `https://hourlypricing.comed.com/api` | API base URL |
| `COMED_REQUEST_TIMEOUT` | `30` | Request timeout (seconds) |
| `RETRY_ATTEMPTS` | `3` | Number of retry attempts |
| `RETRY_DELAY` | `2` | Delay between retries (seconds) |

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src
```

## API Endpoints Used

This project uses the following ComEd Hourly Pricing API endpoints:

1. **5-Minute Feed** (`?type=5minutefeed`): Returns all 5-minute prices from the last 24 hours
2. **5-Minute Feed with Range** (`?type=5minutefeed&datestart=...&dateend=...`): Returns prices for a custom time range
3. **Current Hour Average** (`?type=currenthouraverage`): Returns the current hour's average price

See the [official API documentation](https://hourlypricing.comed.com/hp-api/) for more details.

## License

MIT
