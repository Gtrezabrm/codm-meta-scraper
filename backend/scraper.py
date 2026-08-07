import os
import re
import json
import time
import requests
from datetime import datetime

# کلید API یوتیوب (از تنظیمات Secrets گیت‌هاب خوانده می‌شود)
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# لیست جامع تمام گان‌های اصلی و محبوب کالاف دیوتی موبایل
TARGET_WEAPONS = [
    # --- Assault Rifles (AR) ---
    {"name": "BP50", "class": "AR", "tier": "S"},
    {"name": "DR-H", "class": "AR", "tier": "S"},
    {"name": "Type 19", "class": "AR", "tier": "S"},
    {"name": "AK117", "class": "AR", "tier": "A"},
    {"name": "Grau 5.56", "class": "AR", "tier": "A"},
    {"name": "M13", "class": "AR", "tier": "A"},
    {"name": "LK24", "class": "AR", "tier": "A"},
    {"name": "Oden", "class": "AR", "tier": "B"},
    {"name": "KN-44", "class": "AR", "tier": "B"},
    {"name": "EM2", "class": "AR", "tier": "B"},

    # --- SMGs ---
    {"name": "Fennec", "class": "SMG", "tier": "S"},
    {"name": "Switchblade X9", "class": "SMG", "tier": "S"},
    {"name": "CBR4", "class": "SMG", "tier": "A"},
    {"name": "CX-9", "class": "SMG", "tier": "A"},
    {"name": "TEC-9", "class": "SMG", "tier": "A"},
    {"name": "PP19 Bizon", "class": "SMG", "tier": "A"},
    {"name": "QQ9", "class": "SMG", "tier": "B"},
    {"name": "RUS-79U", "class": "SMG", "tier": "B"},

    # --- LMGs ---
    {"name": "MG42", "class": "LMG", "tier": "S"},
    {"name": "Holger 26", "class": "LMG", "tier": "A"},
    {"name": "UL736", "class": "LMG", "tier": "A"},
    {"name": "Chopper", "class": "LMG", "tier": "B"},
    {"name": "RPD", "class": "LMG", "tier": "B"},

    # --- Snipers ---
    {"name": "LW3-Tundra", "class": "Sniper", "tier": "S"},
    {"name": "DL Q33", "class": "Sniper", "tier": "S"},
    {"name": "Locus", "class": "Sniper", "tier": "A"},
    {"name": "Koshka", "class": "Sniper", "tier": "A"},
    {"name": "HDR", "class": "Sniper", "tier": "B"},
    {"name": "XPR-50", "class": "Sniper", "tier": "B"},

    # --- Marksman ---
    {"name": "SKS", "class": "Marksman", "tier": "S"},
    {"name": "Kilo Bolt-Action", "class": "Marksman", "tier": "B"},

    # --- Shotguns ---
    {"name": "R9-0", "class": "Shotgun", "tier": "S"},
    {"name": "KRM-262", "class": "Shotgun", "tier": "A"},
    {"name": "BY15", "class": "Shotgun", "tier": "A"},
    {"name": "JAK-12", "class": "Shotgun", "tier": "B"},

    # --- Pistols / Secondaries ---
    {"name": "L-CAR 9", "class": "Pistol", "tier": "S"},
    {"name": "Dobvra", "class": "Pistol", "tier": "A"},
    {"name": ".50 GS", "class": "Pistol", "tier": "A"}
]

