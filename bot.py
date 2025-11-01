import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from topup_automation import topup_handler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Get bot token from environment variable
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("Please set TELEGRAM_BOT_TOKEN environment variable")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_text = """
🤖 *Free Fire Diamond Top-Up Bot*

*Available Commands:*
/tp - Top up diamonds using UniPin voucher

*Usage:*
/tp
(Your UID)
(Amount)
(Serial Code) 
(PIN)

*Example:*
/tp
123456789
115
BDMB1S00001234
1234-5678-9012-3456

*Supported Amounts:* 25, 50, 115, 240, 610, 1240, 2530

⚠️ *Note:* Make sure your voucher code starts with BDMB or UPBD
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def tp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tp command for diamond top-up"""
    try:
        # Check if we have the correct number of arguments
        if not context.args and not update.message.reply_to_message:
            await update.message.reply_text(
                "Please provide top-up details in this format:\n\n"
                "/tp\n"
                "(UID)\n"
                "(Amount)\n" 
                "(Serial Code)\n"
                "(PIN)\n\n"
                "Example:\n"
                "/tp\n"
                "123456789\n"
                "115\n"
                "BDMB1S00001234\n"
                "1234-5678-9012-3456"
            )
            return

        # Get the message text
        if update.message.reply_to_message:
            # If it's a reply, get the replied message text
            message_text = update.message.reply_to_message.text
        else:
            # Otherwise, get the current message text
            message_text = update.message.text

        # Parse the input
        lines = message_text.strip().split('\n')
        
        # Remove command line and get parameters
        if lines[0].startswith('/tp'):
            lines = lines[1:]
        
        # Clean empty lines
        lines = [line.strip() for line in lines if line.strip()]
        
        if len(lines) < 4:
            await update.message.reply_text("❌ Insufficient parameters. Need UID, Amount, Serial Code, and PIN.")
            return
        
        uid = lines[0]
        amount = lines[1]
        serial_code = lines[2]
        pin = lines[3]
        
        # Send processing message
        processing_msg = await update.message.reply_text("🔄 Processing your top-up request...")
        
        # Validate inputs
        is_valid, validation_msg = await topup_handler.validate_inputs(uid, amount, serial_code, pin)
        if not is_valid:
            await processing_msg.edit_text(f"❌ Validation Error: {validation_msg}")
            return
        
        # Perform top-up
        result = await topup_handler.perform_topup(uid, amount, serial_code, pin)
        
        # Send result
        if result['success']:
            await processing_msg.edit_text(result['message'])
        else:
            await processing_msg.edit_text(result['message'])
            
    except Exception as e:
        logging.error(f"Error in tp_command: {str(e)}")
        await update.message.reply_text(f"❌ Error processing request: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages"""
    text = update.message.text
    
    if text.startswith('/'):
        await update.message.reply_text("Unknown command. Use /start to see available commands.")
else:
        # If someone sends the parameters without command
        if len(text.split('\n')) >= 4:
            await update.message.reply_text("Please use /tp command followed by your details.")
        else:
            await update.message.reply_text("Use /start to see how to top up diamonds.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logging.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        await update.message.reply_text("❌ An error occurred. Please try again later.")

async def telegram_bot():
    """Main function to run the Telegram bot"""
    try:
        # Create application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("tp", tp_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        # Start the bot
        logging.info("Starting Telegram bot...")
        await application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logging.error(f"Bot error: {str(e)}")

if name == 'main':
    asyncio.run(telegram_bot())      
