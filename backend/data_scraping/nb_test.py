import requests
import json
import re

# The initial download endpoint URL
url = "https://api-brabant.iprox-open.nl/api/v1/public/download/9696a222-e0da-4b77-bc95-104c6f3ccce9"
# Headers to mimic the browser request
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "origin": "https://open.brabant.nl",
    "referer": "https://open.brabant.nl/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
}
# The payload data that was sent in the original request
payload = {
    "nodeIds": [
        "9dda30c1-21c8-42e9-aa43-ab28a6529323",
        "04a73a5f-12f6-41d9-bf71-4bacb02f9ff0",
        "f5a6129c-0f5a-4144-9ba3-da8ee212e656",
        "77152ec8-bc20-4c4c-ab42-1d5fc422eaab",
    ]
}


def download_file():
    # Make the POST request with the required headers and payload
    response = requests.post(url, headers=headers, json=payload)
    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        zip_id = data.get("zipId")
        if zip_id:
            print(f"zipId: {zip_id}")  # Debugging: Print the zipId
            # Construct the URL to download the file using the zipId
            file_url = (
                f"https://api-brabant.iprox-open.nl/api/v1/public/download-zip/{zip_id}"
            )
            print(
                f"Constructed file URL: {file_url}"
            )  # Debugging: Print the constructed URL
            file_response = requests.get(file_url)
            if file_response.status_code == 200:
                # Determine filename from Content-Disposition header if available
                filename = "downloaded_file.zip"  # Default filename
                if "Content-Disposition" in file_response.headers:
                    content_disposition = file_response.headers["Content-Disposition"]
                    filename_match = re.search(r'filename="(.+)"', content_disposition)
                    if filename_match:
                        filename = filename_match.group(1)
                # Save the file
                with open(filename, "wb") as file:
                    file.write(file_response.content)
                print(f"File downloaded successfully as {filename}")
                return True
            else:
                print(f"Error downloading file: {file_response.status_code}")
                print(file_response.text)
                return False
        else:
            print("zipId not found in the response")
            return False
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return False


if __name__ == "__main__":
    download_file()