# لوداوت‌های هوشمند پیش‌فرض بر اساس کلاس گان (در صورت عدم دریافت از یوتیوب)
CLASS_DEFAULT_LOADOUTS = {
    "AR": {
        "Muzzle": "Tactical Suppressor",
        "Barrel": "OWC Ranger",
        "Stock": "No Stock",
        "Laser": "OWC Laser - Tactical",
        "Magazine": "50 Round Extended Mag"
    },
    "SMG": {
        "Muzzle": "Monolithic Suppressor",
        "Barrel": "MIP Extended Light Barrel",
        "Stock": "No Stock",
        "Laser": "OWC Laser - Tactical",
        "Magazine": "Extended Mag A"
    },
    "LMG": {
        "Muzzle": "Recoil Booster",
        "Barrel": "Heavy Barrel",
        "Stock": "Steady Stock",
        "Laser": "Aim Assist Laser",
        "Magazine": "Large Magazine"
    },
    "Sniper": {
        "Muzzle": "Tactical Suppressor",
        "Barrel": "MIP Light Barrel",
        "Stock": "Combat Stock",
        "Rear Grip": "Stippled Grip Tape",
        "Magazine": "Fast Reload Mag"
    },
    "Marksman": {
        "Muzzle": "Monolithic Suppressor",
        "Barrel": "Light Barrel",
        "Stock": "No Stock",
        "Underbarrel": "Tactical Foregrip",
        "Optic": "3x Tactical Scope"
    },
    "Shotgun": {
        "Muzzle": "Choke",
        "Barrel": "Extended Barrel",
        "Laser": "MIP Laser 5mW",
        "Underbarrel": "Merc Foregrip",
        "Rear Grip": "Granulated Grip Tape"
    },
    "Pistol": {
        "Muzzle": "Agency Suppressor",
        "Barrel": "Extended Barrel",
        "Trigger": "Lightweight Trigger",
        "Laser": "5mW Laser",
        "Magazine": "Extended Mag"
    }
}

# پرک‌های پیش‌فرض به تفکیک مود بازی
DEFAULT_PERKS = {
    "Multiplayer": ["Lightweight", "Quick Fix", "Hardline"],
    "Battle Royale": ["Framework", "Alertness", "Awareness"],
}

ATTACHMENT_TYPES = [
    "Muzzle", "Barrel", "Stock", "Laser", "Magazine",
    "Rear Grip", "Underbarrel", "Perk", "Optic", "Trigger"
]

# کد اشتراک‌گذاری چیدمان در CODM معمولاً یک رشته‌ی ۹ کاراکتری
# حروف بزرگ/اعداد است (مثل 8K3F92LQ1) که یوتیوبرها با کلماتی مثل
# "Code:", "Share code:", "Loadout code:" قبلش می‌نویسند.
SHARE_CODE_PATTERN = re.compile(
    r"(?:share\s*code|loadout\s*code|code)\s*[:\-]?\s*([A-Z0-9]{6,10})",
    re.IGNORECASE
)


def parse_attachments_from_text(text):
    """
    استخراج اتچمنت‌ها از متن یوتیوب با الگوی دقیق Regex.
    توجه: چون \\s شامل \\n هم می‌شود، اگر مقدار را بدون محدود کردن
    به همان خط بگیریم، ممکن است چند خط بعدی هم به اشتباه داخل مقدار
    قرار بگیرد. برای همین این‌جا فقط تا انتهای همان خط جستجو می‌کنیم.
    """
    found_attachments = {}

    for att_type in ATTACHMENT_TYPES:
        # [^\n\r]+ به‌جای \s+ -> فقط همان خط را می‌گیرد، نه کل متن بعدی را
        pattern = rf"{att_type}\s*[:\-]\s*([^\n\r,]+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # بریدن مقادیر غیرمنطقی طولانی (احتمالاً Regex اشتباه گرفته)
            if 1 <= len(value) <= 40:
                found_attachments[att_type] = value

    return found_attachments


def parse_share_code_from_text(text):
    """
    استخراج کد اشتراک‌گذاری چیدمان از توضیحات/عنوان ویدیو.
    اگر پیدا نشود، رشته‌ی خالی برمی‌گرداند (نه None) تا فراخوان
    مجبور به بررسی None نباشد.
    """
    match = SHARE_CODE_PATTERN.search(text)
    if match:
        return match.group(1).upper()
    return ""


