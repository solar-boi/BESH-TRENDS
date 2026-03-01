"""
DART (Data Acquisition and Real-time Tracking) - Main Entry Point

This module serves as the main entry point for the DART package.

Usage:
    python -m src                    # Run the Streamlit dashboard
    python -m src --test-api         # Test API connectivity
"""
import argparse
import sys
from pathlib import Path

from src.utils.helpers import configure_logging

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

configure_logging()


def test_api():
    """Test API connectivity and display sample data."""
    from src.services.pricing_service import PricingService
    
    print("Testing ComEd API connectivity...")
    service = PricingService()
    
    if service.is_api_available():
        print("✓ API is available")
        
        # Get current price
        timestamp, price = service.get_current_price()
        print(f"\n📊 Current Hour Average:")
        print(f"   Time: {timestamp}")
        print(f"   Price: {price:.2f}¢/kWh")
        
        # Get statistics
        stats = service.get_price_statistics()
        print(f"\n📈 Last 24 Hours Statistics:")
        print(f"   Data points: {stats['count']}")
        print(f"   Average: {stats['average']:.2f}¢/kWh")
        print(f"   Min: {stats['min']:.2f}¢/kWh")
        print(f"   Max: {stats['max']:.2f}¢/kWh")
        
        return 0
    else:
        print("✗ API is not available")
        return 1


def run_dashboard():
    """Launch the Streamlit dashboard."""
    import subprocess
    
    app_path = Path(__file__).parent / "visualization" / "app.py"
    print(f"Starting dashboard: {app_path}")
    
    subprocess.run(["streamlit", "run", str(app_path)])


def main():
    """Main entry point for the DART package."""
    parser = argparse.ArgumentParser(
        description="DART - ComEd Real-Time Pricing Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m src                    # Run the dashboard
    python -m src --test-api         # Test API connectivity
        """,
    )
    
    parser.add_argument(
        "--test-api",
        action="store_true",
        help="Test API connectivity and display sample data",
    )
    
    args = parser.parse_args()
    
    if args.test_api:
        sys.exit(test_api())
    else:
        run_dashboard()


if __name__ == "__main__":
    main()
