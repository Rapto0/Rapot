from investiny import economic_calendar

try:
    print("Fetching investing.com calendar...")
    data = economic_calendar()
    print("Success!")
    print(data.head())
    print(data.columns)
except Exception as e:
    print(f"Error: {e}")
