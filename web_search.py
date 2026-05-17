# web_search.py — CHAHAT Web Search & Page Fetching
# ✅ Searches the web via HTTP requests (no Chrome, no API key needed)
# ✅ Fetches full page content and extracts readable text
# ✅ Fast, reliable, no CAPTCHA issues

import re
import time
import urllib.parse


def search_web(query: str, max_results: int = 5) -> str:
    """
    Search the web and return top results.
    Uses DuckDuckGo HTML (no library needed, just plain HTTP requests).
    Returns formatted search results with titles, snippets, and URLs.
    """
    try:
        import requests
        from bs4 import BeautifulSoup

        print(f"🌐 Searching web: '{query}'")

        # DuckDuckGo HTML search (no CAPTCHA, no blocking)
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        data = {"q": query, "b": ""}
        resp = requests.post(url, headers=headers, data=data, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        # Extract search results (skip ads)
        for result_div in soup.find_all("div", class_="result"):
            # Skip ads
            result_classes = result_div.get("class", [])
            if "result--ad" in result_classes:
                continue
            if len(results) >= max_results:
                break
            try:
                # Title and URL
                title_tag = result_div.find("a", class_="result__a")
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)

                # Extract real URL from DuckDuckGo redirect
                raw_url = title_tag.get("href", "")
                if "uddg=" in raw_url:
                    real_url = urllib.parse.unquote(
                        raw_url.split("uddg=")[1].split("&")[0]
                    )
                else:
                    real_url = raw_url

                # Snippet
                snippet_tag = result_div.find("a", class_="result__snippet")
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                if title:
                    results.append({
                        "title": title,
                        "snippet": snippet,
                        "url": real_url
                    })
            except Exception:
                continue

        if not results:
            return f"🔍 '{query}' ke liye koi result nahi mila. Try different keywords."

        # Format output
        output = f"🌐 **Web Search Results for: \"{query}\"**\n\n"
        for i, r in enumerate(results, 1):
            output += f"**{i}. {r['title']}**\n"
            if r["snippet"]:
                output += f"   {r['snippet']}\n"
            if r["url"]:
                output += f"   🔗 {r['url']}\n"
            output += "\n"

        output += (
            "---\n"
            "💡 Agar kisi page ka detail chahiye toh fetch_page tool use karo."
        )

        print(f"   ✅ Found {len(results)} results")
        return output

    except ImportError:
        return (
            "❌ requests or beautifulsoup4 not installed. "
            "Run: pip install requests beautifulsoup4"
        )
    except Exception as e:
        return f"❌ Web search failed: {e}"


def fetch_page(url: str, max_chars: int = 6000) -> str:
    """
    Fetch a web page and extract its readable text content.
    Uses requests + BeautifulSoup — fast and reliable.
    """
    try:
        import requests
        from bs4 import BeautifulSoup

        print(f"📄 Fetching page: {url[:80]}")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove noise elements
        for tag in soup(["script", "style", "nav", "footer", "header",
                         "aside", "form", "button", "iframe", "noscript",
                         "svg", "img", "video", "audio"]):
            tag.decompose()

        # Try to find the main content area first
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", {"role": "main"})
            or soup.find("div", class_=re.compile(r"content|article|post|entry", re.I))
            or soup.body
            or soup
        )

        # Extract text with some structure
        lines = []
        for element in main_content.find_all(
            ["h1", "h2", "h3", "h4", "p", "li", "pre", "code", "td", "th", "blockquote"]
        ):
            text = element.get_text(separator=" ", strip=True)
            if not text or len(text) < 3:
                continue

            tag_name = element.name
            if tag_name in ("h1", "h2", "h3", "h4"):
                prefix = "#" * int(tag_name[1])
                lines.append(f"\n{prefix} {text}\n")
            elif tag_name == "li":
                lines.append(f"  • {text}")
            elif tag_name in ("pre", "code"):
                lines.append(f"```\n{text}\n```")
            elif tag_name == "blockquote":
                lines.append(f"> {text}")
            else:
                lines.append(text)

        content = "\n".join(lines).strip()

        # Truncate if too long
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n... [content truncated — page bahut lamba tha]"

        if not content:
            # Fallback: just get all text
            content = main_content.get_text(separator="\n", strip=True)[:max_chars]

        page_title = soup.title.string.strip() if soup.title and soup.title.string else "Unknown"

        output = f"📄 **Page: {page_title}**\n"
        output += f"🔗 {url}\n\n"
        output += content

        print(f"   ✅ Extracted {len(content)} chars from page")
        return output

    except ImportError:
        return (
            "❌ requests or beautifulsoup4 not installed. "
            "Run: pip install requests beautifulsoup4"
        )
    except Exception as e:
        return f"❌ Page fetch failed: {e}"


def cleanup_driver():
    """No-op — kept for backward compatibility (no Selenium driver used)."""
    pass


# ── Quick test ────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Testing Web Search ===")
    result = search_web("Python Polars library tutorial", max_results=3)
    print(result)
    print("\n=== Testing Page Fetch ===")
    result2 = fetch_page("https://docs.python.org/3/tutorial/index.html", max_chars=500)
    print(result2)
