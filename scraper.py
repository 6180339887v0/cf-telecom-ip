import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

DATA_DIR = Path(__file__).parent / "data"
IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
DIGIT_RE = re.compile(r"[^\d.]")


def session() -> requests.Session:
    s = requests.Session()
    s.mount("https://", HTTPAdapter(max_retries=Retry(
        total=3, backoff_factor=0.5, status_forcelist=(500, 502, 503, 504)
    )))
    return s


def from_wetest(s: requests.Session) -> dict[str, float]:
    resp = s.get("https://www.wetest.vip/page/cloudflare/address_v4.html", timeout=10)
    resp.raise_for_status()
    table = BeautifulSoup(resp.text, "lxml").find("table")
    result = {}
    for tr in table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) < 7 or cells[0] != "电信" or not IP_RE.match(cells[1]):
            continue
        rtt = DIGIT_RE.sub("", cells[4])
        if rtt:
            result[cells[1]] = float(rtt)
    return result


def from_uouin(s: requests.Session) -> dict[str, float]:
    resp = s.get("https://bestcf.pages.dev/uouin/all.txt", timeout=10)
    resp.raise_for_status()
    result = {}
    for line in resp.text.strip().splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 5 or parts[1] != "电信":
            continue
        ip = parts[0].split(":")[0]
        rtt = DIGIT_RE.sub("", parts[3])
        if IP_RE.match(ip) and rtt:
            result[ip] = float(rtt)
    return result


def main() -> None:
    s = session()
    merged: dict[str, float] = {}

    for fetch in (from_wetest, from_uouin):
        try:
            for ip, rtt in fetch(s).items():
                if ip not in merged or rtt < merged[ip]:
                    merged[ip] = rtt
        except Exception as e:
            print(f"{fetch.__name__} 失败: {e}", file=sys.stderr)

    if not merged:
        sys.exit("两个数据源均抓取失败")

    ranked = sorted(merged.items(), key=lambda x: x[1])

    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "telecom_ips.json").write_text(
        json.dumps({
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "count": len(ranked),
            "records": [{"ip": ip, "rtt_ms": rtt} for ip, rtt in ranked],
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (DATA_DIR / "telecom_ips.txt").write_text(
        "\n".join(ip for ip, _ in ranked) + "\n", encoding="utf-8"
    )
    print(f"共 {len(ranked)} 条，最优延迟 {ranked[0][1]}ms")


if __name__ == "__main__":
    main()
