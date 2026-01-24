import requests


def get_investing_calendar():
    # This is a very basic attempt to see if we can scrape investing.com without getting blocked immediately
    # Often they require headers/cookies
    url = "https://www.investing.com/economic-calendar/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Successfully accessed Investing.com")
            # Parse logic would go here
            return True
        else:
            print("Failed into access Investing.com")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    get_investing_calendar()
