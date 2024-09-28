import requests
def fetch_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        print(response.text)
    else:
        print(f"Failed to fetch data: {response.status_code}")

# 假设这是从用户输入接收到的 URL
url = "http://example.com/api/data?param=malicious_payload"

fetch_data(url)

# print(solution())