def search_youtube(query):
    """یک درخواست جستجوی یوتیوب می‌زند و آیتم‌های خام را برمی‌گرداند."""
    if not YOUTUBE_API_KEY:
        return []

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": 2,
        "key": YOUTUBE_API_KEY,
    }

    try:
        response = requests.get(url, params=params, timeout=8)
        if response.status_code == 200:
            return response.json().get("items", [])
        else:
            # مهم: کد ۴۰۳ معمولاً یعنی quota روزانه‌ی یوتیوب تمام شده
            print(f"یوتیوب استتوس {response.status_code} برگرداند: {response.text[:200]}")
    except requests.RequestException as e:
        print(f"خطای شبکه در درخواست یوتیوب: {e}")

    return []


def fetch_loadout_for_mode(weapon_name, mode_label, search_phrase):
    """
    جستجو در یوتیوب برای پیدا کردن بهترین چیدمان یک گان برای یک مود
    مشخص (Multiplayer یا Battle Royale). اگر چیزی قابل‌قبول پیدا نشد،
    None برمی‌گرداند تا فراخوان از مقدار پیش‌فرض کلاس استفاده کند.
    """
    query = f"CODM {weapon_name} {search_phrase}"
    items = search_youtube(query)

    for item in items:
        description = item["snippet"].get("description", "")
        title = item["snippet"].get("title", "")
        combined_text = f"{title}\n{description}"

        attachments = parse_attachments_from_text(combined_text)
        share_code = parse_share_code_from_text(combined_text)

        if len(attachments) >= 3:
            return {
                "mode": mode_label,
                "name": f"{mode_label} Meta ({weapon_name})",
                "attachments": attachments,
                "perks": DEFAULT_PERKS.get(mode_label, []),
                "code": share_code,  # ممکن است خالی باشد اگر پیدا نشد
            }

    return None


def build_default_loadout(weapon_class, mode_label):
    """چیدمان پیش‌فرض بر اساس کلاس گان، برای زمانی که یوتیوب چیزی نداد."""
    default_atts = CLASS_DEFAULT_LOADOUTS.get(weapon_class, CLASS_DEFAULT_LOADOUTS["AR"])
    return {
        "mode": mode_label,
        "name": f"Pro {mode_label} Build",
        "attachments": default_atts,
        "perks": DEFAULT_PERKS.get(mode_label, []),
        "code": "",  # چیدمان پیش‌فرض کد اشتراک‌گذاری واقعی ندارد
    }


def build_weapon_database():
    weapons_list = []

    # هر مود یک عبارت جستجوی جدا دارد تا یوتیوب نتایج مرتبط‌تری بدهد
    modes = [
        ("Multiplayer", "best loadout multiplayer"),
        ("Battle Royale", "best loadout battle royale BR"),
    ]

    for item in TARGET_WEAPONS:
        w_name = item["name"]
        w_class = item["class"]
        w_tier = item["tier"]

        print(f"در حال پردازش گان: {w_name} ({w_class})...")

        loadouts = []
        for mode_label, search_phrase in modes:
            loadout = fetch_loadout_for_mode(w_name, mode_label, search_phrase)
            if not loadout:
                loadout = build_default_loadout(w_class, mode_label)
            loadouts.append(loadout)

            # فاصله‌ی کوچک بین درخواست‌ها برای احترام به Rate Limit یوتیوب.
            # هر جستجو ۱۰۰ واحد از quota روزانه (۱۰,۰۰۰ واحدی) مصرف می‌کند؛
            # با ۳۸ گان × ۲ مود = ۷۶ درخواست در روز، به سقف نزدیک می‌شویم.
            time.sleep(0.5)

        weapons_list.append({
            "name": w_name,
            "class": w_class,
            "tier": w_tier,
            "loadouts": loadouts,
        })

    return {
        "weapons": weapons_list,
        "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    }


def main():
    print("=== شروع استخراج اطلاعات تمام گان‌ها ===")
    data = build_weapon_database()

    output_path = os.path.join(os.path.dirname(__file__), 'weapons_data.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"موفقیت‌آمیز بود! دیتابیس با {len(data['weapons'])} گان ذخیره شد.")


if __name__ == "__main__":
    main()
