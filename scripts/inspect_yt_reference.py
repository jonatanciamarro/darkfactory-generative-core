import urllib.request
import re

url = "https://www.youtube.com/watch?v=E-2U8oqZr4M"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
try:
    with urllib.request.urlopen(req, timeout=12) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
    
    title_m = re.search(r"<title>(.*?)</title>", html)
    print("TITLE:", title_m.group(1) if title_m else "N/A")
    
    author_m = re.search(r'"author":"([^"]+)"', html)
    print("CHANNEL:", author_m.group(1) if author_m else "N/A")
    
    desc_m = re.search(r'"shortDescription":"([^"]+)"', html)
    print("DESCRIPTION:", desc_m.group(1)[:400] if desc_m else "N/A")
    
    keywords_m = re.search(r'"keywords":(\[[^\]]+\])', html)
    print("KEYWORDS:", keywords_m.group(1)[:300] if keywords_m else "N/A")
except Exception as e:
    print("ERROR:", e)
