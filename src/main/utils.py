import requests


def fetch_usd_xmr():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=monero&vs_currencies=usd"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if "monero" in data and "usd" in data["monero"]:
            return data["monero"]["usd"]
        else:
            raise Exception("Price data not available")
    else:
        raise Exception("Failed to fetch data")


if __name__ == "__main__":
    xmr_price = get_xmr_price()
    print("Current XMR Price:", xmr_price)
