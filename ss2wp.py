import argparse
import os
import re
import sys
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


def sanitize_title_prefix(title: str) -> str:
    """Return a safe prefix for image filenames based on the post title."""
    prefix = title.strip().replace(" ", "_").lower()
    prefix = re.sub(r"[^a-z0-9_]", "", prefix)[:10]
    return prefix or "image"


def sanitize_post_name(title: str) -> str:
    """Return a filesystem-friendly name based on the post title."""
    name = title.strip().replace(" ", "_")
    # Remove characters that could be problematic in file or folder names
    name = re.sub(r"[^\w-]", "", name)
    # Limit to the first 15 characters to avoid overly long paths
    name = name[:15]
    return name or "post"


def download_image(url: str, images_dir: Path, prefix: str, index: int) -> str:
    """Download an image and return its local filename."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    # Create filename using title prefix and sequential index
    ext = os.path.splitext(url.split("?")[0])[1] or ".jpg"
    filename = f"{prefix}_{index}{ext}"
    filepath = images_dir / filename
    with open(filepath, "wb") as f:
        f.write(resp.content)
    return filename


def process_images(soup: BeautifulSoup, images_dir: Path, prefix: str) -> None:
    # Determine the root BeautifulSoup object for creating new tags. When
    # ``soup`` is a Tag rather than the ``BeautifulSoup`` object itself,
    # calling ``soup.new_tag`` will fail because Tags expose ``new_tag`` as
    # ``None``. We therefore walk up the parent chain until we reach the
    # root ``BeautifulSoup`` instance which provides ``new_tag``.
    root = soup
    while hasattr(root, "parent") and root.parent is not None:
        root = root.parent

    index = 1
    for img in soup.find_all("img"):
        src = img.get("src")
        if src:
            try:
                download_image(src, images_dir, prefix, index)
            except Exception as exc:
                print(f"Failed to download {src}: {exc}", file=sys.stderr)

        index += 1

        # ``root`` is guaranteed to be the ``BeautifulSoup`` instance so we can
        # safely create new tags from it.
        placeholder = root.new_tag("p")
        placeholder.string = "[[[ IMAGE ]]]"

        parent = img.parent
        if parent.name == "p" and len(parent.contents) == 1:
            parent.replace_with(placeholder)
        else:
            img.replace_with(placeholder)


def strip_paragraph_classes(soup: BeautifulSoup) -> None:
    for p_tag in soup.find_all("p"):
        p_tag.attrs.pop("class", None)



def build_html(title: str, content: BeautifulSoup) -> str:
    html_parts = [f"<h1>{title}</h1>"]
    for element in content.find_all(["p", "ul", "ol", "pre", "blockquote"]):
        html_parts.append(str(element))
    return "\n".join(html_parts)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert Squarespace post to WordPress HTML"
    )
    parser.add_argument("url", help="URL of the Squarespace post")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    html = fetch_page(args.url)
    title, content = parse_post(html)
    post_name = sanitize_post_name(title)
    post_dir = Path.cwd() / post_name
    post_dir.mkdir(exist_ok=True)
    images_dir = ensure_images_dir(post_dir)
    prefix = sanitize_title_prefix(title)
    process_images(content, images_dir, prefix)
    strip_paragraph_classes(content)

    output_html = build_html(title, content)

    output_file = post_dir / f"{post_name}.html"
    output_file.write_text(output_html, encoding="utf-8")
    print(f"Wrote {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
