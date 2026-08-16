from io import BytesIO
from urllib.request import urlopen
from zipfile import ZipFile

from src.paths import RAW_XLSX, ensure_directories


DATA_URL = "https://archive.ics.uci.edu/static/public/352/online+retail.zip"


def download_dataset() -> None:
    """Download the public UCI dataset when it is not available locally."""
    ensure_directories()
    if RAW_XLSX.exists():
        return

    print("Downloading the UCI Online Retail dataset...")
    with urlopen(DATA_URL, timeout=120) as response:
        archive = ZipFile(BytesIO(response.read()))
        with archive.open("Online Retail.xlsx") as source, RAW_XLSX.open("wb") as target:
            target.write(source.read())


if __name__ == "__main__":
    download_dataset()

