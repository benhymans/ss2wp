# ss2wp

ss2wp is a Python script that helps migrate blog posts from Squarespace to WordPress. It retrieves a Squarespace article, extracts the title, text content and images, and produces HTML that can be pasted directly into the WordPress editor. All images are downloaded locally with filenames based on the post title so they are easy to upload to WordPress.

## Features

- **Extract title and article text** from a given Squarespace blog post URL
- **Generate clean HTML** that preserves basic formatting and is ready to paste into WordPress
- **Download post images** into a local directory with filenames derived from the post title
- **Replace images with placeholders** using `<p>[[[ IMAGE ]]]</p>` in the output

## Usage

The script requires Python 3. Install the dependencies and run the script with the target post URL:

```bash
pip install -r requirements.txt
python ss2wp.py <squarespace-post-url>
```

Running the script creates a new folder named after the post title (spaces are
replaced with underscores). The folder will contain the generated HTML file and
an `images` directory with all downloaded images.

## Status

The script is functional and ready to be used for simple migrations.
