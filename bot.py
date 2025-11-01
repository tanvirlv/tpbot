import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from playwright.sync_api import sync_playwright
import time

# Conversation states
UID, AMOUNT, SERIAL, PIN = range(4)

class FreeFireTopUpBot:
    def __init__(self):
        self.telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.base_url = "https://shop.garena.my"
        
        # Configure logging
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        self.logger = logging.getLogger(__name__)
        
        # Diamond amount mapping
        self.diamond_packages = {
            '25': '25 Diamond',
            '50': '50 Diamond', 
            '115': '115 Diamond',
            '240': '240 Diamond',
            '500': '500 Diamond',
            '610': '610 Diamond',
            '1240': '1240 Diamond',
            '2530': '2530 Diamond'
        }

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message when command /start is issued."""
        welcome_text = """
🎮 *Welcome to Free Fire Top-Up Bot!* 🎮

*Use the following format to top up diamonds:*
/tp

*Then follow the steps:*
1️⃣ Enter your UID
2️⃣ Enter diamond amount
3️⃣ Enter serial code  
4️⃣ Enter PIN

*Example:*
UID: `1234567890`
Amount: `500`
Serial: `BDMB1S00001234`
PIN: `1234-5678-9012-3456`

⚠️ *Make sure your UID and codes are correct!*
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
        return ConversationHandler.END

    async def topup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the top-up conversation."""
        await update.message.reply_text(
            "🚀 *Starting Top-Up Process* 🚀\n\n"
            "Please enter your *Free Fire UID*:",
            parse_mode='Markdown'
        )
        return UID

    async def get_uid(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Store UID and ask for amount."""
        uid = update.message.text.strip()
        
        # Validate UID
        if not uid.isdigit() or len(uid) < 6:
            await update.message.reply_text(
                "❌ *Invalid UID!* Please enter a valid numeric UID (at least 6 digits):",
                parse_mode='Markdown'
            )
            return UID
        
        context.user_data['uid'] = uid
        
        # Show available amounts
        amounts_text = "\n".join([f"• {amount} diamonds" for amount in self.diamond_packages.keys()])
        await update.message.reply_text(
            f"✅ *UID Accepted:* `{uid}`\n\n"
            f"*Please enter diamond amount:*\n{amounts_text}\n\n"
            f"*Example:* `500`",
            parse_mode='Markdown'
        )
        return AMOUNT

    async def get_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Store amount and ask for serial."""
        amount = update.message.text.strip()
        
        # Validate amount
        if amount not in self.diamond_packages:
            await update.message.reply_text(
                "❌ *Invalid amount!* Please choose from available amounts:",
                parse_mode='Markdown'
            )
            return AMOUNT
        
        context.user_data['amount'] = amount
        
        await update.message.reply_text(
            f"✅ *Amount Selected:* `{amount} diamonds`\n\n"
            "Please enter your *Serial Code*:\n"
            "*Format:* `BDMB1S00001234` or `UPBD1S00001234`",
            parse_mode='Markdown'
        )
        return SERIAL

    async def get_serial(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Store serial and ask for PIN."""
        serial = update.message.text.strip().upper()
        
        # Validate serial format
        if not (serial.startswith('BDMB') or serial.startswith('UPBD')):
            await update.message.reply_text(
                "❌ *Invalid Serial!* Must start with *BDMB* or *UPBD*\n"
                "Please enter correct serial code:",
                parse_mode='Markdown'
            )
            return SERIAL
        
        context.user_data['serial'] = serial
        
        await update.message.reply_text(
            f"✅ *Serial Code Accepted:* `{serial}`\n\n"
            "Please enter your *PIN*:\n"
            "*Format:* `XXXX-XXXX-XXXX-XXXX`\n"
            "*Example:* `1234-5678-9012-3456`",
            parse_mode='Markdown'
        )
        return PIN

    async def get_pin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Store PIN and process top-up."""
        pin = update.message.text.strip()
        
        # Validate PIN format
        pin_clean = pin.replace('-', '')
        if not pin_clean.isdigit() or len(pin_clean) != 16:
            await update.message.reply_text(
                "❌ *Invalid PIN format!* Must be 16 digits\n"
                "Please enter PIN in format: `XXXX-XXXX-XXXX-XXXX`",
                parse_mode='Markdown'
            )
            return PIN
        
        context.user_data['pin'] = pin
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            "🔄 *Processing your top-up request...*\n"
            "This may take 1-2 minutes. Please wait...",
            parse_mode='Markdown'
        )
        
        # Process top-up (this runs in a separate thread to avoid blocking)
        result = await self.run_top_up_sync(
            context.user_data['uid'],
            context.user_data['amount'],
            context.user_data['serial'],
            context.user_data['pin']
        )
        
        # Send result
        await processing_msg.edit_text(result, parse_mode='Markdown')
        
        # Clear user data
        context.user_data.clear()
        
        return ConversationHandler.END

    async def run_top_up_sync(self, uid: str, amount: str, serial: str, pin: str) -> str:
        """Run the sync top-up function in executor to avoid blocking"""
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.process_top_up, uid, amount, serial, pin)
        return result

    def process_top_up(self, uid: str, amount: str, serial: str, pin: str) -> str:
        """
        Main function to process Free Fire top-up using Playwright
        """
        try:
            with sync_playwright() as p:
                # Launch browser in headless mode
                browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled']
                )
                
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                )
                
                page = context.new_page()
                
                self.logger.info("Starting top-up process...")
                
                # Step 1: Navigate to Garena Shop
                try:
                    page.goto(f"{self.base_url}/?channel=202953", timeout=60000)
                    page.wait_for_load_state('networkidle')
                    self.logger.info("Loaded Garena shop")
                except Exception as e:
                    return f"❌ *Failed to load Garena shop:* `{str(e)}`"

                # Step 2: Select Free Fire game
                try:
                    # Try multiple selectors for Free Fire game
                    selectors = [
                        "img[alt*='Free Fire']",
                        "img[alt*='FREE FIRE']", 
                        "img[src*='free-fire']",
                        "div[class*='free-fire']",
                        "//img[contains(@alt, 'Free Fire')]",
                        "//div[contains(text(), 'Free Fire')]"
                    ]
                    
                    free_fire_found = False
                    for selector in selectors:
                        try:
                            if selector.startswith('//'):
                                element = page.wait_for_selector(f"xpath={selector}", timeout=5000)
                            else:
                                element = page.wait_for_selector(selector, timeout=5000)
                            element.click()
                            free_fire_found = True
                            self.logger.info("Selected Free Fire game")
                            break
                        except:
                            continue
                    
                    if not free_fire_found:
                        return "❌ *Could not find Free Fire game selection*"
                    
                    time.sleep(3)
                except Exception as e:
                    return f"❌ *Failed to select Free Fire game:* `{str(e)}`"

                # Step 3: Login with Player ID
                try:
                    # Try multiple selectors for UID input
                    uid_selectors = [
                        "input[placeholder*='player ID']",
                        "input[placeholder*='Player ID']",
                        "input[type='text']",
                        "input[name*='id']",
                        "//input[contains(@placeholder, 'player')]"
                    ]
                    
                    uid_input_found = False
                    for selector in uid_selectors:
                        try:
                            if selector.startswith('//'):
                                element = page.wait_for_selector(f"xpath={selector}", timeout=5000)
                            else:
                                element = page.wait_for_selector(selector, timeout=5000)
                            element.fill(uid)
                            uid_input_found = True
                            break
                        except:
                            continue
                    
                    if not uid_input_found:
                        return "❌ *Could not find UID input field*"
                    
                    # Find and click login button
                    login_selectors = [
                        "button:has-text('Login')",
                        "button[type='submit']",
                        "//button[contains(text(), 'Login')]"
                    ]
                    
                    login_found = False
                    for selector in login_selectors:
                        try:
                            if selector.startswith('//'):
                                element = page.wait_for_selector(f"xpath={selector}", timeout=5000)
                            else:
                                element = page.wait_for_selector(selector, timeout=5000)
                            element.click()
                            login_found = True
                            break
                        except:
                            continue
                    
                    if not login_found:
                        return "❌ *Could not find login button*"
                    
                    self.logger.info(f"Logged in with UID: {uid}")
                    time.sleep(3)
                except Exception as e:
                    return f"❌ *Failed to login with UID:* `{str(e)}`"

                # Step 4: Select UniPin payment method
                try:
                    unipin_selectors = [
                        "div:has-text('UniPin Credits & Voucher')",
                        "//div[contains(text(), 'UniPin')]",
                        "div[class*='unipin']"
                    ]
                    
                    unipin_found = False
                    for selector in unipin_selectors:
                        try:
                            if selector.startswith('//'):
                                element = page.wait_for_selector(f"xpath={selector}", timeout=5000)
                            else:
                                element = page.wait_for_selector(selector, timeout=5000)
                            element.click()
                            unipin_found = True
                            break
                        except:
                            continue
                    
                    if not unipin_found:
                        return "❌ *Could not find UniPin payment option*"
                    
                    # Click proceed to payment
                    proceed_selectors = [
                        "button:has-text('Proceed to Payment')",
                        "//button[contains(text(), 'Proceed')]"
                    ]
                    
                    proceed_found = False
                    for selector in proceed_selectors:
                        try:
                            if selector.startswith('//'):
                                element = page.wait_for_selector(f"xpath={selector}", timeout=5000)
                            else:
                                element = page.wait_for_selector(selector, timeout=5000)
                            element.click()
                            proceed_found = True
                            break
                        except:
                            continue
                    
                    if not proceed_found:
                        return "❌ *Could not find proceed button*"
                    
                    self.logger.info("Selected UniPin payment method")
                    time.sleep(3)
                except Exception as e:
                    return f"❌ *Failed to select UniPin payment:* `{str(e)}`"

                # Step 5: Select diamond amount
                try:
                    diamond_amount = self.diamond_packages.get(amount)
                    if not diamond_amount:
                        return f"❌ *Invalid amount:* `{amount}`"
                    
                    diamond_selectors = [
                        f"button:has-text('{diamond_amount}')",
                        f"//button[contains(text(), '{diamond_amount}')]",
                        f"div:has-text('{diamond_amount}')"
                    ]
                    
                    diamond_found = False
                    for selector in diamond_selectors:
                        try:
                            if selector.startswith('//'):
                                element = page.wait_for_selector(f"xpath={selector}", timeout=5000)
                            else:
                                element = page.wait_for_selector(selector, timeout=5000)
                            element.click()
                            diamond_found = True
                            break
                        except:
                            continue
                    
                    if not diamond_found:
                        return f"❌ *Could not find diamond amount:* `{diamond_amount}`"
                    
                    self.logger.info(f"Selected diamond amount: {diamond_amount}")
                    time.sleep(3)
                except Exception as e:
                    return f"❌ *Failed to select diamond amount {amount}:* `{str(e)}`"

                # Step 6: Select voucher type based on serial prefix
                try:
                    page.wait_for_selector("text=Select Payment Channel", timeout=15000)
                    
                    # Click Physical Vouchers dropdown
                    physical_selectors = [
                        "div:has-text('Physical Vouchers')",
                        "//div[contains(text(), 'Physical Vouchers')]"
                    ]
                    
                    for selector in physical_selectors:
                        try:
                            if selector.startswith('//'):
                                element = page.wait_for_selector(f"xpath={selector}", timeout=5000)
                            else:
                                element = page.wait_for_selector(selector, timeout=5000)
                            element.click()
                            break
                        except:
                            continue
                    
                    time.sleep(2)
                    
                    # Select voucher type based on serial prefix
                    if serial.startswith('BDMB'):
                        voucher_selectors = [
                            "div:has-text('UniPin')",
                            "//div[contains(text(), 'UniPin')]"
                        ]
                    elif serial.startswith('UPBD'):
                        voucher_selectors = [
                            "div:has-text('UP Gift Card')", 
                            "//div[contains(text(), 'UP Gift Card')]"
                        ]
                    else:
                        return "❌ *Invalid serial code format.* Must start with BDMB or UPBD"
                    
                    voucher_found = False
                    for selector in voucher_selectors:
                        try:
                            if selector.startswith('//'):
                                element = page.wait_for_selector(f"xpath={selector}", timeout=5000)
                            else:
                                element = page.wait_for_selector(selector, timeout=5000)
                            element.click()
                            voucher_found = True
                            break
                        except:
                            continue
                    
                    if not voucher_found:
                        return "❌ *Could not find voucher type*"
                    
                    self.logger.info(f"Selected voucher type for serial: {serial}")
                    time.sleep(3)
                except Exception as e:
                    return f"❌ *Failed to select voucher type:* `{str(e)}`"

                # Step 7: Enter voucher details
                try:
                    # Wait for voucher input form and fill serial
                    serial_selectors = [
                        "input[placeholder*='Serial']",
                        "input[placeholder*='serial']",
                        "input[name*='serial']"
                    ]
                    
                    serial_found = False
                    for selector in serial_selectors:
                        try:
                            if selector.startswith('//'):
                                element = page.wait_for_selector(f"xpath={selector}", timeout=5000)
                            else:
                                element = page.wait_for_selector(selector, timeout=5000)
                            element.fill(serial)
                            serial_found = True
                            break
                        except:
                            continue
                    
                    if not serial_found:
                        return "❌ *Could not find serial input field*"
                    
                    # Fill PIN (remove dashes)
                    pin_clean = pin.replace('-', '')
                    pin_selectors = [
                        "input[placeholder*='PIN']",
                        "input[placeholder*='pin']", 
                        "input[name*='pin']",
                        "input[type='password']"
                    ]
                    
                    pin_found = False
                    for selector in pin_selectors:
                        try:
                            if selector.startswith('//'):
                                element = page.wait_for_selector(f"xpath={selector}", timeout=5000)
                            else:
                                element = page.wait_for_selector(selector, timeout=5000)
                            element.fill(pin_clean)
                            pin_found = True
                            break
                        except:
                            continue
                    
                    if not pin_found:
                        return "❌ *Could not find PIN input field*"
                    
                    # Click confirm button
                    confirm_selectors = [
                        "button:has-text('CONFIRM')",
                        "//button[contains(text(), 'CONFIRM')]",
                        "button[type='submit']"
                    ]
                    
                    confirm_found = False
                    for selector in confirm_selectors:
                        try:
                            if selector.startswith('//'):
                                element = page.wait_for_selector(f"xpath={selector}", timeout=5000)
                            else:
                                element = page.wait_for_selector(selector, timeout=5000)
                            element.click()
                            confirm_found = True
                            break
                        except:
                            continue
                    
                    if not confirm_found:
                        return "❌ *Could not find confirm button*"
                    
                    self.logger.info("Submitted voucher details")
                    time.sleep(5)
                except Exception as e:
                    return f"❌ *Failed to submit voucher details:* `{str(e)}`"

                # Step 8: Check transaction result
                try:
                    # Check for various success/error indicators
                    success_indicators = [
                        "text=Transaction successful",
                        "text=Payment Completed",
                        "text=successful",
                        "text=Success"
                    ]
                    
                    error_indicators = [
                        "text=Consumed Voucher",
                        "text=Invalid",
                        "text=Error",
                        "text=Failed"
                    ]
                    
                    # Check for success
                    success_found = False
                    for indicator in success_indicators:
                        if page.query_selector(indicator):
                            success_found = True
                            break
                    
                    # Check for errors
                    error_found = False
                    error_message = ""
                    for indicator in error_indicators:
                        element = page.query_selector(indicator)
                        if element:
                            error_found = True
                            error_message = element.inner_text()
                            break
                    
                    if success_found:
                        result = f"""
