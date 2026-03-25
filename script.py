import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

KST = ZoneInfo("Asia/Seoul")

ROOMS = {
    12101: [201],
    12102: [203, 207, 208],
    12103: [204, 205, 206, 209, 210, 211],
    12104: [202],
    14101: [402, 403, 423, 425],
    14102: [401],
    14103: [*range(404, 423), *range(426, 432)],
}

URL = "https://k-rsv.snu.ac.kr/NEW_SNU_BOOKING/json/getRoomList"

HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "OS_KIND": "WEB",
    "Origin": "https://k-rsv.snu.ac.kr",
    "Referer": "https://k-rsv.snu.ac.kr/NEW_SNU_BOOKING/pc/booking/roomList",
    "X-Requested-With": "XMLHttpRequest",
}

COOKIES = {
    "JSESSIONID": "A74BC16C369FFB7ADE64FA58ABE2B82E"
}

SLOTS = [f"{h:02d}:{m:02d}" for h in range(9, 23) for m in (0, 30) if (h, m) <= (22, 30)]


def day(n):
    return (datetime.now(KST) + timedelta(days=n)).strftime("%Y%m%d")


def now_str():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")


def make_query(n, sector):
    return {
        "searchDate": day(n),
        "roomNo": "0",
        "sectorNo": str(sector),
        "seatNo": "",
        "TIME_START": "",
        "TIME_END": "",
        "ABLETIME": "",
        "NAME": "",
        "sectorName": "",
        "roomName": "",
        "tab_on": "tabBooking",
        "libNo": "1",
    }


def blocked_times(abletime):
    return {x[11:16] for x in abletime.split(",") if len(x) >= 16} if abletime else set()


def fetch_day(session, n):
    now_hm = datetime.now(KST).strftime("%H:%M")
    out = {}

    for sector in ROOMS:
        r = session.post(URL, data=make_query(n, sector), timeout=15)
        r.raise_for_status()

        for d in r.json()["BookingTimeList"]:
            room = int(d["NAME"][1:])
            blocked = blocked_times(d["ABLETIME"])

            out[room] = {
                slot: ("N/A" if n == 0 and slot <= now_hm else int(slot not in blocked))
                for slot in SLOTS
            }

    df = pd.DataFrame.from_dict(out, orient="index")[SLOTS]
    df.index.name = "room"
    return df.sort_index()


def make_4day_df():
    s = requests.Session()
    s.headers.update(HEADERS)
    s.cookies.update(COOKIES)

    dfs = []
    for n in range(4):
        df = fetch_day(s, n)
        df.columns = pd.MultiIndex.from_product(
            [[day(n)], df.columns],
            names=["date", "time"]
        )
        dfs.append(df)

    return pd.concat(dfs, axis=1)


def export_4day_csv(path="rooms_4day.csv"):
    df = make_4day_df()

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(f"generated_at,{now_str()}\n\n")
        df.to_csv(f)


# usage
export_4day_csv(f"{now_str().replace(':', '-')}.csv")