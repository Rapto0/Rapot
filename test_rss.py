import xml.etree.ElementTree as ET

import requests


def get_investing_rss():
    url = "https://tr.investing.com/rss/calendar_Economic.rss"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            root = ET.fromstring(response.content)
            # Channel is usually the first child
            channel = root.find("channel")
            if channel:
                print(f"Feed Title: {channel.find('title').text}")
                items = channel.findall("item")
                print(f"Found {len(items)} items")
                for item in items[:5]:
                    print("-" * 20)
                    print(f"Title: {item.find('title').text}")
                    print(f"PubDate: {item.find('pubDate').text}")
            return True
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    get_investing_rss()
