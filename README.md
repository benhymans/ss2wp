# ss2wp

ss2wp is a Python script that helps migrate blog posts from Squarespace to WordPress. It retrieves a Squarespace article, extracts the title, text content and images, and produces HTML that can be pasted directly into the WordPress editor. All images are downloaded locally with unique names to make uploading them to WordPress easier.

## Features

- **Extract title and article text** from a given Squarespace blog post URL
- **Generate clean HTML** that preserves basic formatting and is ready to paste into WordPress
- **Download post images** into a local directory with unique filenames

## Usage

The script requires Python 3 and `requests` plus `beautifulsoup4` packages. Install the dependencies and run the script with the target post URL:

```bash
pip install requests beautifulsoup4
python ss2wp.py <squarespace-post-url>
```

The downloaded images will be saved in an `images` folder in the current directory. The resulting HTML will be printed to standard output for easy copying, or optionally written to a file using `-o`:

```bash
python ss2wp.py <url> -o output.html
```

## Status

The script is functional and ready to be used for simple migrations.
