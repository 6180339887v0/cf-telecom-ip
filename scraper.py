import re
import sys
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

URL = "https://bestcf.pages.dev/uouin/all.txt"
CARRIER = "电信"
DATA_DIR = Path(__file__).parent / "data"


def session() -> requests.Session:
    s = requests.Session()
    s.mount("https://", HTTPAdapter(max_retries=Retry(
        total=3, backoff_factor=0.5, status_forcelist=(500, 502, 503, 504)
    )))
    return s


def fetch_telecom_ips(s: requests.Session) -> list[str]:
    resp = s.get(URL, timeout=10)
    resp.raise_for_status()
    ips = []
    for line in resp.text.strip().splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 5 or parts[1] != CARRIER:
            continue
        ip = parts[0].split(":")[0]
        if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip):
            ips.append(ip)
    return ips


def main() -> None:
    ips = fetch_telecom_ips(session())
    if not ips:
        sys.exit("未抓取到电信线路数据")

    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "telecom_ips.txt").write_text(
        "\n".join(ips) + "\n", encoding="utf-8"
    )
    print(f"共 {len(ips)} 条")


if __name__ == "__main__":
    main()
