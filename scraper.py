import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
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


def fetch_telecom_ips(s: requests.Session) -> dict[str, float]:
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
    records = fetch_telecom_ips(session())
    if not records:
        sys.exit("未抓取到电信线路数据")

    ranked = sorted(records.items(), key=lambda x: x[1])

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
