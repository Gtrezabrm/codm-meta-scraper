import os
import re
import json
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

def parse_attachments_from_text(text):
    """
    استخراج اتچمنت‌ها از متن یوتیوب با الگوی دقیق Regex
    """
    attachment_types = ["Muzzle", "Barrel", "Stock", "Laser", "Magazine", "Rear Grip", "Underbarrel", "Perk", "Optic", "Trigger"]
    found_attachments = {}
    
    for att_type in attachment_types:
        pattern = rf"{att_type}\s*[:\-]\s*([A-Za-z0-9\s\-]+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            found_attachments[att_type] = match.group(1).strip()
            
    return found_attachments

def fetch_from_youtube(weapon_name):
    """
    جستجو در یوتیوب برای پیدا کردن اتچمنت‌های مولتی‌پلییر سیزن جدید
    """
    if not YOUTUBE_API_KEY:
        return None

    query = f"CODM {weapon_name} best loadout multiplayer"
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=video&maxResults=2&key={YOUTUBE_API_KEY}"

    try:
        response = requests.get(url, timeout=8)
        if response.status_code == 200:
            data = response.json()
            for item in data.get("items", []):
                description = item["snippet"]["description"]
                title = item["snippet"]["title"]
                combined_text = f"{title}\n{description}"
                
                attachments = parse_attachments_from_text(combined_text)
                if len(attachments) >= 3:
                    return {
                        "mode": "Multiplayer",
                        "name": f"MP Meta ({weapon_name})",
                        "attachments": attachments,
                        "perks": ["Lightweight", "Quick Fix", "Dead Silence"]
                    }
    except Exception as e:
        print(f"خطا در دریافت یوتیوب برای {weapon_name}: {e}")
        
    return None

def build_weapon_database():
    weapons_list = []

    for item in TARGET_WEAPONS:
        w_name = item["name"]
        w_class = item["class"]
        w_tier = item["tier"]
        
        print(f"در حال پردازش گان: {w_name} ({w_class})...")

        # تلاش برای استخراج آنلاین از یوتیوب
        yt_loadout = fetch_from_youtube(w_name)

        # اگر آنلاین پیدا نشد، از اتچمنت متناسب با کلاس همان گان استفاده می‌شود
        if not yt_loadout:
            default_atts = CLASS_DEFAULT_LOADOUTS.get(w_class, CLASS_DEFAULT_LOADOUTS["AR"])
            yt_loadout = {
                "mode": "Multiplayer",
                "name": f"Pro MP Build",
                "attachments": default_atts,
                "perks": ["Lightweight", "Quick Fix", "Hardline"]
            }

        weapons_list.append({
            "name": w_name,
            "class": w_class,
            "tier": w_tier,
            "loadouts": [yt_loadout]
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
