# Telegram Lab Report Explanation Bot

A production-ready Telegram bot for educational explanations of lab reports using AI, with strict medical safety constraints.

## Features

- Accepts PDF lab reports
- Extracts lab data and returns as JSON
- Educational explanations (AI integration coming)
- Strict safety guardrails (no medical advice)
- Admin configuration panel (coming)

## Setup

1. **Get API Keys:**
   - Create a Telegram bot and get token from [BotFather](https://t.me/botfather)
   - Get Google Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

2. **Environment Variables:**
   - Add to `credential.env`:
     ```
     TELEGRAM_BOT_TOKEN=your_telegram_token_here
     GEMINI_API_KEY=your_gemini_api_key_here
     ```

3. **Install Dependencies:**
   ```
   pip install -r requirements.txt
   ```

4. **Run the Bot:**
   ```
   python app/main.py
   ```

## Current Status

- ✅ Telegram bot skeleton with polling
- ✅ PDF text extraction (returns JSON)
- ✅ Basic message handling
- 🔄 AI integration (in progress)
- 🔄 Admin panel (planned)

## Safety Features

- **No Diagnosis:** Never provides medical diagnoses
- **No Treatments:** Never suggests treatments or medications
- **Educational Only:** Explains lab values in neutral terms
- **Mandatory Disclaimer:** Every response includes safety disclaimer
- **Input Validation:** Rejects non-PDF files and invalid reports

## Usage

1. Start the bot with `/start`
2. Send a PDF lab report
3. Receive extracted data as JSON
4. (Future) Get educational explanations

⚠️ **Important:** This bot provides educational information only. It does not diagnose, treat, or provide medical advice. Always consult healthcare professionals.
