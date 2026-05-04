from flask import Flask, render_template, request, jsonify, Response
import requests
from datetime import datetime

app = Flask(__name__)


class KSOImageFetcher:
    """
    Fetches images from Kodaikanal Solar Observatory
    URL Format: https://kso.iiap.res.in/new/static/images/rawimg/{FILTER}/{YEAR}/{MONTH}/{FILTER}_{YYYYMMDD}T{HHMMSS}_Q{QUALITY}L{LEVEL}a128px.jpg
    """

    BASE_URL = "https://kso.iiap.res.in/new/static/images/rawimg"

    # Filter mapping
    FILTER_MAP = {"whitelight": "WL", "cak": "CAK", "halpha": "HA"}

    # Common times throughout the day (IST - Indian Standard Time)
    TIME_SLOTS = [
        "054500",
        "060000",
        "061500",
        "063000",
        "064500",
        "070000",
        "071500",
        "073000",
        "074500",
        "080000",
        "081500",
        "083000",
        "084500",
        "090000",
        "091500",
        "093000",
        "094500",
        "100000",
        "101500",
        "103000",
        "104500",
        "110000",
        "111500",
        "113000",
        "114500",
        "120000",
        "121500",
        "123000",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

    def construct_image_url(self, date, filter_code, time, quality="1", level="0"):
        """
        Construct image URL based on KSO format
        Example: https://kso.iiap.res.in/new/static/images/rawimg/WL/2011/08/WL_20110802T091500_Q1L0a128px.jpg
        """
        year = date.strftime("%Y")
        month = date.strftime("%m")
        date_str = date.strftime("%Y%m%d")

        filename = f"{filter_code}_{date_str}T{time}_Q{quality}L{level}a128px.jpg"
        url = f"{self.BASE_URL}/{filter_code}/{year}/{month}/{filename}"

        return url, filename

    def check_image_exists(self, url):
        """Check if image URL is accessible"""
        try:
            response = self.session.head(url, timeout=5)
            return response.status_code == 200
        except:
            # If HEAD fails, try GET with small timeout
            try:
                response = self.session.get(url, timeout=5, stream=True)
                return response.status_code == 200
            except:
                return False

    def get_images_for_date(self, date_str, filter_type, level="0"):
        """
        Get all available images for a specific date and filter
        """
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return []

        filter_code = self.FILTER_MAP.get(filter_type, "WL")
        images = []

        print(f"Searching for {filter_type} images on {date_str}")

        # Try all common time slots
        for time_slot in self.TIME_SLOTS:
            url, filename = self.construct_image_url(
                date, filter_code, time_slot, quality="1", level=level
            )

            if self.check_image_exists(url):
                print(f"Found: {url}")
                images.append(
                    {
                        "url": url,
                        "filename": filename,
                        "time": f"{time_slot[:2]}:{time_slot[2:4]}:{time_slot[4:]} IST",
                        "proxy_url": f"/proxy?url={url}",
                    }
                )

        # Also try quality 2 and 3 for first few time slots
        for time_slot in self.TIME_SLOTS[:5]:
            for quality in ["2", "3"]:
                url, filename = self.construct_image_url(
                    date, filter_code, time_slot, quality=quality, level=level
                )

                if self.check_image_exists(url):
                    print(f"Found (Q{quality}): {url}")
                    images.append(
                        {
                            "url": url,
                            "filename": filename,
                            "time": f"{time_slot[:2]}:{time_slot[2:4]}:{time_slot[4:]} IST (Quality {quality})",
                            "proxy_url": f"/proxy?url={url}",
                        }
                    )

        print(f"Total found: {len(images)} images for {filter_type}")
        return images

    def download_image(self, url):
        """Download image from KSO"""
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            print(f"Error downloading: {e}")
        return None


fetcher = KSOImageFetcher()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    """Search for solar images"""
    data = request.get_json()
    date = data.get("date")
    level = data.get("level", "0")
    filters = data.get("filters", ["whitelight", "cak", "halpha"])

    if not date:
        return jsonify({"error": "Date is required"}), 400

    results = {"date": date, "images": {}}

    # Fetch images for each filter
    for filter_type in filters:
        images = fetcher.get_images_for_date(date, filter_type, level)
        results["images"][filter_type] = images

    return jsonify(results)


@app.route("/proxy")
def proxy_image():
    """Proxy images from KSO to avoid CORS issues"""
    url = request.args.get("url")

    if not url or not url.startswith("https://kso.iiap.res.in"):
        return "Invalid URL", 400

    image_data = fetcher.download_image(url)

    if image_data:
        return Response(image_data, mimetype="image/jpeg")

    return "Image not found", 404


@app.route("/download")
def download_image():
    """Download image with filename"""
    url = request.args.get("url")
    filename = request.args.get("filename", "solar_image.jpg")

    if not url or not url.startswith("https://kso.iiap.res.in"):
        return "Invalid URL", 400

    image_data = fetcher.download_image(url)

    if image_data:
        return Response(
            image_data,
            mimetype="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    return "Image not found", 404


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
