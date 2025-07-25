import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

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
        title = og_title["content"][:-10].strip()
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


def find_gallery_link(soup: BeautifulSoup, base_url: str) -> str | None:
    """Return an absolute URL to the gallery page if found."""
    link = soup.find("a", href=lambda h: h and "/gallery#/" in h)
    if link and link.get("href"):
        return urljoin(base_url, link["href"])
    return None


def extract_gallery_images(html: str, gallery_url: str) -> tuple[list[str], str]:
    """Return image URLs and description text from the gallery page."""
    soup = BeautifulSoup(html, "html.parser")

    fragment = urlparse(gallery_url).fragment
    fragment = fragment.lstrip("/")
    fragment = fragment.rstrip("/")
    target = fragment

    project = None
    if target:
        for candidate in soup.find_all("div", class_="project gallery-project"):
            data_url = candidate.get("data-url", "").lstrip("/").rstrip("/")
            if data_url.endswith(target):
                project = candidate
                break

    if project is None:
        project = soup.find("div", class_="project gallery-project active-project")

    if not project:
        return [], ""

    image_list = project.find("div", class_="image-list")
    if not image_list:
        return [], ""

    desc_div = project.find("div", class_="project-description")
    description = ""
    if desc_div:
        for a in desc_div.find_all("a"):
            text = a.get_text(strip=True)
            if re.match(r"read\s*more(?:\.{3}|…)?$", text, flags=re.I):
                a.decompose()
        description = desc_div.get_text(" ", strip=True)
        description = re.sub(
            r"\s*read\s*more(?:\.{3}|…)?\s*$", "", description, flags=re.I
        )

    images: list[str] = []
    for img in image_list.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        full = urljoin(gallery_url, src)
        clean = full.split("?", 1)[0]
        images.append(clean)
    return images, description


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


def build_html(
    title: str, content: BeautifulSoup, gallery_description: str | None = None
) -> str:
    """Return minimal HTML for the post body including headings."""
    html_parts = [f"<h1>{title}</h1>"]

    allowed_tags = ["p", "ul", "ol", "pre", "blockquote"]
    # Exclude ``h1`` tags from the body to avoid duplicating the page's
    # main heading in the generated output.
    allowed_tags.extend(f"h{i}" for i in range(2, 7))

    for element in content.find_all(allowed_tags):
        html_parts.append(str(element))

    if gallery_description:
        html_parts.append("<hr>")
        html_parts.append("<h2>Gallery</h2>")
        html_parts.append(f"<p>{gallery_description}</p>")

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

    soup = BeautifulSoup(html, "html.parser")
    gallery_link = find_gallery_link(soup, args.url)
    gallery_images: list[str] = []
    gallery_description = ""
    if gallery_link:
        try:
            gallery_html = fetch_page(gallery_link)
            gallery_images, gallery_description = extract_gallery_images(
                gallery_html, gallery_link
            )
        except Exception as exc:  # pragma: no cover - network errors
            print(f"Failed to retrieve gallery page: {exc}", file=sys.stderr)

    post_name = sanitize_post_name(title)
    post_dir = Path.cwd() / post_name
    post_dir.mkdir(exist_ok=True)
    images_dir = ensure_images_dir(post_dir)
    prefix = sanitize_title_prefix(title)
    process_images(content, images_dir, prefix)
    strip_paragraph_classes(content)

    output_html = build_html(title, content, gallery_description or None)
    # Drop the first image placeholder if one exists to mimic Squarespace's
    # lead image handling.
    output_html = re.sub(r"\n?<p>\[\[\[ IMAGE \]\]\]</p>\n?", "", output_html, count=1)

    output_file = post_dir / f"{post_name}.html"
    output_file.write_text(output_html, encoding="utf-8")
    print(f"Wrote {output_file}")
    if gallery_images:
        gallery_prefix = f"gallery_{prefix}"
        for idx, url in enumerate(gallery_images, start=1):
            try:
                download_image(url, images_dir, gallery_prefix, idx)
            except Exception as exc:  # pragma: no cover - network errors
                print(f"Failed to download gallery image {url}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
