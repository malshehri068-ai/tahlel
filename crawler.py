import re
from urllib.parse import urljoin, urlparse, urldefrag
import requests
from bs4 import BeautifulSoup

KEYWORDS = {
    "returns": ["return", "refund", "exchange", "استرجاع", "استبدال", "استرداد"],
    "shipping": ["shipping", "delivery", "الشحن", "التوصيل"],
    "privacy": ["privacy", "سياسة الخصوصية", "الخصوصية"],
    "complaints": ["complaint", "complaints", "شكوى", "الشكاوى"],
    "contact": ["contact", "اتصل", "تواصل", "خدمة العملاء"],
}
HEADERS = {"User-Agent": "TahlelBot/1.0 (+website analysis)"}

def normalize(url):
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")

def classify(url, title="", anchor_text=""):
    hay = f"{url} {title} {anchor_text}".lower()
    for category, words in KEYWORDS.items():
        if any(word.lower() in hay for word in words):
            return category
    return None

def link_score(url, anchor_text=""):
    score = 0
    if classify(url, anchor_text=anchor_text): score += 100
    text = f"{url} {anchor_text}".lower()
    if any(x in text for x in ["policy", "سياسة", "help", "مساعدة", "faq", "الأسئلة"]): score += 10
    return score

def crawl_site(start_url, max_pages=15, timeout=12):
    start_url = normalize(start_url)
    domain = urlparse(start_url).netloc.lower()
    queue = [(-1000, start_url)]
    seen, pages = set(), []
    special = {k: None for k in KEYWORDS}
    while queue and len(pages) < max_pages:
        queue.sort(key=lambda item: item[0], reverse=True)
        _, url = queue.pop(0)
        parsed = urlparse(url)
        if url in seen or parsed.netloc.lower() != domain: continue
        seen.add(url)
        try:
            response = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            if "text/html" not in response.headers.get("content-type", "").lower(): continue
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "noscript"]): tag.decompose()
            title = soup.title.get_text(" ", strip=True) if soup.title else ""
            text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
            final_url = response.url.rstrip("/")
            pages.append({"url": final_url, "title": title, "text": text[:20000], "status": response.status_code})
            category = classify(final_url, title)
            if category and special[category] is None: special[category] = final_url
            for anchor in soup.find_all("a", href=True):
                href = urljoin(final_url, anchor["href"])
                href, _ = urldefrag(href)
                href = href.rstrip("/")
                if not href.startswith(("http://", "https://")): continue
                if urlparse(href).netloc.lower() != domain or href in seen: continue
                queue.append((link_score(href, anchor.get_text(" ", strip=True)), href))
        except requests.RequestException:
            continue
    return {"start_url": start_url, "pages": pages, "special_pages": special}
