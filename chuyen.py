import json, os

SRC = "acc.json"
DST = "ac.json"

def convert():
    if not os.path.exists(SRC):
        print(f"[!] Không tìm thấy {SRC}")
        return

    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)

    new_data = {}
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            uid = str(item.get("uid", "")).strip()
            pwd = str(item.get("password", "")).strip()
            if uid and pwd:
                new_data[uid] = pwd
    elif isinstance(data, dict):
        for uid, pwd in data.items():
            new_data[str(uid)] = str(pwd)

    with open(DST, "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=4, ensure_ascii=False)

    print(f"[✓] Convert {len(data)} acc → {len(new_data)} acc dict")
    print(f"[✓] Ghi vào {DST}")

if __name__ == "__main__":
    convert()