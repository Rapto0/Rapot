import requests
from bs4 import BeautifulSoup


def get_widget_calendar():
    # URL for Investing.com's embeddable widget
    url = "https://sslecal2.forexprostools.com/?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&features=datepicker,timezone&countries=25,32,6,37,72,22,17,39,14,10,35,43,56,36,110,11,26,12,4,5"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            table = soup.find("table", {"id": "economicCalendarData"})
            if table:
                rows = table.find_all("tr", {"class": "js-event-item"})
                print(f"Found {len(rows)} events")
                for row in rows[:5]:
                    time = row.find("td", {"class": "time"}).text.strip()
                    currency = row.find("td", {"class": "left flagCur"}).text.strip()
                    event = row.find("td", {"class": "left event"}).text.strip()
                    print(f"{time} - {currency} - {event}")
                return True
            else:
                print("Table not found")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    get_widget_calendar()
