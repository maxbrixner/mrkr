# Mrkr

A lighweight labeling solution for text in images.

## Requirements

```bash
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-eng
sudo apt-get install tesseract-ocr-deu
...
```

## Command Line Interface

You can use the CLI to set up MRKR.

Before you start, enable logging by

```bash
export LOGGING_CONFIG=logging.dev
```

Create the database tables by

```bash
python -m mrkr create-tables
```
