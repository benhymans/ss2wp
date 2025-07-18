import argparse
import os
import re
import sys
import uuid
from pathlib import Path

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36"
}


def fetch_page(url: str) -> str:
    """Retrieve the HTML content for the given URL."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_post(html: str) -> tuple[str, BeautifulSoup]:
    """Extract the title and article body soup from the HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Attempt to determine the title
    title = None
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    if not title:
        title_tag = soup.find(re.compile("^h[1-2]$"))
        if title_tag and title_tag.text.strip():
            title = title_tag.text.strip()
    if not title:
        title = "Untitled Post"

    # Article content
    article = soup.find("article")
    if not article:
        article = soup.find("main")
    if not article:
        # Fallback to body
        article = soup.find("body")

    return title, article


def ensure_images_dir(path: Path) -> Path:
    images_dir = path / "images"
    images_dir.mkdir(exist_ok=True)
    return images_dir


def download_image(url: str, images_dir: Path) -> str:
    """Download an image and return its local filename."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    # Generate unique filename from uuid and extension
    ext = os.path.splitext(url.split("?")[0])[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = images_dir / filename
    with open(filepath, "wb") as f:
        f.write(resp.content)
    return filename


def process_images(soup: BeautifulSoup, images_dir: Path) -> None:
    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        try:
            filename = download_image(src, images_dir)
            img["src"] = f"images/{filename}"
        except Exception as exc:
            print(f"Failed to download {src}: {exc}", file=sys.stderr)


def build_html(title: str, content: BeautifulSoup) -> str:
    html_parts = [f"<h1>{title}</h1>"]
    for element in content.find_all(["p", "img", "ul", "ol", "pre", "blockquote"]):
        html_parts.append(str(element))
    return "\n".join(html_parts)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert Squarespace post to WordPress HTML")
    parser.add_argument("url", help="URL of the Squarespace post")
    parser.add_argument("-o", "--output", help="Optional output file")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    html = fetch_page(args.url)
    title, content = parse_post(html)
    images_dir = ensure_images_dir(Path.cwd())
    process_images(content, images_dir)
    output_html = build_html(title, content)

    if args.output:
        Path(args.output).write_text(output_html, encoding="utf-8")
    else:
        print(output_html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
