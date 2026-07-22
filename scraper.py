import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

DATA_DIR = Path(__file__).parent / "data"
USERNAME = "silence"
API_URL = "https://api.uouin.com/app/cloudflare"


def session() -> requests.Session:
    s = requests.Session()
    s.mount("https://", HTTPAdapter(max_retries=Retry(
        total=3, backoff_factor=0.5, status_forcelist=(500, 502, 503, 504)
    )))
    return s


def fetch_telecom_ips(s: requests.Session) -> list[dict]:
    key = os.environ["UOUIN_KEY"]
    resp = s.get(
        API_URL,
        params={"username": USERNAME, "key": key, "nodeid": "ctcc"},
        timeout=10,
    )
    resp.raise_for_status()
    payload = resp.json()

    if payload.get("code") != "200":
        sys.exit(f"API返回异常: {payload.get('msg')}")

    info = payload["data"]["ctcc"]["info"]
    records = []
    for item in info:
        ping = float(item["ping"].replace("ms", ""))
        records.append({
            "ip": item["ip"],
            "loss": item["loss"],
            "ping_ms": ping,
            "speed": item["speed"],
            "bandwidth": item["bandwidth"],
        })
    return records


def main() -> None:
    records = fetch_telecom_ips(session())
    if not records:
        sys.exit("未抓取到电信线路数据")

    ranked = sorted(records, key=lambda r: r["ping_ms"])

    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "telecom_ips.json").write_text(
        json.dumps({
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "count": len(ranked),
            "records": ranked,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (DATA_DIR / "telecom_ips.txt").write_text(
        "\n".join(r["ip"] for r in ranked) + "\n", encoding="utf-8"
    )
    print(f"共 {len(ranked)} 条，最优延迟 {ranked[0]['ping_ms']}ms")


if __name__ == "__main__":
    main()
