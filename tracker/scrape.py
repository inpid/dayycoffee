#!/usr/bin/env python3
"""생두 업체 상품 페이지를 수집해 신규/품절/재입고/가격변동을 기록하고 알림을 보낸다.

사용: python scrape.py [--sources sources.json] [--no-notify]
알림 환경변수: TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID, 또는 DISCORD_WEBHOOK_URL
"""
import argparse, json, os, re, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
DATA = ROOT / "data"
KST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (compatible; GreenBeanTracker/1.0)"

PRESETS = {
    "cafe24": {
        "item": "ul.prdList > li",
        "name": ".name a",
        "price": ".price",
        "link": ".name a",
        "image": "img",
        "soldout": ".icon_soldout, img[alt*='품절']",
    },
}
ORIGINS = ["에티오피아", "콜롬비아", "케냐", "브라질", "과테말라", "코스타리카", "파나마", "르완다",
           "부룬디", "탄자니아", "예멘", "인도네시아", "온두라스", "엘살바도르", "니카라과", "페루",
           "멕시코", "볼리비아", "인도", "베트남", "파푸아뉴기니", "우간다", "자메이카", "하와이", "에콰도르"]


def now():
    return datetime.now(KST).isoformat(timespec="seconds")


def fetch(url):
    if not url.startswith("http"):
        return (ROOT / url).read_text(encoding="utf-8")
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding if r.encoding in (None, "ISO-8859-1") else r.encoding
    return r.text


def parse_price(text):
    digits = re.sub(r"[^\d]", "", text or "")
    return int(digits) if digits else None


def guess_origin(name):
    return next((o for o in ORIGINS if o in name), "")


def parse_page(html, src):
    sel = {**PRESETS.get(src.get("preset"), {}), **src.get("selectors", {})}
    soup = BeautifulSoup(html, "html.parser")
    base = src.get("base_url") or src["url"]
    out = []
    for el in soup.select(sel["item"]):
        a = el.select_one(sel["link"])
        n = el.select_one(sel["name"])
        if not (a and n) or not a.get("href"):
            continue
        name = " ".join(n.get_text(" ", strip=True).split())
        p = el.select_one(sel["price"])
        img = el.select_one(sel["image"])
        so = bool(sel.get("soldout") and el.select_one(sel["soldout"])) or "품절" in el.get_text()
        out.append({
            "name": name,
            "url": urljoin(base, a["href"]),
            "price": parse_price(p.get_text() if p else ""),
            "image": urljoin(base, img["src"]) if img and img.get("src") else "",
            "soldout": so,
            "origin": guess_origin(name),
        })
    return out


def scrape_source(src):
    pages = src.get("max_pages", 1) if src.get("page_param") else 1
    items, seen = [], set()
    for page in range(1, pages + 1):
        url = src["url"]
        if src.get("page_param"):
            url += ("&" if "?" in url else "?") + f"{src['page_param']}={page}"
        found = [i for i in parse_page(fetch(url), src) if i["url"] not in seen]
        if not found:
            break
        seen.update(i["url"] for i in found)
        items += found
    return items


def diff(src, scraped, beans, ts, baseline):
    """beans(dict)를 갱신하고 이벤트 리스트를 반환."""
    events, cur = [], set()

    def ev(kind, key, b, **kw):
        events.append({"time": ts, "type": kind, "source": src["id"], "source_name": src["name"],
                       "name": b["name"], "url": b["url"], "price": b["price"], **kw})

    for it in scraped:
        key = f"{src['id']}|{it['url']}"
        cur.add(key)
        b = beans.get(key)
        if b is None:
            beans[key] = {**it, "source": src["id"], "source_name": src["name"], "first_seen": ts,
                          "last_seen": ts, "baseline": baseline, "status": "soldout" if it["soldout"] else "on_sale",
                          "price_history": [[ts, it["price"]]]}
            if not baseline:
                ev("new", key, it)
            continue
        if b["status"] == "removed" or (b["status"] == "soldout" and not it["soldout"]):
            if not baseline:
                ev("restock", key, it)
        elif b["status"] == "on_sale" and it["soldout"]:
            ev("soldout", key, it)
        if it["price"] and b["price"] and it["price"] != b["price"]:
            ev("price_change", key, it, old_price=b["price"])
            b["price_history"].append([ts, it["price"]])
        b.update({k: it[k] for k in ("name", "image", "price", "origin")})
        b.update(last_seen=ts, status="soldout" if it["soldout"] else "on_sale")

    for key, b in beans.items():
        if b["source"] == src["id"] and key not in cur and b["status"] != "removed":
            b["status"] = "removed"
            ev("removed", key, b)
    return events