✅ *TOP-UP SUCCESSFUL!*

🎮 *Game:* Free Fire
👤 *UID:* `{uid}`
💎 *Amount:* {diamond_amount}
📦 *Serial:* `{serial}`

💰 *Transaction completed successfully!*
Your diamonds should be credited to your account shortly.
                        """
                        self.logger.info("Top-up successful")
                        return result
                    
                    elif error_found:
                        return f"❌ *Transaction failed:* `{error_message}`"
                    
                    else:
                        # Try to get any message text from the page
                        body_text = page.inner_text("body")
                        if "success" in body_text.lower():
                            result = f"""
✅ *TOP-UP LIKELY SUCCESSFUL!*

🎮 *Game:* Free Fire  
👤 *UID:* `{uid}`
💎 *Amount:* {diamond_amount}

*Please check your Free Fire account to confirm diamond receipt.*
                            """
                            return result
                        else:
                            return "❌ *Transaction status unclear.* Please try again or contact support."
                        
                except Exception as e:
                    return f"❌ *Error checking transaction status:* `{str(e)}`"

                finally:
                    browser.close()
                    
        except Exception as e:
            self.logger.error(f"Top-up process failed: {e}")
            return f"❌ *Top-up process failed:* `{str(e)}`"

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel the conversation."""
        await update.message.reply_text(
            "❌ *Top-up cancelled.*\nUse /tp to start again.",
            parse_mode='Markdown'
        )
        context.user_data.clear()
        return ConversationHandler.END


def run_bot():
    """Run the telegram bot with polling"""
    bot_instance = FreeFireTopUpBot()
    
    if not bot_instance.telegram_token:
        bot_instance.logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
        return
    
    # Create application
    application = Application.builder().token(bot_instance.telegram_token).build()
    
    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('tp', bot_instance.topup_command)],
        states={
            UID: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.get_uid)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.get_amount)],
            SERIAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.get_serial)],
            PIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.get_pin)],
        },
        fallbacks=[CommandHandler('cancel', bot_instance.cancel)]
    )
    
    application.add_handler(CommandHandler("start", bot_instance.start))
    application.add_handler(conv_handler)
    
    # Start polling
    bot_instance.logger.info("Starting bot polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == '__main__':
    run_bot()