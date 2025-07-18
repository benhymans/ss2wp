# ss2wp

ss2wp is a Python script that helps migrate blog posts from Squarespace to WordPress. It retrieves a Squarespace article, extracts the title, text content and images, and produces HTML that can be pasted directly into the WordPress editor. All images are downloaded locally with unique names to make uploading them to WordPress easier.

## Features

- **Extract title and article text** from a given Squarespace blog post URL
- **Generate clean HTML** that preserves basic formatting and is ready to paste into WordPress
- **Download post images** into a local directory with unique filenames

## Usage

The script will be invoked from the command line and requires Python 3. Run it with the target post URL:

```bash
python ss2wp.py <squarespace-post-url>
```

The downloaded images will be saved in an `images` folder in the current directory. The resulting HTML will be printed to standard output for easy copying, or optionally written to a file.

## Status

This repository currently contains the project description. Implementation of the script will come next.