LABEL = {"new": "🆕 신규", "restock": "🔄 재입고", "soldout": "⛔ 품절", "price_change": "💰 가격변동", "removed": "🗑 판매종료"}


def format_message(events):
    lines = ["☕ 생두 업데이트"]
    for e in events:
        if e["type"] == "removed":
            continue
        price = f"{e['price']:,}원" if e["price"] else "가격미정"
        if e["type"] == "price_change":
            price = f"{e['old_price']:,}→{e['price']:,}원"
        lines.append(f"{LABEL[e['type']]} [{e['source_name']}] {e['name']} · {price}\n{e['url']}")
    return "\n".join(lines) if len(lines) > 1 else None


def notify(events):
    msg = format_message(events)
    if not msg:
        return
    msg = msg[:3900]
    tok, chat, hook = (os.environ.get(k) for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "DISCORD_WEBHOOK_URL"))
    try:
        if tok and chat:
            requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                          data={"chat_id": chat, "text": msg, "disable_web_page_preview": True}, timeout=20)
        if hook:
            requests.post(hook, json={"content": msg}, timeout=20)
    except requests.RequestException as e:
        print("알림 전송 실패:", e, file=sys.stderr)
    if not (tok and chat) and not hook:
        print("(알림 설정 없음 — 아래 내용이 발송될 예정)\n" + msg)


def build_html(beans, events, status):
    """데이터를 내장한 단일 파일 greenbean.html 생성 (서버 없이 더블클릭으로 열림)."""
    tpl = (ROOT / "web" / "template.html").read_text("utf-8")
    blob = json.dumps({"beans": beans, "events": events, "status": status}, ensure_ascii=False).replace("</", "<\\/")
    head, rest = tpl.split("/*DATA*/", 1)
    (ROOT / "greenbean.html").write_text(head + blob + rest.split("/*END*/", 1)[1], "utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default=str(ROOT / "sources.json"))
    ap.add_argument("--no-notify", action="store_true")
    args = ap.parse_args()

    DATA.mkdir(exist_ok=True)
    load = lambda f, d: json.loads((DATA / f).read_text("utf-8")) if (DATA / f).exists() else d
    beans, events_log, status = load("beans.json", {}), load("events.json", []), {}
    sources = [s for s in json.loads(Path(args.sources).read_text("utf-8"))["sources"] if s.get("enabled")]
    ts, new_events = now(), []

    for src in sources:
        baseline = not any(b["source"] == src["id"] for b in beans.values())
        try:
            scraped = scrape_source(src)
            if not scraped:
                raise RuntimeError("상품을 하나도 찾지 못함 (선택자 확인 필요)")
            new_events += diff(src, scraped, beans, ts, baseline)
            status[src["id"]] = {"name": src["name"], "ok": True, "count": len(scraped), "time": ts}
            print(f"[{src['id']}] {len(scraped)}개 수집{' (최초 기준선)' if baseline else ''}")
        except Exception as e:  # 한 업체 실패가 전체를 막지 않게
            status[src["id"]] = {"name": src["name"], "ok": False, "error": str(e), "time": ts}
            print(f"[{src['id']}] 실패: {e}", file=sys.stderr)

    events_log = (new_events + events_log)[:500]
    out = {"updated": ts}
    (DATA / "beans.json").write_text(json.dumps(beans, ensure_ascii=False, indent=1), "utf-8")
    (DATA / "events.json").write_text(json.dumps(events_log, ensure_ascii=False, indent=1), "utf-8")
    (DATA / "status.json").write_text(json.dumps({**out, "sources": status}, ensure_ascii=False, indent=1), "utf-8")
    build_html(beans, events_log, {**out, "sources": status})
    print(f"이벤트 {len(new_events)}건")
    if new_events and not args.no_notify:
        notify(new_events)


if __name__ == "__main__":
    main()
