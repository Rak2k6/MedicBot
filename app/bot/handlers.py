import logging
import sys
import os
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes
import json

# Add the app directory to sys.path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from processing.pdf_extract import extract_pdf_text

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "Welcome to the Lab Report Explanation Bot!\n\n"
        "Send me a PDF lab report, and I'll provide educational explanations of the results.\n\n"
        "⚠️ **Important:** This is for educational purposes only and not medical advice. "
        "Please consult a qualified doctor for interpretation."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = """
Available commands:
/start - Start the bot
/help - Show this help message

To use the bot:
1. Send a PDF file containing your lab report
2. The bot will extract the data and provide educational explanations

⚠️ **Disclaimer:** This bot provides educational information only. It does not diagnose, treat, or provide medical advice. Always consult healthcare professionals.
"""
    await update.message.reply_text(help_text)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document uploads (PDFs)."""
    document = update.message.document

    if not document:
        await update.message.reply_text("Please send a document.")
        return

    # Check if it's a PDF
    if document.mime_type != 'application/pdf':
        await update.message.reply_text("Please send a PDF file only.")
        return

    # Download the file
    file = await context.bot.get_file(document.file_id)
    file_path = f"temp_{document.file_name}"

    try:
        await file.download_to_drive(file_path)
        logger.info(f"Downloaded file: {file_path}")

        # Extract text and return as JSON
        extracted_data = extract_pdf_text(file_path)
        
        if extracted_data:
            # Check if we have any useful data
            has_content = (
                extracted_data.get('extracted_text', '').strip() or
                extracted_data.get('lab_tests')
            )

            if has_content:
                # Format as JSON string for response
                json_response = json.dumps(extracted_data, indent=2)
                
                if len(json_response) > 4000:
                    # Too long for text message, send as file
                    result_filename = f"extracted_{document.file_name or 'data'}.json"
                    
                    try:
                        with open(result_filename, 'w', encoding='utf-8') as f:
                            f.write(json_response)
                            
                        await update.message.reply_text(
                            f"Extraction successful!\n"
                            f"Found {len(extracted_data.get('lab_tests', {}))} lab tests.\n"
                            f"The data is too large for a text message, so I've attached it as a file."
                        )
                        
                        with open(result_filename, 'rb') as f:
                            await update.message.reply_document(
                                document=f,
                                filename=result_filename,
                                caption="Full Extracted Data"
                            )
                    except Exception as e:
                         logger.error(f"Error sending extraction result file: {e}")
                         await update.message.reply_text("Error sending the result file.")
                    finally:
                         if os.path.exists(result_filename):
                            os.remove(result_filename)
                else:
                    await update.message.reply_text(f"Extracted data:\n\n```json\n{json_response}\n```")
            else:
                await update.message.reply_text("PDF processed but no extractable content found. The file may be empty, corrupted, or in an unsupported format.")
        else:
            await update.message.reply_text("Could not extract data from the PDF. Please ensure it's a valid file.")

    except Exception as e:
        logger.error(f"Error processing document: {e}")
        await update.message.reply_text("Sorry, there was an error processing your file.")

    finally:
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages."""
    await update.message.reply_text(
        "Please send a PDF lab report for analysis. Use /help for more information."
    )

def setup_handlers(application):
    """Set up all handlers for the bot."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Handlers set up successfully")
