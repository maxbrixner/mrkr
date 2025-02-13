# Mrkr

A lighweight labeling solution for text in images.

## Requirements

Mrkr uses Google's Tesseract as one of its OCR providers. As an example, you can install Tesseract on Debian-like systems as follows:

```bash
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-eng
sudo apt-get install tesseract-ocr-deu
...
```

Install the requirements using pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Command Line Interface

You can use the CLI to set up MRKR.

Before you start, enable logging:

```bash
export LOGGING_CONFIG=logging.dev
```

Then, create the database tables:

```bash
python -m mrkr create-tables
```

You can also drop the tables (i.e. delete all data):

```bash
python -m mrkr drop-tables
```

Create a demo user and a demo project:

```bash
python -m mrkr insert-demo
```

The demo user's email is ``spongebob@bb.com``, his password is ``krabby``.

## Deploy using Posit Connect

First, install rsconnect:

```bash
source .venv/bin/activate
pip install rsconnect
```

Then, create a manifest (if it does not exist):

```bash
rsconnect write-manifest fastapi --entrypoint mrkr:app .
```