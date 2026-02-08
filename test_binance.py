import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("--- BINANCE DIAGNOSTIC TOOL ---")


def test_import():
    print("\n1. Testing Imports...")
    try:
        import pydantic
        from binance.client import Client

        print("✅ binance.client imported successfully.")
        print(
            f"✅ pydantic version: {pydantic.VERSION if hasattr(pydantic, 'VERSION') else 'unknown'}"
        )
        return Client
    except ImportError as e:
        print(f"❌ IMPORT ERROR: {e}")
        return None
    except Exception as e:
        print(f"❌ UNEXPECTED IMPORT ERROR: {e}")
        return None


def test_connectivity(Client):
    print("\n2. Testing Connectivity (Exchange Info)...")
    try:
        # Public client
        client = Client(None, None)
        info = client.get_exchange_info()
        symbols = [
            s["symbol"]
            for s in info["symbols"]
            if s["quoteAsset"] == "USDT" and s["status"] == "TRADING"
        ]
        print(f"✅ Success! Found {len(symbols)} active USDT pairs.")
        return client, symbols[0] if symbols else "BTCUSDT"
    except Exception as e:
        print(f"❌ CONNECTIVITY ERROR: {e}")
        return None, None


def test_historical_data(client, symbol):
    print(f"\n3. Testing Historical Data (Klines) for {symbol}...")
    try:
        # Fetch 1 day of data
        klines = client.get_historical_klines(symbol, "1d", "2 days ago UTC")
        if klines and len(klines) > 0:
            print(f"✅ Success! Retrieved {len(klines)} candles.")
            print(f"Sample data: {klines[0][:5]}")  # Print timestamp, open, high, low, close
        else:
            print("⚠️ retrieved empty data list.")
    except Exception as e:
        print(f"❌ DATA FETCH ERROR: {e}")


if __name__ == "__main__":
    Client = test_import()
    if Client:
        client, symbol = test_connectivity(Client)
        if client and symbol:
            test_historical_data(client, symbol)

    print("\n--- DIAGNOSIS COMPLETE ---")
    print("If you see errors above, please share them.")
