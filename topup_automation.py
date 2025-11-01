import asyncio
from playwright.async_api import async_playwright
import logging
import time
from typing import Tuple, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(name)

class FreeFireTopUp:
    def init(self):
        self.base_url = "https://shop.garena.my/?channel=202953"
        self.browser = None
        self.page = None
        
    async def setup_browser(self):
        """Initialize browser with proper settings"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=VizDisplayCompositor',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding'
            ]
        )
        
        self.page = await self.browser.new_page()
        
        # Set user agent to look more human
        await self.page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        })
        
        return self.page

    async def perform_topup(self, uid: str, amount: str, serial_code: str, pin: str) -> Dict:
        """Main function to perform diamond top-up"""
        try:
            await self.setup_browser()
            
            # Step 1: Navigate to Garena Shop
            logger.info("Navigating to Garena Shop...")
            await self.page.goto(self.base_url, timeout=60000)
            await self.page.wait_for_timeout(3000)
            
            # Step 2: Select Free Fire game
            logger.info("Selecting Free Fire game...")
            free_fire_selector = "img[src*='freefire']"
            await self.page.wait_for_selector(free_fire_selector, timeout=30000)
            await self.page.click(free_fire_selector)
            await self.page.wait_for_timeout(2000)
            
            # Step 3: Login with Player ID
            logger.info(f"Logging in with UID: {uid}")
            uid_input_selector = "input[placeholder*='enter player ID']"
            await self.page.wait_for_selector(uid_input_selector, timeout=30000)
            await self.page.fill(uid_input_selector, uid)
            
            login_button_selector = "button:has-text('Login')"
            await self.page.click(login_button_selector)
            await self.page.wait_for_timeout(3000)
            
            # Step 4: Proceed to UniPin payment
            logger.info("Selecting UniPin payment method...")
            unipin_selector = "div:has-text('UniPin Credits & Voucher')"
            await self.page.wait_for_selector(unipin_selector, timeout=30000)
            await self.page.click(unipin_selector)
            
            proceed_button_selector = "button:has-text('Proceed to Payment')"
            await self.page.wait_for_selector(proceed_button_selector, timeout=30000)
            await self.page.click(proceed_button_selector)
            await self.page.wait_for_timeout(5000)
            
            # Wait for page to load completely
            await self.page.wait_for_load_state('networkidle')
            
            # Step 5: Select diamond amount
            logger.info(f"Selecting diamond amount: {amount}")
            amount_mapping = {
                "25": "25 Diamond",
                "50": "50 Diamond", 
                "115": "115 Diamond",
                "240": "240 Diamond",
                "610": "610 Diamond",
                "1240": "1,240 Diamond",
                "2530": "2,530 Diamond"
}
            
            diamond_text = amount_mapping.get(amount, f"{amount} Diamond")
            diamond_selector = f"div:has-text('{diamond_text}')"
            
            try:
                await self.page.wait_for_selector(diamond_selector, timeout=30000)
                await self.page.click(diamond_selector)
                await self.page.wait_for_timeout(2000)
            except Exception as e:
                logger.warning(f"Could not find exact amount {diamond_text}, trying alternative selection")
                # Alternative selection method
                all_options = await self.page.query_selector_all('div[class*="denom"], div[class*="amount"]')
                for option in all_options:
                    text = await option.text_content()
                    if amount in text:
                        await option.click()
                        break
            
            # Step 6: Wait for payment channel selection
            await self.page.wait_for_timeout(3000)
            
            # Step 7: Select voucher type based on serial code prefix
            logger.info("Selecting voucher type...")
            serial_prefix = serial_code[:4].upper()
            
            if serial_prefix == "BDMB":
                voucher_type = "UniPin Voucher"
            elif serial_prefix == "UPBD":
                voucher_type = "UP Gift Card"
            else:
                return {"success": False, "message": "❌ Invalid serial code format. Must start with BDMB or UPBD"}
            
            # Look for voucher selection
            voucher_selector = f"div:has-text('{voucher_type}')"
            try:
                await self.page.wait_for_selector(voucher_selector, timeout=30000)
                await self.page.click(voucher_selector)
                await self.page.wait_for_timeout(2000)
            except:
                # Try dropdown approach
                dropdown_selector = "div[class*='dropdown'], select, div[role='button']"
                dropdowns = await self.page.query_selector_all(dropdown_selector)
                if dropdowns:
                    await dropdowns[0].click()
                    await self.page.wait_for_timeout(1000)
                    await self.page.click(voucher_selector)
            
            # Step 8: Enter voucher details
            logger.info("Entering voucher details...")
            
            # Enter serial number
            serial_input_selector = "input[placeholder*='Serial'], input[name*='serial'], input[type='text']:first-of-type"
            await self.page.wait_for_selector(serial_input_selector, timeout=30000)
            await self.page.fill(serial_input_selector, serial_code)
            await self.page.wait_for_timeout(1000)
            
            # Enter PIN (handle the formatted input)
            pin_input_selector = "input[placeholder*='PIN'], input[name*='pin'], input[type='password']"
            pin_inputs = await self.page.query_selector_all(pin_input_selector)
            
            if len(pin_inputs) == 1:
                # Single input field
                await pin_inputs[0].fill(pin.replace('-', ''))
            else:
                # Multiple input fields (formatted)
                pin_digits = pin.replace('-', '')
                for i in range(min(16, len(pin_digits))):
                    if i < len(pin_inputs):
                        await pin_inputs[i].fill(pin_digits[i])
            
            await self.page.wait_for_timeout(2000)
            
            # Step 9: Confirm transaction
            logger.info("Confirming transaction...")
            confirm_selector = "button:has-text('CONFIRM'), button:has-text('Confirm')"
            await self.page.wait_for_selector(confirm_selector, timeout=30000)
await self.page.click(confirm_selector)
            
            # Step 10: Wait for transaction result
            logger.info("Waiting for transaction result...")
            await self.page.wait_for_timeout(10000)
            
            # Check for success or error
            success_indicators = [
                "Transaction successful",
                "Payment Completed",
                "Success",
                "Berjaya"
            ]
            
            error_indicators = [
                "Consumed Voucher",
                "Invalid",
                "Error",
                "Failed"
            ]
            
            page_content = await self.page.content()
            
            for indicator in success_indicators:
                if indicator.lower() in page_content.lower():
                    # Capture transaction details if available
                    transaction_id = "N/A"
                    try:
                        # Look for transaction ID in the page
                        transaction_elements = await self.page.query_selector_all('div, span')
                        for element in transaction_elements:
                            text = await element.text_content()
                            if 'transaction' in text.lower() and len(text) > 10:
                                transaction_id = text
                                break
                    except:
                        pass
                    
                    return {
                        "success": True, 
                        "message": f"✅ Top-Up Successful!\n\nUID: {uid}\nAmount: {amount} Diamonds\nTransaction: {transaction_id}",
                        "transaction_id": transaction_id
                    }
            
            for indicator in error_indicators:
                if indicator.lower() in page_content.lower():
                    return {
                        "success": False, 
                        "message": f"❌ Transaction Failed: {indicator}\nPlease check your voucher code and try again."
                    }
            
            # If no clear indicators, check URL or take screenshot for debugging
            current_url = self.page.url
            if 'success' in current_url.lower():
                return {"success": True, "message": f"✅ Top-Up Successful for UID: {uid}"}
            elif 'error' in current_url.lower():
                return {"success": False, "message": "❌ Transaction Error Occurred"}
            
            # Default response if cannot determine
            return {"success": False, "message": "❓ Unable to verify transaction status. Please check your account manually."}
            
        except Exception as e:
            logger.error(f"Top-up error: {str(e)}")
            return {"success": False, "message": f"❌ Automation Error: {str(e)}"}
        
        finally:
            # Clean up
            if self.browser:
                await self.browser.close()

    async def validate_inputs(self, uid: str, amount: str, serial: str, pin: str) -> Tuple[bool, str]:
        """Validate input parameters"""
        if not uid or len(uid) < 5:
            return False, "Invalid UID"
        
        valid_amounts = ["25", "50", "115", "240", "610", "1240", "2530"]
        if amount not in valid_amounts:
            return False, f"Invalid amount. Choose from: {', '.join(valid_amounts)}"
        
        if not serial or len(serial) < 10:
            return False, "Invalid serial code"
        
        if not pin or len(pin.replace('-', '')) != 16:
            return False, "Invalid PIN format. Should be 16 digits (with or without dashes)"
        
        return True, "Valid"

# Singleton instance
topup_handler = FreeFireTopUp()

            
           
