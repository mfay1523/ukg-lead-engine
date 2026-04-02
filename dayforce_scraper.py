name: Dayforce Lead Bot

on:
  schedule:
    - cron: "10 11 * * *"
  workflow_dispatch:

jobs:
  run-bot:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Show repo files (debug)
        run: ls -la

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests beautifulsoup4

      - name: Run Dayforce bot
        env:
          EMAIL_ADDRESS: ${{ secrets.EMAIL_ADDRESS }}
          EMAIL_APP_PASSWORD: ${{ secrets.EMAIL_APP_PASSWORD }}
        run: |
          python dayforce_scraper.py
