import xml.etree.ElementTree as ET

import requests


def get_myfxbook_xml():
    url = "https://www.myfxbook.com/calendar_xml.xml"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            print("Successfully accessed MyFXBook")
            try:
                root = ET.fromstring(response.content)
                events = root.findall("event")
                print(f"Found {len(events)} events")
                for event in events[:5]:
                    print("-" * 20)
                    print(f"Time: {event.find('time').text}")
                    print(f"Currency: {event.find('currency').text}")
                    print(f"Event: {event.find('name').text}")
            except Exception as parse_error:
                print(f"Parse Error: {parse_error}")
                print("Content might not be XML")
                print(response.content[:200])
            return True
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    get_myfxbook_xml()
