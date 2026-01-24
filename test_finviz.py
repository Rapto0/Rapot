import requests
from bs4 import BeautifulSoup


def get_finviz_calendar():
    url = "https://finviz.com/calendar.ashx"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            # Finviz has a nice table structure
            soup = BeautifulSoup(response.content, "html.parser")
            # The calendar is usually in a div with specific class or just the main content
            # Let's inspect the first few table rows
            rows = soup.find_all("tr", {"class": "calendar-row"})
            print(f"Found {len(rows)} events")
            for row in rows[:5]:
                # Extract columns
                cols = row.find_all("td")
                if len(cols) >= 9:
                    time = cols[0].text.strip()
                    currency = cols[2].text.strip()
                    _impact = cols[3].find("img")["src"] if cols[3].find("img") else "low"
                    event = cols[4].text.strip()
                    actual = cols[5].text.strip()
                    forecast = cols[6].text.strip()
                    _prev = cols[7].text.strip()

                    print(f"{time} | {currency} | {event} | {actual} vs {forecast}")
            return True
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    get_finviz_calendar()
