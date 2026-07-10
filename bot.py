# bot.py - Simple Nested Lookup Bot
import os
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== CONFIGURATION =====
BOT_TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get('PORT', 10000))

if not BOT_TOKEN:
    logger.error("BOT_TOKEN not set!")
    raise ValueError("BOT_TOKEN environment variable is required!")

# ===== ALLOWED USERS (Optional) =====
# Leave empty to allow everyone, or add Telegram user IDs
ALLOWED_USERS = []
allowed_str = os.environ.get('ALLOWED_USER_IDS', '')
if allowed_str:
    ALLOWED_USERS = [int(x.strip()) for x in allowed_str.split(',') if x.strip()]

# ===== DEFAULT DATA =====
DEFAULT_DOCUMENT = {
    "build_version": {
        "model_name": "MacBook Pro",
        "build_version": {
            "processor_name": "Intel Core i7",
            "processor_speed": "2.7 GHz",
            "core_details": {
                "build_version": "4",
                "l2_cache(per_core)": "256 KB"
            }
        },
        "number_of_cores": "4",
        "memory": "256 KB"
    },
    "os_details": {
        "product_version": "10.13.6",
        "build_version": "17G65"
    },
    "name": "Test",
    "date": "YYYY-MM-DD HH:MM:SS"
}

user_data = {}

# ===== HELPERS =====
async def check_user(update: Update) -> bool:
    if not ALLOWED_USERS:
        return True
    if update.effective_user.id in ALLOWED_USERS:
        return True
    await update.message.reply_text("⛔ Unauthorized.")
    return False

# ===== COMMAND HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update):
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"document": DEFAULT_DOCUMENT.copy()}
    
    welcome = """
🤖 *Nested Lookup Bot*

*Commands:*
🔍 `/lookup <key>` - Find all values for a key
📋 `/keys` - Show all unique keys
📄 `/view` - View your document
✏️ `/update <key> <value>` - Update a key
🗑️ `/delete <key>` - Delete a key
🔄 `/reset` - Reset to default
📊 `/stats` - Show statistics
❓ `/help` - Show this message

*Example:* `/lookup build_version`
    """
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update):
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    doc = user_data[user_id]["document"]
    formatted = json.dumps(doc, indent=2, ensure_ascii=False)
    
    if len(formatted) > 4000:
        formatted = formatted[:4000] + "\n... (truncated)"
    
    await update.message.reply_text(
        f"📄 *Your Document:*\n```json\n{formatted}\n```",
        parse_mode='Markdown'
    )

async def lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update):
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /lookup <key>\nExample: /lookup build_version")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    key = context.args[0]
    doc = user_data[user_id]["document"]
    
    try:
        from nested_lookup import nested_lookup
        results = nested_lookup(key, doc)
        
        if not results:
            await update.message.reply_text(f"Key '{key}' not found.")
            return
        
        if len(results) == 1:
            await update.message.reply_text(f"🔍 Found: `{results[0]}`", parse_mode='Markdown')
        else:
            response = f"🔍 Found {len(results)} values:\n"
            for i, val in enumerate(results[:10], 1):
                response += f"{i}. `{str(val)[:50]}`\n"
            if len(results) > 10:
                response += f"... and {len(results) - 10} more"
            await update.message.reply_text(response, parse_mode='Markdown')
            
    except ImportError:
        await update.message.reply_text("❌ nested_lookup module not installed. Please add it to requirements.txt")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def show_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update):
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    doc = user_data[user_id]["document"]
    
    try:
        from nested_lookup import get_all_keys
        all_keys = get_all_keys(doc)
        keys_list = sorted(list(all_keys))
        
        if not keys_list:
            await update.message.reply_text("No keys found.")
            return
        
        response = f"📋 *All Keys:* ({len(keys_list)} total)\n\n"
        response += "\n".join([f"• `{k}`" for k in keys_list[:30]])
        
        if len(keys_list) > 30:
            response += f"\n\n... and {len(keys_list) - 30} more"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except ImportError:
        await update.message.reply_text("❌ nested_lookup module not installed.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def update_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update):
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /update <key> <new_value>\nExample: /update model_name 'MacBook Air'")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    key = context.args[0]
    new_value = " ".join(context.args[1:])
    
    try:
        from nested_lookup import nested_lookup, nested_update
        doc = user_data[user_id]["document"]
        old_count = len(nested_lookup(key, doc))
        
        if old_count == 0:
            await update.message.reply_text(f"Key '{key}' not found.")
            return
        
        nested_update(doc, key, new_value, in_place=True, treat_as_element=True)
        user_data[user_id]["document"] = doc
        
        await update.message.reply_text(f"✅ Updated '{key}' {old_count} time(s).")
        
    except ImportError:
        await update.message.reply_text("❌ nested_lookup module not installed.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def delete_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update):
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /delete <key>\nExample: /delete memory")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    key = context.args[0]
    
    try:
        from nested_lookup import nested_lookup, nested_delete
        doc = user_data[user_id]["document"]
        old_count = len(nested_lookup(key, doc))
        
        if old_count == 0:
            await update.message.reply_text(f"Key '{key}' not found.")
            return
        
        nested_delete(doc, key, in_place=True)
        user_data[user_id]["document"] = doc
        
        await update.message.reply_text(f"🗑️ Deleted '{key}' {old_count} time(s).")
        
    except ImportError:
        await update.message.reply_text("❌ nested_lookup module not installed.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update):
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    user_data[user_id]["document"] = DEFAULT_DOCUMENT.copy()
    await update.message.reply_text("🔄 Document reset to default.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update):
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    doc = user_data[user_id]["document"]
    
    try:
        from nested_lookup import get_all_keys
        all_keys = get_all_keys(doc)
        
        response = f"""
📊 *Document Statistics*

• Total unique keys: `{len(all_keys)}`
• Document size: `{len(json.dumps(doc))}` characters
• Top-level keys: `{len(doc)}`
"""
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except ImportError:
        await update.message.reply_text("❌ nested_lookup module not installed.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ===== MAIN =====

def main():
    logger.info("🤖 Starting bot...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("view", view))
    app.add_handler(CommandHandler("lookup", lookup))
    app.add_handler(CommandHandler("keys", show_keys))
    app.add_handler(CommandHandler("update", update_key))
    app.add_handler(CommandHandler("delete", delete_key))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("stats", stats))
    
    webhook_url = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
    
    if webhook_url:
        logger.info(f"🚀 Starting webhook on port {PORT}")
        logger.info(f"🔗 URL: https://{webhook_url}/webhook")
        
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=f"https://{webhook_url}/webhook"
        )
    else:
        logger.info("Starting polling mode...")
        app.run_polling()

if __name__ == "__main__":
    main()else:
    ALLOWED_USER_IDS = [123456789]  # Replace with your ID

RATE_LIMIT = int(os.getenv("RATE_LIMIT", "3"))

# ==================== SETUP ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN, default=types.DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))

# ==================== RATE LIMITER ====================
class RateLimiter:
    def __init__(self, max_requests: int = 3):
        self.max_requests = max_requests
        self.requests = []
    
    async def acquire(self):
        now = datetime.now().timestamp()
        self.requests = [t for t in self.requests if now - t < 1.0]
        if len(self.requests) >= self.max_requests:
            wait = 1.0 - (now - self.requests[0])
            if wait > 0:
                await asyncio.sleep(wait)
        self.requests.append(now)

rate_limiter = RateLimiter(RATE_LIMIT)

# ==================== STATES ====================
class LookupStates(StatesGroup):
    WAITING_FOR_PERSON_SEARCH = State()
    WAITING_FOR_PROPERTY_SEARCH = State()
    WAITING_FOR_DL = State()
    WAITING_FOR_NAME = State()

# ==================== TLO API CLIENT ====================
class TLOClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = TLO_API_URL
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        await rate_limiter.acquire()
        response = await http_client.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response.json()
    
    async def person_search(self, **kwargs) -> Dict:
        valid = ['first_name', 'last_name', 'middle_name', 'dob', 'ssn',
                'dl_number', 'dl_state', 'address', 'city', 'state', 'zip', 'phone', 'email']
        params = {k: v for k, v in kwargs.items() if k in valid and v}
        return await self._request("POST", "person/search", json=params)
    
    async def get_full_report(self, person_id: str) -> Dict:
        return await self._request("GET", f"person/{person_id}/full")
    
    async def get_mvr(self, dl_number: str, state: str) -> Dict:
        return await self._request("POST", "mvr", json={
            "dl_number": dl_number,
            "state": state,
            "include_history": True
        })
    
    async def get_criminal_record(self, person_id: str) -> Dict:
        return await self._request("GET", f"person/{person_id}/criminal")
    
    async def get_property_records(self, person_id: str) -> Dict:
        return await self._request("GET", f"person/{person_id}/property")
    
    async def get_relatives(self, person_id: str) -> Dict:
        return await self._request("GET", f"person/{person_id}/relatives")

tlo = TLOClient(TLO_API_KEY)

# ==================== AUDIT LOGGER ====================
class AuditLogger:
    def __init__(self, log_file: str = "audit.log"):
        self.log_file = log_file
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f:
                f.write("timestamp,user_id,username,action,query,result_count\n")
    
    async def log(self, user_id: int, username: str, action: str, query: str, result_count: int = 0):
        timestamp = datetime.now().isoformat()
        safe_query = query.replace('"', '""').replace('\n', ' ')
        entry = f'"{timestamp}",{user_id},"{username}","{action}","{safe_query}",{result_count}\n'
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(entry)
        except Exception as e:
            logger.error(f"Audit error: {e}")

audit_logger = AuditLogger()

# ==================== AUTH ====================
async def check_user(message: Message) -> bool:
    if message.from_user.id not in ALLOWED_USER_IDS:
        await message.reply("⛔ Unauthorized access.")
        return False
    return True

# ==================== PARSER ====================
def parse_person_query(query: str) -> Dict[str, str]:
    params = {}
    text = query.strip()
    
    # SSN
    ssn = re.search(r'\b\d{3}[-]?\d{2}[-]?\d{4}\b', text)
    if ssn:
        params['ssn'] = re.sub(r'[-]', '', ssn.group())
        text = text.replace(ssn.group(), '').strip()
    
    # DOB
    dob = re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text)
    if dob:
        params['dob'] = dob.group()
        text = text.replace(dob.group(), '').strip()
    
    # DL
    dl = re.search(r'\b([A-Z]{2})\s*(\d{5,10})\b', text)
    if dl:
        params['dl_state'] = dl.group(1)
        params['dl_number'] = dl.group(2)
        text = text.replace(dl.group(), '').strip()
    
    # Name
    if text:
        parts = text.split()
        if len(parts) >= 2:
            params['first_name'] = parts[0]
            params['last_name'] = ' '.join(parts[1:])
        else:
            params['last_name'] = text
    
    return params

# ==================== FORMATTERS ====================
def format_person(data: Dict) -> str:
    p = data.get('person', {})
    d = p.get('demographics', {})
    i = p.get('identifiers', {})
    c = p.get('contact', {})
    e = p.get('employment', {})
    
    return f"""
👤 <b>PERSONAL INFORMATION</b>
{'=' * 40}

<b>Full Name:</b> {d.get('full_name', 'N/A')}
<b>AKA:</b> {', '.join(p.get('aliases', [])) or 'N/A'}

<b>DOB:</b> {d.get('dob', 'N/A')}
<b>Age:</b> {d.get('age', 'N/A')}
<b>Gender:</b> {d.get('gender', 'N/A')}

<b>SSN:</b> {i.get('ssn', 'N/A')}
<b>DL Number:</b> {i.get('dl_number', 'N/A')}
<b>DL State:</b> {i.get('dl_state', 'N/A')}

<b>Address:</b>
{c.get('address', 'N/A')}
{c.get('city', '')} {c.get('state', '')} {c.get('zip', '')}
<b>Phone:</b> {c.get('phone', 'N/A')}
<b>Email:</b> {c.get('email', 'N/A')}

<b>Employer:</b> {e.get('employer', 'N/A')}
<b>Occupation:</b> {e.get('occupation', 'N/A')}
"""

def format_mvr(data: Dict) -> str:
    text = f"""
🚗 <b>MOTOR VEHICLE REPORT</b>
{'=' * 40}

<b>Name:</b> {data.get('name', 'N/A')}
<b>DL Number:</b> {data.get('dl_number', 'N/A')}
<b>State:</b> {data.get('state', 'N/A')}
<b>Status:</b> {data.get('status', 'N/A')}

<b>History:</b>
"""
    for r in data.get('history', [])[:5]:
        text += f"  • {r.get('date', 'N/A')}: {r.get('action', 'N/A')}\n"
    return text

def format_criminal(data: Dict) -> str:
    text = f"""
⚖️ <b>CRIMINAL RECORD</b>
{'=' * 40}

<b>Felonies:</b>
"""
    for f in data.get('felonies', [])[:5]:
        text += f"  ⚠️ {f.get('offense', 'N/A')} ({f.get('date', 'N/A')})\n"
    
    text += f"\n<b>Misdemeanors:</b>\n"
    for o in data.get('misdemeanors', [])[:5]:
        text += f"  • {o.get('offense', 'N/A')} ({o.get('date', 'N/A')})\n"
    return text

def format_property(data: Dict) -> str:
    text = f"""
🏠 <b>PROPERTY RECORDS</b>
{'=' * 40}

<b>Properties:</b>
"""
    for p in data.get('properties', [])[:5]:
        text += f"""
  📍 {p.get('address', 'N/A')}
  • Value: ${p.get('value', 'N/A'):,}
  • Year: {p.get('year_built', 'N/A')}
"""
    return text

def format_relatives(data: Dict) -> str:
    text = f"""
👨‍👩‍👧‍👦 <b>RELATIVES</b>
{'=' * 40}

<b>Immediate Family:</b>
"""
    for r in data.get('immediate_family', [])[:5]:
        text += f"  • {r.get('name', 'N/A')} ({r.get('relation', 'N/A')})\n"
    return text

# ==================== SEND LONG MESSAGE ====================
async def send_long_message(message: Message, text: str, title: str = ""):
    if not text:
        await message.reply("❌ Empty response.")
        return
    
    # Strip HTML for length check
    clean = text.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
    clean = clean.replace('<u>', '').replace('</u>', '').replace('<code>', '').replace('</code>', '')
    
    if len(clean) <= 4096:
        await message.reply(text)
        return
    
    lines = text.split('\n')
    parts = []
    current = ""
    
    for line in lines:
        clean_line = line.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
        if len(current) + len(clean_line) + 1 > 3800:
            parts.append(current)
            current = line + '\n'
        else:
            current += line + '\n'
    
    if current:
        parts.append(current)
    
    for i, part in enumerate(parts, 1):
        if title and len(parts) > 1:
            await message.reply(f"📄 <b>{title}</b> (Part {i}/{len(parts)})\n\n{part}")
        else:
            await message.reply(part)

# ==================== COMPLIANCE ====================
COMPLIANCE_NOTICE = """
<i>⚠️ <b>FCRA COMPLIANCE NOTICE</b></i>

This information is a <b>consumer report</b> under the Fair Credit Reporting Act (FCRA).

<b>You must have a permissible purpose</b> to obtain this report.

<i>Unauthorized use is a federal offense.</i>
"""

# ==================== BOT COMMANDS ====================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    if not await check_user(message):
        return
    
    await audit_logger.log(
        message.from_user.id,
        message.from_user.username or str(message.from_user.id),
        "start",
        "/start"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🔍 Person Search", callback_data="person_search")],
        [InlineKeyboardButton("🚗 MVR Lookup", callback_data="mvr_lookup")],
        [InlineKeyboardButton("⚖️ Criminal Check", callback_data="criminal_check")],
        [InlineKeyboardButton("🏠 Property Records", callback_data="property_records")],
        [InlineKeyboardButton("👨‍👩‍👧‍👦 Find Relatives", callback_data="find_relatives")],
        [InlineKeyboardButton("📋 Compliance Info", callback_data="compliance")]
    ])
    
    await message.reply(
        "🔍 <b>TLO PERSONAL INFORMATION LOOKUP</b>\n\n"
        "Select what you want to search for:\n"
        "• Person Search - Name, DOB, SSN\n"
        "• MVR - Driver's license history\n"
        "• Criminal - Court records\n"
        "• Property - Real estate owned\n"
        "• Relatives - Family & associates\n\n"
        "<i>All searches are logged and audited.</i>",
        reply_markup=keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    if not await check_user(message):
        return
    
    await message.reply(
        "📖 <b>Help & Commands</b>\n\n"
        "/start - Main menu\n"
        "/search <query> - Search person\n"
        "/mvr <DL#> <state> - MVR lookup\n"
        "/criminal <name> - Criminal check\n"
        "/property <name> - Property records\n"
        "/relatives <name> - Find relatives\n"
        "/compliance - FCRA compliance info\n"
        "/cancel - Cancel current operation\n"
        "/help - This message\n\n"
        "<i>All searches are monitored and logged.</i>"
    )

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    if await state.get_state():
        await state.clear()
        await message.reply("✅ Cancelled current operation.")
    else:
        await message.reply("❌ Nothing to cancel.")

@dp.message(Command("compliance"))
async def cmd_compliance(message: Message):
    if not await check_user(message):
        return
    await message.reply(COMPLIANCE_NOTICE)

@dp.callback_query(lambda c: c.data == "compliance")
async def callback_compliance(callback: types.CallbackQuery):
    await callback.message.reply(COMPLIANCE_NOTICE)
    await callback.answer()

# ==================== PERSON SEARCH ====================
@dp.callback_query(lambda c: c.data == "person_search")
async def callback_person_search(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "👤 <b>PERSON SEARCH</b>\n\n"
        "Examples:\n"
        "<code>John Doe</code>\n"
        "<code>John Doe 01/15/1980</code>\n"
        "<code>John Doe CA DL1234567</code>\n"
        "<code>John Doe 123-45-6789</code>\n\n"
        "Type /cancel to stop.",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_PERSON_SEARCH)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_PERSON_SEARCH)
async def process_person_search(message: Message, state: FSMContext):
    query = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    
    params = parse_person_query(query)
    if not params:
        await message.reply("❌ Could not parse input. Please provide at least a name.")
        return
    
    await audit_logger.log(user_id, username, "person_search", query, 0)
    await message.reply("⏳ Searching...")
    
    try:
        result = await tlo.person_search(**params)
        if not result.get('found'):
            await message.reply("❌ No matching records found.")
            await state.clear()
            return
        
        person_id = result['person_id']
        full = await tlo.get_full_report(person_id)
        formatted = format_person(full)
        await send_long_message(message, formatted, "Personal Information")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("🚗 MVR", callback_data=f"mvr_{person_id}")],
            [InlineKeyboardButton("⚖️ Criminal", callback_data=f"criminal_{person_id}")],
            [InlineKeyboardButton("🏠 Property", callback_data=f"property_{person_id}")],
            [InlineKeyboardButton("👨‍👩‍👧‍👦 Relatives", callback_data=f"relatives_{person_id}")]
        ])
        await message.reply("📋 <b>Additional Reports:</b>", reply_markup=keyboard)
        await audit_logger.log(user_id, username, "person_search_result", query, 1)
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
    
    await state.clear()

# ==================== MVR ====================
@dp.callback_query(lambda c: c.data == "mvr_lookup")
async def callback_mvr(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "🚗 <b>MVR LOOKUP</b>\n\n"
        "Send: <code>DL_NUMBER STATE</code>\n"
        "Example: <code>D1234567 CA</code>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_DL)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_DL)
async def process_mvr(message: Message, state: FSMContext):
    parts = message.text.strip().upper().split()
    if len(parts) < 2:
        await message.reply("❌ Example: <code>D1234567 CA</code>")
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    await audit_logger.log(user_id, username, "mvr_lookup", message.text, 0)
    await message.reply("⏳ Retrieving MVR...")
    
    try:
        result = await tlo.get_mvr(parts[0], parts[1])
        if result.get('found'):
            await send_long_message(message, format_mvr(result), "MVR Report")
            await audit_logger.log(user_id, username, "mvr_result", message.text, 1)
        else:
            await message.reply("❌ No records found.")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
    await state.clear()

# ==================== CRIMINAL ====================
@dp.callback_query(lambda c: c.data == "criminal_check")
async def callback_criminal(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "⚖️ <b>CRIMINAL CHECK</b>\n\n"
        "Example: <code>John Doe 01/15/1980</code>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_NAME)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_NAME)
async def process_criminal(message: Message, state: FSMContext):
    text = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    
    params = parse_person_query(text)
    await audit_logger.log(user_id, username, "criminal_search", text, 0)
    await message.reply("⏳ Checking records...")
    
    try:
        result = await tlo.person_search(**params)
        if not result.get('found'):
            await message.reply("❌ No matching records found.")
            await state.clear()
            return
        
        criminal = await tlo.get_criminal_record(result['person_id'])
        if criminal.get('found'):
            await send_long_message(message, format_criminal(criminal), "Criminal Record")
            await audit_logger.log(user_id, username, "criminal_result", text, 1)
        else:
            await message.reply("✅ No criminal records found.")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
    await state.clear()

# ==================== PROPERTY ====================
@dp.callback_query(lambda c: c.data == "property_records")
async def callback_property(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "🏠 <b>PROPERTY RECORDS</b>\n\n"
        "Example: <code>John Doe</code>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_PROPERTY_SEARCH)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_PROPERTY_SEARCH)
async def process_property(message: Message, state: FSMContext):
    query = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    
    params = parse_person_query(query)
    await audit_logger.log(user_id, username, "property_search", query, 0)
    await message.reply("⏳ Searching property records...")
    
    try:
        result = await tlo.person_search(**params)
        if not result.get('found'):
            await message.reply("❌ No records found.")
            await state.clear()
            return
        
        props = await tlo.get_property_records(result['person_id'])
        await send_long_message(message, format_property(props), "Property Records")
        await audit_logger.log(user_id, username, "property_result", query, 1)
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
    await state.clear()

# ==================== RELATIVES ====================
@dp.callback_query(lambda c: c.data == "find_relatives")
async def callback_relatives(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "👨‍👩‍👧‍👦 <b>FIND RELATIVES</b>\n\n"
        "Example: <code>John Doe 01/15/1980</code>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_NAME)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_NAME)
async def process_relatives(message: Message, state: FSMContext):
    text = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    
    params = parse_person_query(text)
    await audit_logger.log(user_id, username, "relatives_search", text, 0)
    await message.reply("⏳ Finding relatives...")
    
    try:
        result = await tlo.person_search(**params)
        if not result.get('found'):
            await message.reply("❌ No matching records found.")
            await state.clear()
            return
        
        relatives = await tlo.get_relatives(result['person_id'])
        await send_long_message(message, format_relatives(relatives), "Relatives Report")
        await audit_logger.log(user_id, username, "relatives_result", text, 1)
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
    await state.clear()

# ==================== ADDITIONAL CALLBACKS ====================
@dp.callback_query(lambda c: c.data.startswith("criminal_"))
async def callback_criminal_result(callback: types.CallbackQuery):
    person_id = callback.data.split("_")[1]
    user_id = callback.from_user.id
    username = callback.from_user.username or str(user_id)
    
    await audit_logger.log(user_id, username, "criminal_person", person_id, 0)
    await callback.message.reply("⏳ Retrieving criminal records...")
    
    try:
        criminal = await tlo.get_criminal_record(person_id)
        await send_long_message(callback.message, format_criminal(criminal), "Criminal Record")
        await audit_logger.log(user_id, username, "criminal_person_result", person_id, 1)
    except Exception as e:
        await callback.message.reply(f"❌ Error: {str(e)}")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("property_"))
async def callback_property_result(callback: types.CallbackQuery):
    person_id = callback.data.split("_")[1]
    user_id = callback.from_user.id
    username = callback.from_user.username or str(user_id)
    
    await audit_logger.log(user_id, username, "property_person", person_id, 0)
    await callback.message.reply("⏳ Retrieving property records...")
    
    try:
        props = await tlo.get_property_records(person_id)
        await send_long_message(callback.message, format_property(props), "Property Records")
        await audit_logger.log(user_id, username, "property_person_result", person_id, 1)
    except Exception as e:
        await callback.message.reply(f"❌ Error: {str(e)}")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("relatives_"))
async def callback_relatives_result(callback: types.CallbackQuery):
    person_id = callback.data.split("_")[1]
    user_id = callback.from_user.id
    username = callback.from_user.username or str(user_id)
    
    await audit_logger.log(user_id, username, "relatives_person", person_id, 0)
    await callback.message.reply("⏳ Retrieving relatives...")
    
    try:
        relatives = await tlo.get_relatives(person_id)
        await send_long_message(callback.message, format_relatives(relatives), "Relatives Report")
        await audit_logger.log(user_id, username, "relatives_person_result", person_id, 1)
    except Exception as e:
        await callback.message.reply(f"❌ Error: {str(e)}")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("mvr_"))
async def callback_mvr_result(callback: types.CallbackQuery):
    await callback.message.reply("⚠️ MVR requires DL number and state. Please use /mvr command.")
    await callback.answer()

# ==================== MAIN ====================
async def main():
    logger.info("🚀 Starting TLO Personal Info Bot...")
    logger.info(f"👥 Allowed users: {ALLOWED_USER_IDS}")
    logger.info(f"📊 Rate limit: {RATE_LIMIT} requests/second")
    
    try:
        await bot.delete_webhook()
        await dp.start_polling(bot, allowed_updates=types.UpdateType.MESSAGE)
    finally:
        await http_client.aclose()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")    ALLOWED_USER_IDS = [int(x.strip()) for x in allowed_users_str.split(",") if x.strip()]
else:
    # Default demo users - REPLACE WITH YOUR TELEGRAM IDs
    ALLOWED_USER_IDS = [123456789, 987654321]

RATE_LIMIT = int(os.getenv("RATE_LIMIT", "3"))  # requests per second

# ==================== SETUP ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN, default=types.DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

# HTTP client with longer timeout
http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))

# ==================== RATE LIMITER ====================
class RateLimiter:
    def __init__(self, max_requests_per_second: int = 3):
        self.max_requests = max_requests_per_second
        self.requests = []
    
    async def acquire(self):
        now = datetime.now().timestamp()
        self.requests = [t for t in self.requests if now - t < 1.0]
        
        if len(self.requests) >= self.max_requests:
            wait_time = 1.0 - (now - self.requests[0])
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self.requests.append(now)

rate_limiter = RateLimiter(RATE_LIMIT)

# ==================== STATES ====================
class LookupStates(StatesGroup):
    WAITING_FOR_PERSON_SEARCH = State()
    WAITING_FOR_PROPERTY_SEARCH = State()
    WAITING_FOR_DL = State()
    WAITING_FOR_NAME = State()

# ==================== TLO API CLIENT ====================
class TLOClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = TLO_API_URL
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            await rate_limiter.acquire()
            response = await http_client.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise
    
    async def person_search(self, **kwargs) -> Dict:
        valid_fields = ['first_name', 'last_name', 'middle_name', 'dob', 'ssn',
                       'dl_number', 'dl_state', 'address', 'city', 'state', 
                       'zip', 'phone', 'email']
        params = {k: v for k, v in kwargs.items() if k in valid_fields and v}
        return await self._request("POST", "person/search", json=params)
    
    async def get_full_report(self, person_id: str) -> Dict:
        return await self._request("GET", f"person/{person_id}/full")
    
    async def get_mvr(self, dl_number: str, state: str) -> Dict:
        return await self._request("POST", "mvr", json={
            "dl_number": dl_number,
            "state": state,
            "include_history": True
        })
    
    async def get_criminal_record(self, person_id: str) -> Dict:
        return await self._request("GET", f"person/{person_id}/criminal")
    
    async def get_property_records(self, person_id: str) -> Dict:
        return await self._request("GET", f"person/{person_id}/property")
    
    async def get_relatives(self, person_id: str) -> Dict:
        return await self._request("GET", f"person/{person_id}/relatives")

tlo = TLOClient(TLO_API_KEY)

# ==================== AUDIT LOGGER ====================
class AuditLogger:
    def __init__(self, log_file: str = "audit.log"):
        self.log_file = log_file
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f:
                f.write("timestamp,user_id,username,action,query,result_count\n")
    
    async def log(self, user_id: int, username: str, action: str, query: str, result_count: int = 0):
        timestamp = datetime.now().isoformat()
        query_safe = query.replace('"', '""').replace('\n', ' ')
        log_entry = f'"{timestamp}",{user_id},"{username}","{action}","{query_safe}",{result_count}\n'
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Audit log error: {e}")

audit_logger = AuditLogger()

# ==================== AUTH MIDDLEWARE ====================
async def check_user(message: Message) -> bool:
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    if user_id not in ALLOWED_USER_IDS:
        logger.warning(f"Unauthorized: {username} ({user_id})")
        await message.reply("⛔ Unauthorized access.")
        return False
    return True

# ==================== PARSING HELPER ====================
def parse_person_query(query: str) -> Dict[str, str]:
    params = {}
    text = query.strip()
    
    # SSN
    ssn_match = re.search(r'\b\d{3}[-]?\d{2}[-]?\d{4}\b', text)
    if ssn_match:
        params['ssn'] = re.sub(r'[-]', '', ssn_match.group())
        text = text.replace(ssn_match.group(), '').strip()
    
    # DOB
    dob_match = re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text)
    if dob_match:
        params['dob'] = dob_match.group()
        text = text.replace(dob_match.group(), '').strip()
    
    # DL
    dl_match = re.search(r'\b([A-Z]{2})\s*(\d{5,10})\b', text)
    if dl_match:
        params['dl_state'] = dl_match.group(1)
        params['dl_number'] = dl_match.group(2)
        text = text.replace(dl_match.group(), '').strip()
    
    # Name
    if text:
        parts = text.split()
        if len(parts) >= 2:
            params['first_name'] = parts[0]
            params['last_name'] = ' '.join(parts[1:])
        else:
            params['last_name'] = text
    
    return params

# ==================== FORMATTERS ====================
def format_person_info(data: Dict) -> str:
    person = data.get('person', {})
    d = person.get('demographics', {})
    i = person.get('identifiers', {})
    c = person.get('contact', {})
    e = person.get('employment', {})
    
    return f"""
👤 <b>PERSONAL INFORMATION</b>
{'=' * 40}

<b>Full Name:</b> {d.get('full_name', 'N/A')}
<b>AKA/Aliases:</b> {', '.join(person.get('aliases', [])) or 'N/A'}

<b>Date of Birth:</b> {d.get('dob', 'N/A')}
<b>Age:</b> {d.get('age', 'N/A')}
<b>Gender:</b> {d.get('gender', 'N/A')}
<b>Race:</b> {d.get('race', 'N/A')}

<b>SSN:</b> {i.get('ssn', 'N/A')}
<b>Driver's License:</b> {i.get('dl_number', 'N/A')}
<b>DL State:</b> {i.get('dl_state', 'N/A')}
<b>DL Status:</b> {i.get('dl_status', 'N/A')}

<b>Current Address:</b> 
{c.get('address', 'N/A')}
{c.get('city', '')} {c.get('state', '')} {c.get('zip', '')}
<b>Phone:</b> {c.get('phone', 'N/A')}
<b>Email:</b> {c.get('email', 'N/A')}

<b>Employment:</b>
<b>Employer:</b> {e.get('employer', 'N/A')}
<b>Occupation:</b> {e.get('occupation', 'N/A')}

<b>Confidence Score:</b> {data.get('confidence', 0)}%
"""

def format_mvr(data: Dict) -> str:
    text = f"""
🚗 <b>MOTOR VEHICLE REPORT</b>
{'=' * 40}

<b>Name:</b> {data.get('name', 'N/A')}
<b>DL Number:</b> {data.get('dl_number', 'N/A')}
<b>State:</b> {data.get('state', 'N/A')}
<b>Status:</b> {data.get('status', 'N/A')}
<b>License Class:</b> {data.get('class', 'N/A')}

<b>License History:</b>
"""
    for r in data.get('history', [])[:5]:
        text += f"  • {r.get('date', 'N/A')}: {r.get('action', 'N/A')}\n"
    return text

def format_criminal(data: Dict) -> str:
    text = f"""
⚖️ <b>CRIMINAL RECORD</b>
{'=' * 40}

<b>Felonies:</b>
"""
    for f in data.get('felonies', [])[:5]:
        text += f"  ⚠️ {f.get('offense', 'N/A')} ({f.get('date', 'N/A')})\n"
    
    text += f"\n<b>Misdemeanors:</b>\n"
    for o in data.get('misdemeanors', [])[:5]:
        text += f"  • {o.get('offense', 'N/A')} ({o.get('date', 'N/A')})\n"
    return text

def format_property(data: Dict) -> str:
    text = f"""
🏠 <b>PROPERTY RECORDS</b>
{'=' * 40}

<b>Properties Owned:</b>
"""
    for p in data.get('properties', [])[:5]:
        text += f"""
  📍 {p.get('address', 'N/A')}
  • Type: {p.get('type', 'N/A')}
  • Value: ${p.get('value', 'N/A'):,}
  • Year Built: {p.get('year_built', 'N/A')}
"""
    return text

def format_relatives(data: Dict) -> str:
    text = f"""
👨‍👩‍👧‍👦 <b>RELATIVES & ASSOCIATES</b>
{'=' * 40}

<b>Immediate Family:</b>
"""
    for r in data.get('immediate_family', [])[:5]:
        text += f"  • {r.get('name', 'N/A')} ({r.get('relation', 'N/A')})\n"
    return text

# ==================== SEND LONG MESSAGE ====================
async def send_long_message(message: Message, text: str, title: str = ""):
    if len(text) <= 4096:
        await message.reply(text)
        return
    parts = [text[i:i+4096] for i in range(0, len(text), 4096)]
    for i, part in enumerate(parts, 1):
        await message.reply(f"📄 <b>{title}</b> (Part {i}/{len(parts)})\n\n{part}")

# ==================== COMPLIANCE NOTICE ====================
COMPLIANCE_NOTICE = """
<i>⚠️ <b>FCRA COMPLIANCE NOTICE</b></i>

This information is a <b>consumer report</b> under the Fair Credit Reporting Act (FCRA).

<b>You must have a permissible purpose</b> to obtain this report.

<i>Unauthorized use is a federal offense.</i>
"""

# ==================== BOT COMMANDS ====================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    if not await check_user(message): return
    await audit_logger.log(message.from_user.id, message.from_user.username or str(message.from_user.id), "start", "/start")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🔍 Person Search", callback_data="person_search")],
        [InlineKeyboardButton("🚗 MVR Lookup", callback_data="mvr_lookup")],
        [InlineKeyboardButton("⚖️ Criminal Check", callback_data="criminal_check")],
        [InlineKeyboardButton("🏠 Property Records", callback_data="property_records")],
        [InlineKeyboardButton("👨‍👩‍👧‍👦 Find Relatives", callback_data="find_relatives")],
        [InlineKeyboardButton("📋 Compliance Info", callback_data="compliance")]
    ])
    await message.reply(
        "🔍 <b>TLO PERSONAL INFORMATION LOOKUP</b>\n\n"
        "Select what you want to search for:\n"
        "• Person Search - Name, DOB, SSN\n"
        "• MVR - Driver's license history\n"
        "• Criminal - Court records\n"
        "• Property - Real estate owned\n"
        "• Relatives - Family & associates\n\n"
        "<i>All searches are logged and audited.</i>",
        reply_markup=keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    if not await check_user(message): return
    await message.reply(
        "📖 <b>Help & Commands</b>\n\n"
        "/start - Main menu\n"
        "/search <query> - Search person\n"
        "/mvr <DL#> <state> - MVR lookup\n"
        "/criminal <name> - Criminal check\n"
        "/property <name> - Property records\n"
        "/relatives <name> - Find relatives\n"
        "/compliance - FCRA compliance info\n"
        "/cancel - Cancel current operation\n"
        "/help - This message\n\n"
        "<i>All searches are monitored and logged.</i>"
    )

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    if await state.get_state():
        await state.clear()
        await message.reply("✅ Cancelled current operation.")
    else:
        await message.reply("❌ Nothing to cancel.")

@dp.message(Command("compliance"))
async def cmd_compliance(message: Message):
    if not await check_user(message): return
    await message.reply(COMPLIANCE_NOTICE)

@dp.callback_query(lambda c: c.data == "compliance")
async def callback_compliance(callback: types.CallbackQuery):
    await callback.message.reply(COMPLIANCE_NOTICE)
    await callback.answer()

# ==================== PERSON SEARCH ====================
@dp.callback_query(lambda c: c.data == "person_search")
async def callback_person_search(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "👤 <b>PERSON SEARCH</b>\n\n"
        "Examples:\n"
        "<code>John Doe</code>\n"
        "<code>John Doe 01/15/1980</code>\n"
        "<code>John Doe CA DL1234567</code>\n"
        "<code>John Doe 123-45-6789</code>\n\n"
        "Type /cancel to stop.",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_PERSON_SEARCH)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_PERSON_SEARCH)
async def process_person_search(message: Message, state: FSMContext):
    query = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    
    params = parse_person_query(query)
    if not params:
        await message.reply("❌ Could not parse input. Please provide at least a name.")
        return
    
    await audit_logger.log(user_id, username, "person_search", query, 0)
    await message.reply("⏳ Searching TLO database...")
    
    try:
        result = await tlo.person_search(**params)
        if not result.get('found'):
            await message.reply("❌ No matching records found.")
            await state.clear()
            return
        
        person_id = result['person_id']
        full_report = await tlo.get_full_report(person_id)
        formatted = format_person_info(full_report)
        await send_long_message(message, formatted, "Personal Information")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("🚗 Get MVR", callback_data=f"mvr_{person_id}")],
            [InlineKeyboardButton("⚖️ Criminal Check", callback_data=f"criminal_{person_id}")],
            [InlineKeyboardButton("🏠 Property Records", callback_data=f"property_{person_id}")],
            [InlineKeyboardButton("👨‍👩‍👧‍👦 Relatives", callback_data=f"relatives_{person_id}")]
        ])
        await message.reply("📋 <b>Additional Reports Available:</b>", reply_markup=keyboard)
        await audit_logger.log(user_id, username, "person_search_result", query, 1)
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
    await state.clear()

# ==================== MVR LOOKUP ====================
@dp.callback_query(lambda c: c.data == "mvr_lookup")
async def callback_mvr(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "🚗 <b>MVR LOOKUP</b>\n\n"
        "Please send: <code>DL_NUMBER STATE</code>\n"
        "Example: <code>D1234567 CA</code>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_DL)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_DL)
async def process_mvr(message: Message, state: FSMContext):
    parts = message.text.strip().upper().split()
    if len(parts) < 2:
        await message.reply("❌ Please provide DL number and state. Example: <code>D1234567 CA</code>")
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    await audit_logger.log(user_id, username, "mvr_lookup", message.text, 0)
    await message.reply("⏳ Retrieving MVR...")
    
    try:
        result = await tlo.get_mvr(parts[0], parts[1])
        if result.get('found'):
            await send_long_message(message, format_mvr(result), "MVR Report")
            await audit_logger.log(user_id, username, "mvr_result", message.text, 1)
        else:
            await message.reply("❌ No MVR records found.")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
    await state.clear()

# ==================== CRIMINAL CHECK ====================
@dp.callback_query(lambda c: c.data == "criminal_check")
async def callback_criminal(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "⚖️ <b>CRIMINAL RECORD CHECK</b>\n\n"
        "Please send name and DOB.\n"
        "Example: <code>John Doe 01/15/1980</code>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_NAME)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_NAME)
async def process_criminal(message: Message, state: FSMContext):
    text = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    
    params = parse_person_query(text)
    await audit_logger.log(user_id, username, "criminal_search", text, 0)
    await message.reply("⏳ Checking criminal records...")
    
    try:
        result = await tlo.person_search(**params)
        if not result.get('found'):
            await message.reply("❌ No matching records found.")
            await state.clear()
            return
        
        criminal = await tlo.get_criminal_record(result['person_id'])
        if criminal.get('found'):
            await send_long_message(message, format_criminal(criminal), "Criminal Record")
            await audit_logger.log(user_id, username, "criminal_result", text, 1)
        else:
            await message.reply("✅ No criminal records found.")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
    await state.clear()

# ==================== PROPERTY RECORDS ====================
@dp.callback_query(lambda c: c.data == "property_records")
async def callback_property(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "🏠 <b>PROPERTY RECORDS</b>\n\n"
        "Please send the person's name.\n"
        "Example: <code>John Doe</code>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_PROPERTY_SEARCH)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_PROPERTY_SEARCH)
async def process_property(message: Message, state: FSMContext):
    query = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    
    params = parse_person_query(query)
    await audit_logger.log(user_id, username, "property_search", query, 0)
    await message.reply("⏳ Searching property records...")
    
    try:
        result = await tlo.person_search(**params)
        if not result.get('found'):
            await message.reply("❌ No records found.")
            await state.clear()
            return
        
        property_records = await tlo.get_property_records(result['person_id'])
        await send_long_message(message, format_property(property_records), "Property Records")
        await audit_logger.log(user_id, username, "property_result", query, 1)
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
    await state.clear()

# ==================== FIND RELATIVES ====================
@dp.callback_query(lambda c: c.data == "find_relatives")
async def callback_relatives(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "👨‍👩‍👧‍👦 <b>FIND RELATIVES</b>\n\n"
        "Please send name and DOB.\n"
        "Example: <code>John Doe 01/15/1980</code>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_NAME)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_NAME)
async def process_relatives(message: Message, state: FSMContext):
    text = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    
    params = parse_person_query(text)
    await audit_logger.log(user_id, username, "relatives_search", text, 0)
    await message.reply("⏳ Finding relatives...")
    
    try:
        result = await tlo.person_search(**params)
        if not result.get('found'):
            await message.reply("❌ No matching records found.")
            await state.clear()
            return
        
        relatives = await tlo.get_relatives(result['person_id'])
        await send_long_message(message, format_relatives(relatives), "Relatives Report")
        await audit_logger.log(user_id, username, "relatives_result", text, 1)
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
    await state.clear()

# ==================== ADDITIONAL REPORT CALLBACKS ====================
@dp.callback_query(lambda c: c.data.startswith("criminal_"))
async def callback_criminal_result(callback: types.CallbackQuery):
    person_id = callback.data.split("_")[1]
    user_id = callback.from_user.id
    username = callback.from_user.username or str(user_id)
    
    await audit_logger.log(user_id, username, "criminal_person_id", person_id, 0)
    await callback.message.reply("⏳ Retrieving criminal records...")
    
    try:
        criminal = await tlo.get_criminal_record(person_id)
        await send_long_message(callback.message, format_criminal(criminal), "Criminal Record")
        await audit_logger.log(user_id, username, "criminal_person_result", person_id, 1)
    except Exception as e:
        await callback.message.reply(f"❌ Error: {str(e)}")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("property_"))
async def callback_property_result(callback: types.CallbackQuery):
    person_id = callback.data.split("_")[1]
    user_id = callback.from_user.id
    username = callback.from_user.username or str(user_id)
    
    await audit_logger.log(user_id, username, "property_person_id", person_id, 0)
    await callback.message.reply("⏳ Retrieving property records...")
    
    try:
        property_records = await tlo.get_property_records(person_id)
        await send_long_message(callback.message, format_property(property_records), "Property Records")
        await audit_logger.log(user_id, username, "property_person_result", person_id, 1)
    except Exception as e:
        await callback.message.reply(f"❌ Error: {str(e)}")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("relatives_"))
async def callback_relatives_result(callback: types.CallbackQuery):
    person_id = callback.data.split("_")[1]
    user_id = callback.from_user.id
    username = callback.from_user.username or str(user_id)
    
    await audit_logger.log(user_id, username, "relatives_person_id", person_id, 0)
    await callback.message.reply("⏳ Retrieving relatives...")
    
    try:
        relatives = await tlo.get_relatives(person_id)
        await send_long_message(callback.message, format_relatives(relatives), "Relatives Report")
        await audit_logger.log(user_id, username, "relatives_person_result", person_id, 1)
    except Exception as e:
        await callback.message.reply(f"❌ Error: {str(e)}")
    await callback.answer()

# ==================== MAIN ====================
async def main():
    logger.info("🚀 Starting TLO Personal Info Bot...")
    logger.info(f"👥 Allowed users: {ALLOWED_USER_IDS}")
    logger.info(f"📊 Rate limit: {RATE_LIMIT} requests/second")
    
    try:
        await bot.delete_webhook()
        await dp.start_polling(bot, allowed_updates=types.UpdateType.MESSAGE)
    finally:
        await http_client.aclose()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")    ALLOWED_USER_IDS = [int(x.strip()) for x in allowed_users_str.split(",") if x.strip()]
else:
    # Default demo users - REPLACE WITH YOUR TELEGRAM IDs
    ALLOWED_USER_IDS = [123456789, 987654321]

RATE_LIMIT = int(os.getenv("RATE_LIMIT", "3"))  # requests per second

# ==================== SETUP ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN, default=types.DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

# HTTP client with longer timeout
http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))

# Simple rate limiter
class RateLimiter:
    def __init__(self, max_requests_per_second: int = 3):
        self.max_requests = max_requests_per_second
        self.requests = []
    
    async def acquire(self):
        now = datetime.now().timestamp()
        # Remove requests older than 1 second
        self.requests = [t for t in self.requests if now - t < 1.0]
        
        if len(self.requests) >= self.max_requests:
            wait_time = 1.0 - (now - self.requests[0])
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self.requests.append(now)

rate_limiter = RateLimiter(RATE_LIMIT)

# ==================== STATES ====================
class LookupStates(StatesGroup):
    WAITING_FOR_PERSON_SEARCH = State()
    WAITING_FOR_PROPERTY_SEARCH = State()
    WAITING_FOR_DL = State()
    WAITING_FOR_NAME = State()

# ==================== TLO API CLIENT ====================
class TLOClient:
    """Complete TLO API Client with retry logic"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = TLO_API_URL
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Generic request method with retry logic"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            await rate_limiter.acquire()
            response = await http_client.request(
                method,
                url,
                headers=self.headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise
    
    async def person_search(self, **kwargs) -> Dict:
        """Search person by name, DOB, SSN, etc."""
        # Build query parameters
        params = {}
        valid_fields = [
            'first_name', 'last_name', 'middle_name', 'dob', 'ssn',
            'dl_number', 'dl_state', 'address', 'city', 'state', 
            'zip', 'phone', 'email'
        ]
        for key in valid_fields:
            if key in kwargs and kwargs[key]:
                params[key] = kwargs[key]
        
        return await self._request("POST", "person/search", json=params)
    
    async def get_full_report(self, person_id: str) -> Dict:
        return await self._request("GET", f"person/{person_id}/full")
    
    async def get_mvr(self, dl_number: str, state: str) -> Dict:
        return await self._request("POST", "mvr", json={
            "dl_number": dl_number,
            "state": state,
            "include_history": True
        })
    
    async def get_criminal_record(self, person_id: str) -> Dict:
        return await self._request("GET", f"person/{person_id}/criminal")
    
    async def get_property_records(self, person_id: str) -> Dict:
        return await self._request("GET", f"person/{person_id}/property")
    
    async def get_relatives(self, person_id: str) -> Dict:
        return await self._request("GET", f"person/{person_id}/relatives")
    
    async def get_credit_header(self, ssn: str) -> Dict:
        return await self._request("POST", "credit/header", json={"ssn": ssn})
    
    async def close(self):
        """Close the HTTP client"""
        pass  # We'll handle this at the bot level

tlo = TLOClient(TLO_API_KEY)

# ==================== AUDIT LOG ====================
class AuditLogger:
    """Simple audit logging"""
    
    def __init__(self, log_file: str = "audit.log"):
        self.log_file = log_file
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                f.write("timestamp,user_id,username,action,query,result_count,ip\n")
    
    async def log(self, user_id: int, username: str, action: str, 
                  query: str, result_count: int = 0, ip: str = "unknown"):
        """Log an action to the audit file"""
        timestamp = datetime.now().isoformat()
        # Sanitize query to prevent CSV injection
        query_safe = query.replace('"', '""').replace('\n', ' ')
        
        log_entry = f'"{timestamp}",{user_id},"{username}","{action}","{query_safe}",{result_count},"{ip}"\n'
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

audit_logger = AuditLogger()

# ==================== AUTH MIDDLEWARE ====================
async def check_user(message: Message) -> bool:
    """Check if user is authorized"""
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    
    if user_id not in ALLOWED_USER_IDS:
        logger.warning(f"Unauthorized access attempt from {username} ({user_id})")
        await message.reply("⛔ Unauthorized access.")
        return False
    
    return True

# ==================== PARSING HELPER ====================
def parse_person_query(query: str) -> Dict[str, str]:
    """Parse name, DOB, SSN, DL from query string"""
    params = {}
    text = query.strip()
    
    # Detect SSN (###-##-####)
    ssn_pattern = r'\b\d{3}[-]?\d{2}[-]?\d{4}\b'
    ssn_match = re.search(ssn_pattern, text)
    if ssn_match:
        params['ssn'] = re.sub(r'[-]', '', ssn_match.group())
        text = text.replace(ssn_match.group(), '').strip()
    
    # Detect DOB (MM/DD/YYYY or MM-DD-YYYY)
    dob_patterns = [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2}\b'
    ]
    dob_match = None
    for pattern in dob_patterns:
        dob_match = re.search(pattern, text)
        if dob_match:
            break
    if dob_match:
        params['dob'] = dob_match.group()
        text = text.replace(dob_match.group(), '').strip()
    
    # Detect DL (state + 5-10 digit number)
    dl_pattern = r'\b([A-Z]{2})\s*(\d{5,10})\b'
    dl_match = re.search(dl_pattern, text)
    if dl_match:
        params['dl_state'] = dl_match.group(1)
        params['dl_number'] = dl_match.group(2)
        text = text.replace(dl_match.group(), '').strip()
    
    # Remaining text is name
    if text:
        name_parts = text.split()
        if len(name_parts) >= 2:
            params['first_name'] = name_parts[0]
            params['last_name'] = ' '.join(name_parts[1:])
        else:
            params['last_name'] = text
    
    return params

# ==================== FORMATTERS ====================
def format_person_info(data: Dict) -> str:
    person = data.get('person', {})
    demographics = person.get('demographics', {})
    identifiers = person.get('identifiers', {})
    contact = person.get('contact', {})
    employment = person.get('employment', {})
    education = person.get('education', {})
    
    text = f"""
👤 <b>PERSONAL INFORMATION</b>
{'=' * 40}

<b>Full Name:</b> {demographics.get('full_name', 'N/A')}
<b>AKA/Aliases:</b> {', '.join(person.get('aliases', [])) or 'N/A'}

<b>Date of Birth:</b> {demographics.get('dob', 'N/A')}
<b>Age:</b> {demographics.get('age', 'N/A')}
<b>Gender:</b> {demographics.get('gender', 'N/A')}
<b>Race:</b> {demographics.get('race', 'N/A')}

<b>SSN:</b> {identifiers.get('ssn', 'N/A')}
<b>Driver's License:</b> {identifiers.get('dl_number', 'N/A')}
<b>DL State:</b> {identifiers.get('dl_state', 'N/A')}
<b>DL Status:</b> {identifiers.get('dl_status', 'N/A')}

<b>Current Address:</b> 
{contact.get('address', 'N/A')}
{contact.get('city', '')} {contact.get('state', '')} {contact.get('zip', '')}
<b>Phone:</b> {contact.get('phone', 'N/A')}
<b>Email:</b> {contact.get('email', 'N/A')}

<b>Employment:</b>
<b>Employer:</b> {employment.get('employer', 'N/A')}
<b>Occupation:</b> {employment.get('occupation', 'N/A')}

<b>Confidence Score:</b> {data.get('confidence', 0)}%
"""
    return text

def format_mvr(data: Dict) -> str:
    text = f"""
🚗 <b>MOTOR VEHICLE REPORT</b>
{'=' * 40}

<b>Name:</b> {data.get('name', 'N/A')}
<b>DL Number:</b> {data.get('dl_number', 'N/A')}
<b>State:</b> {data.get('state', 'N/A')}
<b>Status:</b> {data.get('status', 'N/A')}
<b>License Class:</b> {data.get('class', 'N/A')}

<b>License History:</b>
"""
    for record in data.get('history', [])[:5]:
        text += f"  • {record.get('date', 'N/A')}: {record.get('action', 'N/A')}\n"
    
    if data.get('violations'):
        text += f"\n<b>Recent Violations:</b>\n"
        for violation in data.get('violations', [])[:5]:
            text += f"  • {violation.get('date', 'N/A')}: {violation.get('offense', 'N/A')}\n"
    
    return text

def format_criminal(data: Dict) -> str:
    text = f"""
⚖️ <b>CRIMINAL RECORD</b>
{'=' * 40}

<b>Felonies:</b>
"""
    for felony in data.get('felonies', [])[:5]:
        text += f"  ⚠️ {felony.get('offense', 'N/A')} ({felony.get('date', 'N/A')})\n"
    
    text += f"\n<b>Misdemeanors:</b>\n"
    for offense in data.get('misdemeanors', [])[:5]:
        text += f"  • {offense.get('offense', 'N/A')} ({offense.get('date', 'N/A')})\n"
    
    if data.get('warrants'):
        text += f"\n<b>Warrants:</b>\n"
        for warrant in data.get('warrants', []):
            text += f"  ⚠️ {warrant.get('type', 'N/A')} ({warrant.get('issued', 'N/A')})\n"
    
    return text

def format_property(data: Dict) -> str:
    text = f"""
🏠 <b>PROPERTY RECORDS</b>
{'=' * 40}

<b>Properties Owned:</b>
"""
    for prop in data.get('properties', [])[:5]:
        text += f"""
  📍 {prop.get('address', 'N/A')}
  • Type: {prop.get('type', 'N/A')}
  • Value: ${prop.get('value', 'N/A'):,}
  • Year Built: {prop.get('year_built', 'N/A')}
"""
    return text

def format_relatives(data: Dict) -> str:
    text = f"""
👨‍👩‍👧‍👦 <b>RELATIVES & ASSOCIATES</b>
{'=' * 40}

<b>Immediate Family:</b>
"""
    for relative in data.get('immediate_family', [])[:5]:
        text += f"  • {relative.get('name', 'N/A')} ({relative.get('relation', 'N/A')})\n"
    
    text += f"\n<b>Known Associates:</b>\n"
    for associate in data.get('associates', [])[:5]:
        text += f"  • {associate.get('name', 'N/A')}\n"
    
    return text

# ==================== SPLIT MESSAGE HELPER ====================
async def send_long_message(message: Message, text: str, title: str = ""):
    """Split long messages into parts with labels"""
    if len(text) <= 4096:
        await message.reply(text)
        return
    
    parts = [text[i:i+4096] for i in range(0, len(text), 4096)]
    for i, part in enumerate(parts, 1):
        header = f"📄 <b>{title}</b> (Part {i}/{len(parts)})\n\n"
        await message.reply(header + part)

# ==================== COMPLIANCE DISCLAIMER ====================
COMPLIANCE_NOTICE = """
<i>⚠️ <b>FCRA COMPLIANCE NOTICE</b></i>

This information is a <b>consumer report</b> under the Fair Credit Reporting Act (FCRA).

<b>You must have a permissible purpose</b> to obtain this report:
• Employment screening (with consent)
• Tenant screening (with consent)
• Insurance underwriting
• Government agency use
• Court order or subpoena

<b>You are required to:</b>
• Provide adverse action notice if applicable
• Maintain strict confidentiality
• Dispose of information securely

<i>Unauthorized use is a federal offense.</i>
"""

# ==================== BOT COMMANDS ====================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    if not await check_user(message):
        return
    
    await audit_logger.log(
        message.from_user.id,
        message.from_user.username or str(message.from_user.id),
        "start",
        "/start"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("🔍 Person Search", callback_data="person_search")],
            [InlineKeyboardButton("🚗 MVR Lookup", callback_data="mvr_lookup")],
            [InlineKeyboardButton("⚖️ Criminal Check", callback_data="criminal_check")],
            [InlineKeyboardButton("🏠 Property Records", callback_data="property_records")],
            [InlineKeyboardButton("👨‍👩‍👧‍👦 Find Relatives", callback_data="find_relatives")],
            [InlineKeyboardButton("📋 Compliance Info", callback_data="compliance")]
        ]
    )
    
    await message.reply(
        "🔍 <b>TLO PERSONAL INFORMATION LOOKUP</b>\n\n"
        "Select what you want to search for:\n"
        "• Person Search - Name, DOB, SSN\n"
        "• MVR - Driver's license history\n"
        "• Criminal - Court records\n"
        "• Property - Real estate owned\n"
        "• Relatives - Family & associates\n\n"
        "<i>All searches are logged and audited.</i>",
        reply_markup=keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    if not await check_user(message):
        return
    
    await message.reply(
        "📖 <b>Help & Commands</b>\n\n"
        "/start - Main menu\n"
        "/search <query> - Search person\n"
        "/mvr <DL#> <state> - MVR lookup\n"
        "/criminal <name> - Criminal check\n"
        "/property <name> - Property records\n"
        "/relatives <name> - Find relatives\n"
        "/compliance - FCRA compliance info\n"
        "/cancel - Cancel current operation\n"
        "/help - This message\n\n"
        "<i>All searches are monitored and logged.</i>"
    )

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.reply("✅ Cancelled current operation.")
    else:
        await message.reply("❌ Nothing to cancel.")

@dp.message(Command("compliance"))
async def cmd_compliance(message: Message):
    if not await check_user(message):
        return
    
    await message.reply(COMPLIANCE_NOTICE)

# ==================== PERSON SEARCH ====================
@dp.callback_query(lambda c: c.data == "person_search")
async def callback_person_search(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "👤 <b>PERSON SEARCH</b>\n\n"
        "Please provide the person's information.\n\n"
        "Examples:\n"
        "<code>John Doe</code>\n"
        "<code>John Doe 01/15/1980</code>\n"
        "<code>John Doe CA DL1234567</code>\n"
        "<code>John Doe 123-45-6789</code>\n\n"
        "Type /cancel to stop.",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_PERSON_SEARCH)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_PERSON_SEARCH)
async def process_person_search(message: Message, state: FSMContext):
    await handle_person_search(message, state)

async def handle_person_search(message: Message, state: FSMContext):
    query = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    
    params = parse_person_query(query)
    
    if not params:
        await message.reply("❌ I couldn't parse your input. Please provide at least a name.")
        return
    
    await audit_logger.log(user_id, username, "person_search", query, 0)
    await message.reply("⏳ Searching TLO database...")
    
    try:
        result = await tlo.person_search(**params)
        
        if not result.get('found'):
            await message.reply("❌ No matching records found.")
            await state.clear()
            return
        
        person_id = result['person_id']
        full_report = await tlo.get_full_report(person_id)
        
        formatted = format_person_info(full_report)
        await send_long_message(message, formatted, "Personal Information")
        
        # Additional options
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton("🚗 Get MVR", callback_data=f"mvr_{person_id}")],
                [InlineKeyboardButton("⚖️ Criminal Check", callback_data=f"criminal_{person_id}")],
                [InlineKeyboardButton("🏠 Property Records", callback_data=f"property_{person_id}")],
                [InlineKeyboardButton("👨‍👩‍👧‍👦 Relatives", callback_data=f"relatives_{person_id}")]
            ]
        )
        await message.reply(
            "📋 <b>Additional Reports Available:</b>",
            reply_markup=keyboard
        )
        
        await audit_logger.log(user_id, username, "person_search_result", query, 1)
        
    except Exception as e:
        logger.error(f"Person search error: {e}")
        await message.reply(f"❌ Error: {str(e)}")
    
    await state.clear()

# ==================== MVR LOOKUP ====================
@dp.callback_query(lambda c: c.data == "mvr_lookup")
async def callback_mvr(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "🚗 <b>MVR LOOKUP</b>\n\n"
        "Please send the driver's license number and state.\n\n"
        "Example: <code>D1234567 CA</code>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_DL)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_DL)
async def process_mvr(message: Message, state: FSMContext):
    text = message.text.strip().upper()
    parts = text.split()
    
    if len(parts) < 2:
        await message.reply("❌ Please provide DL number and state.\nExample: <code>D1234567 CA</code>")
        return
    
    dl_number = parts[0]
    dl_state = parts[1]
    
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    
    await audit_logger.log(user_id, username, "mvr_lookup", f"{dl_number} {dl_state}", 0)
    await message.reply("⏳ Retrieving Motor Vehicle Report...")
    
    try:
        result = await tlo.get_mvr(dl_number, dl_state)
        
        if not result.get('found'):
            await message.reply("❌ No MVR records found.")
            await state.clear()
            return
        
        formatted = format_mvr(result)
        await send_long_message(message, formatted, "MVR Report")
        await audit_logger.log(user_id, username, "mvr_result", f"{dl_number} {dl_state}", 1)
            
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
    
    await state.clear()

# ==================== CRIMINAL CHECK ====================
@dp.callback_query(lambda c: c.data == "criminal_check")
async def callback_criminal(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "⚖️ <b>CRIMINAL RECORD CHECK</b>\n\n"
        "Please send the person's full name and DOB.\n\n"
        "Example: <code>John Doe 01/15/1980</code>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_NAME)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_NAME)
async def process_criminal(message: Message, state: FSMContext):
    await handle_criminal_search(message, state)

async def handle_criminal_search(message: Message, state: FSMContext):
    text = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    
    params = parse_person_query(text)
    
    await audit_logger.log(user_id, username, "criminal_search", text, 0)
    await message.reply("⏳ Checking criminal records...")
    
    try:
        result = await tlo.person_search(**params)
        
        if not result.get('found'):
            await message.reply("❌ No matching records found.")
            await state.clear()
            return
        
        person_id = result['person_id']
        criminal = await tlo.get_criminal_record(person_id)
        
        formatted = format_criminal(criminal)
        await send_long_message(message, formatted, "Criminal Record")
        await audit_logger.log(user_id, username, "criminal_result", text, 1)
        
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
    
    await state.clear()

# ==================== PROPERTY RECORDS ====================
@dp.callback_query(lambda c: c.data == "property_records")
async def callback_property(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "🏠 <b>PROPERTY RECORDS</b>\n\n"
        "Please send the person's name or address to search.\n\n"
        "Example: <code>John Doe</code>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_PROPERTY_SEARCH)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_PROPERTY_SEARCH)
async def process_property(message: Message, state: FSMContext):
    query = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    
    await audit_logger.log(user_id, username, "property_search", query, 0)
    await message.reply("⏳ Searching property records...")
    
    try:
        params = parse_person_query(query)
        result = await tlo.person_search(**params)
        
        if not result.get('found'):
            await message.reply("❌ No records found.")
            await state.clear()
            return
        
        person_id = result['person_id']
        property_records = await tlo.get_property_records(person_id)
        
        formatted = format_property(property_records)
        await send_long_message(message, formatted, "Property Records")
        await audit_logger.log(user_id, username, "property_result", query, 1)
            
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
    
    await state.clear()

# ==================== FIND RELATIVES ====================
@dp.callback_query(lambda c: c.data == "find_relatives")
async def callback_relatives(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "👨‍👩‍👧‍👦 <b>FIND RELATIVES</b>\n\n"
        "Please send the person's name and DOB.\n\n"
        "Example: <code>John Doe 01/15/1980</code>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_NAME)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_NAME)
async def process_relatives(message: Message, state: FSMContext):
    text = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    
    params = parse_person_query(text)
    
    await audit_logger.log(user_id, username, "relatives_search", text, 0)
    await message.reply("⏳ Finding relatives...")
    
    try:
        result = await tlo.person_search(**params)
        
        if not result.get('found'):
            await message.reply("❌ No matching records found.")
            await state.clear()
            return
        
        person_id = result['person_id']
        relatives = await tlo.get_relatives(person_id)
        
        formatted = format_relatives(relatives)
        await send_long_message(message, formatted, "Relatives Report")
        await audit_logger.log(user_id, username, "relatives_result", text, 1)
        
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
    
    await state.clear()

# ==================== ADDITIONAL REPORT CALLBACKS ====================
@dp.callback_query(lambda c: c.data.startswith("mvr_"))
async def callback_mvr_result(callback: types.CallbackQuery):
    person_id = callback.data.split("_")[1]
    await callback.message.reply(f"⏳ Retrieving MVR for person ID: {person_id}")
    # This would need actual implementation with the person's DL info
    await callback.answer("MVR lookup requires DL number and state")

@dp.callback_query(lambda c: c.data.startswith("criminal_"))
async def callback_criminal_result(callback: types.CallbackQuery):
    person_id = callback.data.split("_")[1]
    user_id = callback.from_user.id
    username = callback.from_user.username or str(user_id)
    
    await audit_logger.log(user_id, username, "criminal_person_id", person_id, 0)
    await callback.message.reply("⏳ Retrieving criminal records...")
    
    try:
        criminal = await tlo.get_criminal_record(person_id)
        formatted = format_criminal(criminal)
        await send_long_message(callback.message, formatted, "Criminal Record")
        await audit_logger.log(user_id, username, "criminal_person_result", person_id, 1)
    except Exception as e:
        await callback.message.reply(f"❌ Error: {str(e)}")
    
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("property_"))
async def callback_property_result(callback: types.CallbackQuery):
    person_id = callback.data.split("_")[1]
    user_id = callback.from_user.id
    username = callback.from_user.username or str(user_id)
    
    await audit_logger.log(user_id, username, "property_person_id", person_id, 0)
    await callback.message.reply("⏳ Retrieving property records...")
    
    try:
        property_records = await tlo.get_property_records(person_id)
        formatted = format_property(property_records)
        await send_long_message(callback.message, formatted, "Property Records")
        await audit_logger.log(user_id, username, "property_person_result", person_id, 1)
    except Exception as e:
        await callback.message.reply(f"❌ Error: {str(e)}")
    
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("relatives_"))
async def callback_relatives_result(callback: types.CallbackQuery):
    person_id = callback.data.split("_")[1]
    user_id = callback.from_user.id
    username = callback.from_user.username or str(user_id)
    
    await audit_logger.log(user_id, username, "relatives_person_id", person_id, 0)
    await callback.message.reply("⏳ Retrieving relatives...")
    
    try:
        relatives = await tlo.get_relatives(person_id)
        formatted = format_relatives(relatives)
        await send_long_message(callback.message, formatted, "Relatives Report")
        await audit_logger.log(user_id, username, "relatives_person_result", person_id, 1)
    except Exception as e:
        await callback.message.reply(f"❌ Error: {str(e)}")
    
    await callback.answer()

# ==================== COMPLIANCE CALLBACK ====================
@dp.callback_query(lambda c: c.data == "compliance")
async def callback_compliance(callback: types.CallbackQuery):
    await callback.message.reply(COMPLIANCE_NOTICE)
    await callback.answer()

# ==================== MAIN ====================
async def main():
    logger.info("🚀 Starting TLO Personal Info Bot...")
    logger.info(f"👥 Allowed users: {ALLOWED_USER_IDS}")
    logger.info(f"📊 Rate limit: {RATE_LIMIT} requests/second")
    
    try:
        await bot.delete_webhook()
        await dp.start_polling(bot, allowed_updates=types.UpdateType.MESSAGE)
    finally:
        await http_client.aclose()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")http_client = httpx.AsyncClient(timeout=60.0)  # Longer timeout for TLO

# ==================== STATES ====================
class LookupStates(StatesGroup):
    WAITING_FOR_NAME = State()
    WAITING_FOR_DOB = State()
    WAITING_FOR_SSN = State()
    WAITING_FOR_DL = State()
    WAITING_FOR_SEARCH = State()

# ==================== TLO API CLIENT ====================
class TLOClient:
    """Complete TLO API Client"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = TLO_API_URL
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def person_search(self, **kwargs) -> Dict:
        """Search person by name, DOB, SSN, etc."""
        endpoint = f"{self.base_url}/person/search"
        
        # Build query parameters
        params = {}
        if kwargs.get('first_name'):
            params['first_name'] = kwargs['first_name']
        if kwargs.get('last_name'):
            params['last_name'] = kwargs['last_name']
        if kwargs.get('middle_name'):
            params['middle_name'] = kwargs['middle_name']
        if kwargs.get('dob'):
            params['dob'] = kwargs['dob']
        if kwargs.get('ssn'):
            params['ssn'] = kwargs['ssn']
        if kwargs.get('dl_number'):
            params['dl_number'] = kwargs['dl_number']
        if kwargs.get('dl_state'):
            params['dl_state'] = kwargs['dl_state']
        if kwargs.get('address'):
            params['address'] = kwargs['address']
        if kwargs.get('city'):
            params['city'] = kwargs['city']
        if kwargs.get('state'):
            params['state'] = kwargs['state']
        if kwargs.get('zip'):
            params['zip'] = kwargs['zip']
        if kwargs.get('phone'):
            params['phone'] = kwargs['phone']
        if kwargs.get('email'):
            params['email'] = kwargs['email']
        
        response = await http_client.post(
            endpoint,
            json=params,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    async def get_full_report(self, person_id: str) -> Dict:
        """Get complete TLO report"""
        endpoint = f"{self.base_url}/person/{person_id}/full"
        response = await http_client.get(
            endpoint,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    async def get_mvr(self, dl_number: str, state: str) -> Dict:
        """Get Motor Vehicle Report"""
        endpoint = f"{self.base_url}/mvr"
        response = await http_client.post(
            endpoint,
            json={
                "dl_number": dl_number,
                "state": state,
                "include_history": True
            },
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    async def get_criminal_record(self, person_id: str) -> Dict:
        """Get criminal record check"""
        endpoint = f"{self.base_url}/person/{person_id}/criminal"
        response = await http_client.get(
            endpoint,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    async def get_credit_header(self, ssn: str) -> Dict:
        """Get credit header information"""
        endpoint = f"{self.base_url}/credit/header"
        response = await http_client.post(
            endpoint,
            json={"ssn": ssn},
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    async def get_property_records(self, person_id: str) -> Dict:
        """Get property ownership records"""
        endpoint = f"{self.base_url}/person/{person_id}/property"
        response = await http_client.get(
            endpoint,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    async def get_relatives(self, person_id: str) -> Dict:
        """Get relatives and associates"""
        endpoint = f"{self.base_url}/person/{person_id}/relatives"
        response = await http_client.get(
            endpoint,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

tlo = TLOClient(TLO_API_KEY)

# ==================== AUTH MIDDLEWARE ====================
async def check_user(message: Message) -> bool:
    """Check if user is authorized"""
    if message.from_user.id not in ALLOWED_USER_IDS:
        await message.reply("⛔ Unauthorized access.")
        return False
    return True

# ==================== FORMATTERS ====================
def format_person_info(data: Dict) -> str:
    """Format personal information"""
    person = data.get('person', {})
    demographics = person.get('demographics', {})
    identifiers = person.get('identifiers', {})
    contact = person.get('contact', {})
    employment = person.get('employment', {})
    education = person.get('education', {})
    
    text = f"""
👤 <b>PERSONAL INFORMATION</b>
{'=' * 40}

<b>Full Name:</b> {demographics.get('full_name', 'N/A')}
<b>AKA/Aliases:</b> {', '.join(person.get('aliases', []))}

<b>Date of Birth:</b> {demographics.get('dob', 'N/A')}
<b>Age:</b> {demographics.get('age', 'N/A')}
<b>Gender:</b> {demographics.get('gender', 'N/A')}
<b>Race:</b> {demographics.get('race', 'N/A')}
<b>Height:</b> {demographics.get('height', 'N/A')}
<b>Weight:</b> {demographics.get('weight', 'N/A')}
<b>Eye Color:</b> {demographics.get('eye_color', 'N/A')}
<b>Hair Color:</b> {demographics.get('hair_color', 'N/A')}

<b>SSN:</b> {identifiers.get('ssn', 'N/A')}
<b>SSN Issued:</b> {identifiers.get('ssn_issued', 'N/A')}
<b>Driver's License:</b> {identifiers.get('dl_number', 'N/A')}
<b>DL State:</b> {identifiers.get('dl_state', 'N/A')}
<b>DL Class:</b> {identifiers.get('dl_class', 'N/A')}
<b>DL Status:</b> {identifiers.get('dl_status', 'N/A')}
<b>DL Expiration:</b> {identifiers.get('dl_expiration', 'N/A')}
<b>Passport:</b> {identifiers.get('passport', 'N/A')}

<b>Current Address:</b> 
{contact.get('address', 'N/A')}
{contact.get('city', '')} {contact.get('state', '')} {contact.get('zip', '')}
<b>Phone:</b> {contact.get('phone', 'N/A')}
<b>Email:</b> {contact.get('email', 'N/A')}

<b>Previous Addresses:</b>
"""
    for addr in contact.get('previous_addresses', []):
        text += f"  • {addr.get('address')}, {addr.get('city')}, {addr.get('state')} {addr.get('zip')}\n"
    
    text += f"""
<b>Employment:</b>
<b>Employer:</b> {employment.get('employer', 'N/A')}
<b>Occupation:</b> {employment.get('occupation', 'N/A')}
<b>Income:</b> {employment.get('income', 'N/A')}
<b>Employment Status:</b> {employment.get('status', 'N/A')}

<b>Education:</b>
<b>School:</b> {education.get('school', 'N/A')}
<b>Degree:</b> {education.get('degree', 'N/A')}
<b>Graduation Year:</b> {education.get('year', 'N/A')}

<b>Confidence Score:</b> {data.get('confidence', 0)}%
<b>Data Sources:</b> {', '.join(data.get('sources', []))}
"""
    return text

def format_mvr(data: Dict) -> str:
    """Format Motor Vehicle Report"""
    text = f"""
🚗 <b>MOTOR VEHICLE REPORT</b>
{'=' * 40}

<b>Driver Information:</b>
<b>Name:</b> {data.get('name', 'N/A')}
<b>DL Number:</b> {data.get('dl_number', 'N/A')}
<b>State:</b> {data.get('state', 'N/A')}
<b>Status:</b> {data.get('status', 'N/A')}
<b>License Class:</b> {data.get('class', 'N/A')}
<b>Endorsements:</b> {', '.join(data.get('endorsements', []))}
<b>Restrictions:</b> {', '.join(data.get('restrictions', []))}

<b>License History:</b>
"""
    for record in data.get('history', []):
        text += f"""
  📅 {record.get('date', 'N/A')}
  • Action: {record.get('action', 'N/A')}
  • Reason: {record.get('reason', 'N/A')}
  • Points: {record.get('points', 'N/A')}
"""
    
    text += f"""
<b>Accidents:</b>
"""
    for accident in data.get('accidents', []):
        text += f"""
  📅 {accident.get('date', 'N/A')}
  • Type: {accident.get('type', 'N/A')}
  • Severity: {accident.get('severity', 'N/A')}
  • Injuries: {accident.get('injuries', 'N/A')}
  • Fatalities: {accident.get('fatalities', 'N/A')}
"""
    
    text += f"""
<b>Violations:</b>
"""
    for violation in data.get('violations', []):
        text += f"""
  📅 {violation.get('date', 'N/A')}
  • Offense: {violation.get('offense', 'N/A')}
  • Location: {violation.get('location', 'N/A')}
  • Fine: ${violation.get('fine', 0)}
"""
    return text

def format_criminal(data: Dict) -> str:
    """Format criminal record"""
    text = f"""
⚖️ <b>CRIMINAL RECORD</b>
{'=' * 40}

<b>Felonies:</b>
"""
    for felony in data.get('felonies', []):
        text += f"""
  ⚠️ {felony.get('offense', 'N/A')}
  • Date: {felony.get('date', 'N/A')}
  • Location: {felony.get('location', 'N/A')}
  • Sentence: {felony.get('sentence', 'N/A')}
  • Status: {felony.get('status', 'N/A')}
"""
    
    text += f"""
<b>Misdemeanors:</b>
"""
    for offense in data.get('misdemeanors', []):
        text += f"""
  • {offense.get('offense', 'N/A')}
  • Date: {offense.get('date', 'N/A')}
  • Location: {offense.get('location', 'N/A')}
"""
    
    text += f"""
<b>Warrants:</b>
"""
    for warrant in data.get('warrants', []):
        text += f"""
  ⚠️ {warrant.get('type', 'N/A')}
  • Issued: {warrant.get('issued', 'N/A')}
  • Issuing Agency: {warrant.get('agency', 'N/A')}
  • Status: {warrant.get('status', 'N/A')}
"""
    return text

def format_property(data: Dict) -> str:
    """Format property records"""
    text = f"""
🏠 <b>PROPERTY RECORDS</b>
{'=' * 40)

<b>Properties Owned:</b>
"""
    for prop in data.get('properties', []):
        text += f"""
  📍 {prop.get('address', 'N/A')}
  • Type: {prop.get('type', 'N/A')}
  • Value: ${prop.get('value', 'N/A'):,}
  • Year Built: {prop.get('year_built', 'N/A')}
  • Square Feet: {prop.get('sqft', 'N/A')}
  • Bedrooms: {prop.get('bedrooms', 'N/A')}
  • Bathrooms: {prop.get('bathrooms', 'N/A')}
  • Acquired: {prop.get('acquired', 'N/A')}
  • Mortgage Amount: ${prop.get('mortgage', 'N/A'):,}
"""
    return text

def format_relatives(data: Dict) -> str:
    """Format relatives and associates"""
    text = f"""
👨‍👩‍👧‍👦 <b>RELATIVES & ASSOCIATES</b>
{'=' * 40}

<b>Immediate Family:</b>
"""
    for relative in data.get('immediate_family', []):
        text += f"""
  • {relative.get('name', 'N/A')} ({relative.get('relation', 'N/A')})
  • DOB: {relative.get('dob', 'N/A')}
  • Address: {relative.get('address', 'N/A')}
  • Phone: {relative.get('phone', 'N/A')}
"""
    
    text += f"""
<b>Extended Family:</b>
"""
    for relative in data.get('extended_family', []):
        text += f"  • {relative.get('name', 'N/A')} ({relative.get('relation', 'N/A')})\n"
    
    text += f"""
<b>Known Associates:</b>
"""
    for associate in data.get('associates', []):
        text += f"""
  • {associate.get('name', 'N/A')}
  • Relationship: {associate.get('relationship', 'N/A')}
  • Address: {associate.get('address', 'N/A')}
"""
    return text

# ==================== BOT COMMANDS ====================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    if not await check_user(message):
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("🔍 Person Search", callback_data="person_search")],
            [InlineKeyboardButton("🚗 MVR Lookup", callback_data="mvr_lookup")],
            [InlineKeyboardButton("⚖️ Criminal Check", callback_data="criminal_check")],
            [InlineKeyboardButton("🏠 Property Records", callback_data="property_records")],
            [InlineKeyboardButton("👨‍👩‍👧‍👦 Find Relatives", callback_data="find_relatives")]
        ]
    )
    
    await message.reply(
        "🔍 <b>TLO PERSONAL INFORMATION LOOKUP</b>\n\n"
        "Select what you want to search for:\n"
        "• Person Search - Name, DOB, SSN\n"
        "• MVR - Driver's license history\n"
        "• Criminal - Court records\n"
        "• Property - Real estate owned\n"
        "• Relatives - Family & associates\n\n"
        "<i>All searches are logged and audited.</i>",
        reply_markup=keyboard
    )

# ==================== PERSON SEARCH ====================
@dp.callback_query(lambda c: c.data == "person_search")
async def callback_person_search(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "👤 <b>PERSON SEARCH</b>\n\n"
        "I need at least a name to search.\n"
        "You can also provide additional details.\n\n"
        "Examples:\n"
        "<code>John Doe</code>\n"
        "<code>John Doe 01/15/1980</code>\n"
        "<code>John Doe CA DL1234567</code>\n"
        "<code>John Doe SSN 123-45-6789</code>\n\n"
        "Or type /cancel to stop.",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_SEARCH)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_SEARCH)
async def process_person_search(message: Message, state: FSMContext):
    query = message.text.strip()
    
    # Parse input
    params = {}
    parts = query.split()
    
    # Try to detect SSN
    import re
    ssn_pattern = r'\d{3}[-]?\d{2}[-]?\d{4}'
    ssn_match = re.search(ssn_pattern, query)
    if ssn_match:
        params['ssn'] = ssn_match.group()
        query = query.replace(ssn_match.group(), '').strip()
    
    # Try to detect DOB
    dob_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
    dob_match = re.search(dob_pattern, query)
    if dob_match:
        params['dob'] = dob_match.group()
        query = query.replace(dob_match.group(), '').strip()
    
    # Try to detect DL
    dl_pattern = r'[A-Z]{2}\s*\d{5,10}'
    dl_match = re.search(dl_pattern, query)
    if dl_match:
        params['dl_number'] = dl_match.group().replace(' ', '')
        # Try to extract state
        state_match = re.search(r'([A-Z]{2})\s*\d+', query)
        if state_match:
            params['dl_state'] = state_match.group(1)
        query = query.replace(dl_match.group(), '').strip()
    
    # Remaining is name
    if query:
        name_parts = query.split()
        if len(name_parts) >= 2:
            params['first_name'] = name_parts[0]
            params['last_name'] = ' '.join(name_parts[1:])
        elif len(name_parts) == 1:
            params['last_name'] = name_parts[0]
    
    if not params:
        await message.reply("❌ I couldn't parse your input. Please provide at least a name.")
        await state.clear()
        return
    
    await message.reply("⏳ Searching TLO database...")
    
    try:
        # Perform search
        result = await tlo.person_search(**params)
        
        if not result.get('found'):
            await message.reply("❌ No matching records found.")
            await state.clear()
            return
        
        # Get full report
        person_id = result['person_id']
        full_report = await tlo.get_full_report(person_id)
        
        # Format and send
        formatted = format_person_info(full_report)
        
        # Split if too long
        if len(formatted) > 4096:
            parts = [formatted[i:i+4096] for i in range(0, len(formatted), 4096)]
            for part in parts:
                await message.reply(part)
        else:
            await message.reply(formatted)
        
        # Additional options
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton("🚗 Get MVR", callback_data=f"mvr_{person_id}")],
                [InlineKeyboardButton("⚖️ Criminal Check", callback_data=f"criminal_{person_id}")],
                [InlineKeyboardButton("🏠 Property Records", callback_data=f"property_{person_id}")],
                [InlineKeyboardButton("👨‍👩‍👧‍👦 Relatives", callback_data=f"relatives_{person_id}")]
            ]
        )
        await message.reply(
            "📋 <b>Additional Reports Available:</b>",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Person search error: {e}")
        await message.reply(f"❌ Error: {str(e)}")
    
    await state.clear()

# ==================== MVR LOOKUP ====================
@dp.callback_query(lambda c: c.data == "mvr_lookup")
async def callback_mvr(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "🚗 <b>MVR LOOKUP</b>\n\n"
        "Please send the driver's license number and state.\n\n"
        "Example: <code>D1234567 CA</code>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_DL)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_DL)
async def process_mvr(message: Message, state: FSMContext):
    text = message.text.strip().upper()
    parts = text.split()
    
    if len(parts) < 2:
        await message.reply("❌ Please provide DL number and state.\nExample: <code>D1234567 CA</code>")
        return
    
    dl_number = parts[0]
    state = parts[1]
    
    await message.reply("⏳ Retrieving Motor Vehicle Report...")
    
    try:
        result = await tlo.get_mvr(dl_number, state)
        
        if not result.get('found'):
            await message.reply("❌ No MVR records found.")
            await state.clear()
            return
        
        formatted = format_mvr(result)
        
        if len(formatted) > 4096:
            parts = [formatted[i:i+4096] for i in range(0, len(formatted), 4096)]
            for part in parts:
                await message.reply(part)
        else:
            await message.reply(formatted)
            
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
    
    await state.clear()

# ==================== CRIMINAL CHECK ====================
@dp.callback_query(lambda c: c.data == "criminal_check")
async def callback_criminal(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "⚖️ <b>CRIMINAL RECORD CHECK</b>\n\n"
        "Please send the person's full name and DOB.\n\n"
        "Example: <code>John Doe 01/15/1980</code>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_NAME)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_NAME)
async def process_criminal(message: Message, state: FSMContext):
    text = message.text.strip()
    
    # Parse name and DOB
    import re
    dob_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
    dob_match = re.search(dob_pattern, text)
    
    name = text
    dob = None
    if dob_match:
        dob = dob_match.group()
        name = text.replace(dob_match.group(), '').strip()
    
    await message.reply("⏳ Checking criminal records...")
    
    try:
        # Search person first
        params = {}
        name_parts = name.split()
        if len(name_parts) >= 2:
            params['first_name'] = name_parts[0]
            params['last_name'] = ' '.join(name_parts[1:])
        else:
            params['last_name'] = name
        
        if dob:
            params['dob'] = dob
        
        result = await tlo.person_search(**params)
        
        if not result.get('found'):
            await message.reply("❌ No matching records found.")
            await state.clear()
            return
        
        person_id = result['person_id']
        criminal = await tlo.get_criminal_record(person_id)
        
        if not criminal.get('found'):
            await message.reply("✅ No criminal records found.")
            await state.clear()
            return
        
        formatted = format_criminal(criminal)
        await message.reply(formatted)
        
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
    
    await state.clear()

# ==================== PROPERTY RECORDS ====================
@dp.callback_query(lambda c: c.data == "property_records")
async def callback_property(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "🏠 <b>PROPERTY RECORDS</b>\n\n"
        "Please send the person's name or address to search.\n\n"
        "Example: <code>John Doe</code>\n"
        "Example: <code>123 Main St Los Angeles CA</code>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_SEARCH)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_SEARCH)
async def process_property(message: Message, state: FSMContext):
    query = message.text.strip()
    
    await message.reply("⏳ Searching property records...")
    
    try:
        # Search by name or address
        result = await tlo.person_search(query=query)
        
        if not result.get('found'):
            await message.reply("❌ No records found.")
            await state.clear()
            return
        
        person_id = result['person_id']
        property_records = await tlo.get_property_records(person_id)
        
        if not property_records.get('found'):
            await message.reply("❌ No property records found.")
            await state.clear()
            return
        
        formatted = format_property(property_records)
        
        if len(formatted) > 4096:
            parts = [formatted[i:i+4096] for i in range(0, len(formatted), 4096)]
            for part in parts:
                await message.reply(part)
        else:
            await message.reply(formatted)
            
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
    
    await state.clear()

# ==================== FIND RELATIVES ====================
@dp.callback_query(lambda c: c.data == "find_relatives")
async def callback_relatives(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.reply(
        "👨‍👩‍👧‍👦 <b>FIND RELATIVES</b>\n\n"
        "Please send the person's name and DOB.\n\n"
        "Example: <code>John Doe 01/15/1980</code>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(LookupStates.WAITING_FOR_NAME)
    await callback.answer()

@dp.message(LookupStates.WAITING_FOR_NAME)
async def process_relatives(message: Message, state: FSMContext):
    text = message.text.strip()
    
    # Parse name and DOB
    import re
    dob_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
    dob_match = re.search(dob_pattern, text)
    
    name = text
    dob = None
    if dob_match:
        dob = dob_match.group()
        name = text.replace(dob_match.group(), '').strip()
    
    await message.reply("⏳ Finding relatives...")
    
    try:
        # Search person
        params = {}
        name_parts = name.split()
        if len(name_parts) >= 2:
            params['first_name'] = name_parts[0]
            params['last_name'] = ' '.join(name_parts[1:])
        else:
            params['last_name'] = name
        
        if dob:
            params['dob'] = dob
        
        result = await tlo.person_search(**params)
        
        if not result.get('found'):
            await message.reply("❌ No matching records found.")
            await state.clear()
            return
        
        person_id = result['person_id']
        relatives = await tlo.get_relatives(person_id)
        
        if not relatives.get('found'):
            await message.reply("❌ No relatives found.")
            await state.clear()
            return
        
        formatted = format_relatives(relatives)
        await message.reply(formatted)
        
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
    
    await state.clear()

# ==================== CANCEL HANDLER ====================
@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.reply("✅ Cancelled current operation.")
    else:
        await message.reply("❌ Nothing to cancel.")

# ==================== HELP ====================
@dp.message(Command("help"))
async def cmd_help(message: Message):
    if not await check_user(message):
        return
    
    await message.reply(
        "📖 <b>Help & Commands</b>\n\n"
        "/start - Main menu\n"
        "/search - Search person\n"
        "/mvr - MVR lookup\n"
        "/criminal - Criminal check\n"
        "/property - Property records\n"
        "/relatives - Find relatives\n"
        "/cancel - Cancel current operation\n"
        "/help - This message\n\n"
        "<i>All searches are monitored and logged.</i>"
    )

# ==================== MAIN ====================
async def main():
    logger.info("🚀 Starting TLO Personal Info Bot...")
    logger.info(f"👥 Allowed users: {ALLOWED_USER_IDS}")
    
    await bot.delete_webhook()
    await dp.start_polling(bot, allowed_updates=types.UpdateType.MESSAGE)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    finally:
        http_client.close()
user_data = {}

# ===== COMMAND HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"document": DEFAULT_DOCUMENT.copy()}
    
    welcome = """
🤖 *Nested Lookup Bot*

*Commands:*
🔍 `/lookup <key>` - Find a key
📋 `/keys` - Show all keys
📄 `/view` - View document
✏️ `/update <key> <value>` - Update a key
🗑️ `/delete <key>` - Delete a key
🔄 `/reset` - Reset document
📊 `/stats` - Show statistics
    """
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    doc = user_data[user_id]["document"]
    formatted = json.dumps(doc, indent=2, ensure_ascii=False)
    if len(formatted) > 4000:
        formatted = formatted[:4000] + "\n... (truncated)"
    
    await update.message.reply_text(f"```json\n{formatted}\n```", parse_mode='Markdown')

async def lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /lookup <key>\nExample: /lookup build_version")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    key = context.args[0]
    doc = user_data[user_id]["document"]
    
    try:
        from nested_lookup import nested_lookup
        results = nested_lookup(key, doc)
        
        if not results:
            await update.message.reply_text(f"Key '{key}' not found.")
            return
        
        response = f"🔍 Found {len(results)} result(s):\n\n"
        for i, val in enumerate(results[:10], 1):
            response += f"{i}. `{str(val)[:50]}`\n"
        if len(results) > 10:
            response += f"\n... and {len(results) - 10} more"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def show_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    doc = user_data[user_id]["document"]
    
    try:
        from nested_lookup import get_all_keys
        all_keys = get_all_keys(doc)
        keys_list = sorted(list(all_keys))
        
        if not keys_list:
            await update.message.reply_text("No keys found.")
            return
        
        response = f"📋 *All Keys:* ({len(keys_list)} total)\n\n"
        response += "\n".join([f"• `{k}`" for k in keys_list[:30]])
        if len(keys_list) > 30:
            response += f"\n\n... and {len(keys_list) - 30} more"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def update_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /update <key> <new_value>\nExample: /update model_name 'MacBook Air'")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    key = context.args[0]
    new_value = " ".join(context.args[1:])
    
    try:
        from nested_lookup import nested_lookup, nested_update
        doc = user_data[user_id]["document"]
        old_count = len(nested_lookup(key, doc))
        
        if old_count == 0:
            await update.message.reply_text(f"Key '{key}' not found.")
            return
        
        nested_update(doc, key, new_value, in_place=True, treat_as_element=True)
        user_data[user_id]["document"] = doc
        
        await update.message.reply_text(f"✅ Updated '{key}' {old_count} time(s).")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def delete_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /delete <key>\nExample: /delete memory")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    key = context.args[0]
    
    try:
        from nested_lookup import nested_lookup, nested_delete
        doc = user_data[user_id]["document"]
        old_count = len(nested_lookup(key, doc))
        
        if old_count == 0:
            await update.message.reply_text(f"Key '{key}' not found.")
            return
        
        nested_delete(doc, key, in_place=True)
        user_data[user_id]["document"] = doc
        
        await update.message.reply_text(f"🗑️ Deleted '{key}' {old_count} time(s).")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    user_data[user_id]["document"] = DEFAULT_DOCUMENT.copy()
    await update.message.reply_text("🔄 Document reset to default.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    doc = user_data[user_id]["document"]
    
    try:
        from nested_lookup import get_all_keys
        all_keys = get_all_keys(doc)
        
        response = f"""
📊 *Document Statistics*

• Total unique keys: `{len(all_keys)}`
• Document size: `{len(json.dumps(doc))}` characters
"""
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# ===== MAIN =====

def main():
    logger.info("Starting bot...")
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("view", view))
    app.add_handler(CommandHandler("lookup", lookup))
    app.add_handler(CommandHandler("keys", show_keys))
    app.add_handler(CommandHandler("update", update_key))
    app.add_handler(CommandHandler("delete", delete_key))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("stats", stats))
    
    webhook_url = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
    
    if webhook_url:
        logger.info(f"Running in webhook mode on port {PORT}")
        logger.info(f"Webhook URL: https://{webhook_url}/webhook")
        
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=f"https://{webhook_url}/webhook"
        )
    else:
        logger.info("Running in polling mode")
        app.run_polling()

if __name__ == "__main__":
    main()
user_data = {}

# ===== COMMAND HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"document": DEFAULT_DOCUMENT.copy()}
    
    welcome = """
🤖 *Nested Lookup Bot*

*Commands:*
🔍 `/lookup <key>` - Find a key
📋 `/keys` - Show all keys
📄 `/view` - View document
✏️ `/update <key> <value>` - Update a key
🗑️ `/delete <key>` - Delete a key
🔄 `/reset` - Reset document
📊 `/stats` - Show statistics
    """
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    doc = user_data[user_id]["document"]
    formatted = json.dumps(doc, indent=2, ensure_ascii=False)
    if len(formatted) > 4000:
        formatted = formatted[:4000] + "\n... (truncated)"
    
    await update.message.reply_text(f"```json\n{formatted}\n```", parse_mode='Markdown')

async def lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /lookup <key>\nExample: /lookup build_version")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    key = context.args[0]
    doc = user_data[user_id]["document"]
    
    try:
        from nested_lookup import nested_lookup
        results = nested_lookup(key, doc)
        
        if not results:
            await update.message.reply_text(f"Key '{key}' not found.")
            return
        
        response = f"🔍 Found {len(results)} result(s):\n\n"
        for i, val in enumerate(results[:10], 1):
            response += f"{i}. `{str(val)[:50]}`\n"
        if len(results) > 10:
            response += f"\n... and {len(results) - 10} more"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def show_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    doc = user_data[user_id]["document"]
    
    try:
        from nested_lookup import get_all_keys
        all_keys = get_all_keys(doc)
        keys_list = sorted(list(all_keys))
        
        if not keys_list:
            await update.message.reply_text("No keys found.")
            return
        
        response = f"📋 *All Keys:* ({len(keys_list)} total)\n\n"
        response += "\n".join([f"• `{k}`" for k in keys_list[:30]])
        if len(keys_list) > 30:
            response += f"\n\n... and {len(keys_list) - 30} more"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def update_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /update <key> <new_value>\nExample: /update model_name 'MacBook Air'")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    key = context.args[0]
    new_value = " ".join(context.args[1:])
    
    try:
        from nested_lookup import nested_lookup, nested_update
        doc = user_data[user_id]["document"]
        old_count = len(nested_lookup(key, doc))
        
        if old_count == 0:
            await update.message.reply_text(f"Key '{key}' not found.")
            return
        
        nested_update(doc, key, new_value, in_place=True, treat_as_element=True)
        user_data[user_id]["document"] = doc
        
        await update.message.reply_text(f"✅ Updated '{key}' {old_count} time(s).")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def delete_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /delete <key>\nExample: /delete memory")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    key = context.args[0]
    
    try:
        from nested_lookup import nested_lookup, nested_delete
        doc = user_data[user_id]["document"]
        old_count = len(nested_lookup(key, doc))
        
        if old_count == 0:
            await update.message.reply_text(f"Key '{key}' not found.")
            return
        
        nested_delete(doc, key, in_place=True)
        user_data[user_id]["document"] = doc
        
        await update.message.reply_text(f"🗑️ Deleted '{key}' {old_count} time(s).")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    user_data[user_id]["document"] = DEFAULT_DOCUMENT.copy()
    await update.message.reply_text("🔄 Document reset to default.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    doc = user_data[user_id]["document"]
    
    try:
        from nested_lookup import get_all_keys
        all_keys = get_all_keys(doc)
        
        response = f"""
📊 *Document Statistics*

• Total unique keys: `{len(all_keys)}`
• Document size: `{len(json.dumps(doc))}` characters
"""
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# ===== MAIN =====

def main():
    """Start the bot."""
    logger.info("Starting bot...")
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("view", view))
    app.add_handler(CommandHandler("lookup", lookup))
    app.add_handler(CommandHandler("keys", show_keys))
    app.add_handler(CommandHandler("update", update_key))
    app.add_handler(CommandHandler("delete", delete_key))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("stats", stats))
    
    webhook_url = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
    
    if webhook_url:
        logger.info(f"Running in webhook mode on port {PORT}")
        logger.info(f"Webhook URL: https://{webhook_url}/webhook")
        
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=f"https://{webhook_url}/webhook"
            # ❌ REMOVED: allowed_updates=Update.ALL_TYPES - THIS WAS THE BUG!
        )
    else:
        logger.info("Running in polling mode")
        app.run_polling()

if __name__ == "__main__":
    main()
user_data = {}

# ===== COMMAND HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message."""
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"document": DEFAULT_DOCUMENT.copy()}
    
    welcome = """
🤖 *Nested Lookup Bot*

*Commands:*
🔍 `/lookup <key>` - Find a key
📋 `/keys` - Show all keys
📄 `/view` - View document
✏️ `/update <key> <value>` - Update a key
🗑️ `/delete <key>` - Delete a key
🔄 `/reset` - Reset document
📊 `/stats` - Show statistics
    """
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View the current document."""
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    doc = user_data[user_id]["document"]
    formatted = json.dumps(doc, indent=2, ensure_ascii=False)
    if len(formatted) > 4000:
        formatted = formatted[:4000] + "\n... (truncated)"
    
    await update.message.reply_text(f"```json\n{formatted}\n```", parse_mode='Markdown')

async def lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Look up a key."""
    if not context.args:
        await update.message.reply_text("Usage: /lookup <key>\nExample: /lookup build_version")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    key = context.args[0]
    doc = user_data[user_id]["document"]
    
    try:
        from nested_lookup import nested_lookup
        results = nested_lookup(key, doc)
        
        if not results:
            await update.message.reply_text(f"Key '{key}' not found.")
            return
        
        response = f"🔍 Found {len(results)} result(s):\n\n"
        for i, val in enumerate(results[:10], 1):
            response += f"{i}. `{str(val)[:50]}`\n"
        if len(results) > 10:
            response += f"\n... and {len(results) - 10} more"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def show_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all unique keys."""
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    doc = user_data[user_id]["document"]
    
    try:
        from nested_lookup import get_all_keys
        all_keys = get_all_keys(doc)
        keys_list = sorted(list(all_keys))
        
        if not keys_list:
            await update.message.reply_text("No keys found.")
            return
        
        response = f"📋 *All Keys:* ({len(keys_list)} total)\n\n"
        response += "\n".join([f"• `{k}`" for k in keys_list[:30]])
        if len(keys_list) > 30:
            response += f"\n\n... and {len(keys_list) - 30} more"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def update_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update all occurrences of a key."""
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /update <key> <new_value>\nExample: /update model_name 'MacBook Air'")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    key = context.args[0]
    new_value = " ".join(context.args[1:])
    
    try:
        from nested_lookup import nested_lookup, nested_update
        doc = user_data[user_id]["document"]
        old_count = len(nested_lookup(key, doc))
        
        if old_count == 0:
            await update.message.reply_text(f"Key '{key}' not found.")
            return
        
        nested_update(doc, key, new_value, in_place=True, treat_as_element=True)
        user_data[user_id]["document"] = doc
        
        await update.message.reply_text(f"✅ Updated '{key}' {old_count} time(s).")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def delete_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete all occurrences of a key."""
    if not context.args:
        await update.message.reply_text("Usage: /delete <key>\nExample: /delete memory")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    key = context.args[0]
    
    try:
        from nested_lookup import nested_lookup, nested_delete
        doc = user_data[user_id]["document"]
        old_count = len(nested_lookup(key, doc))
        
        if old_count == 0:
            await update.message.reply_text(f"Key '{key}' not found.")
            return
        
        nested_delete(doc, key, in_place=True)
        user_data[user_id]["document"] = doc
        
        await update.message.reply_text(f"🗑️ Deleted '{key}' {old_count} time(s).")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset document to default."""
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    user_data[user_id]["document"] = DEFAULT_DOCUMENT.copy()
    await update.message.reply_text("🔄 Document reset to default.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show document statistics."""
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    doc = user_data[user_id]["document"]
    
    try:
        from nested_lookup import get_all_keys
        all_keys = get_all_keys(doc)
        
        response = f"""
📊 *Document Statistics*

• Total unique keys: `{len(all_keys)}`
• Document size: `{len(json.dumps(doc))}` characters
"""
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# ===== MAIN =====

def main():
    """Start the bot."""
    logger.info("Starting bot...")
    
    # Check token
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return
    
    # Create the Application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("view", view))
    app.add_handler(CommandHandler("lookup", lookup))
    app.add_handler(CommandHandler("keys", show_keys))
    app.add_handler(CommandHandler("update", update_key))
    app.add_handler(CommandHandler("delete", delete_key))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("stats", stats))
    
    # Get webhook URL from Railway
    webhook_url = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
    
    if webhook_url:
        # Webhook mode
        logger.info(f"Running in webhook mode on port {PORT}")
        logger.info(f"Webhook URL: https://{webhook_url}/webhook")
        
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=f"https://{webhook_url}/webhook",
            allowed_updates=Update.ALL_TYPES
        )
    else:
        # Polling mode
        logger.info("Running in polling mode")
        app.run_polling()

if __name__ == "__main__":
    main()    "os_details": {"product_version": "10.13.6", "build_version": "17G65"},
    "name": "Test",
    "date": "YYYY-MM-DD HH:MM:SS",
}

SAMPLE_DATA4 = {
    "modelversion": "1.1.0",
    "vorgangsID": "1",
    "versorgungsvorschlagDatum": 1510558834978,
    "eingangsdatum": 1510558834978,
    "plz": 82269,
    "vertragsteile": [
        {
            "typ": "1",
            "beitragsDaten": {
                "endalter": 85,
                "brutto": 58.76,
                "netto": 58.76,
                "zahlungsrhythmus": "MONATLICH",
                "plz": 86899,
            },
            "beginn": 1512082800000,
            "lebenslang": "True",
            "ueberschussverwendung": {
                "ueberschussverwendung": "2",
                "indexoption": "3",
            },
            "deckung": [
                {
                    "typ": "2",
                    "art": "1",
                    "leistung": {"value": 7500242424.0, "einheit": "2"},
                    "leistungsRhythmus": "1",
                }
            ],
            "zuschlagNachlass": [],
        },
        {
            "typ": "1",
            "beitragsDaten": {
                "endalter": 85,
                "brutto": 0.6,
                "netto": 0.6,
                "zahlungsrhythmus": "1",
            },
            "zuschlagNachlass": [],
        },
    ],
}

DEFAULT_DOCUMENT = SAMPLE_DATA1  # Start with hardware data

# Available documents for /load command
AVAILABLE_DOCUMENTS = {
    "hardware": SAMPLE_DATA1,
    "insurance": SAMPLE_DATA4,
}

user_data = {}

# ===== COMMAND HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"document": DEFAULT_DOCUMENT.copy()}
    
    welcome = """
🤖 *Nested Lookup Bot - Full Version*

*Your Data Includes:*
📱 Hardware: MacBook Pro with nested build_version
🏦 Insurance: German contracts (vertragsteile, plz, etc.)

*Available Commands:*

🔍 `/lookup <key>` - Find all values for a key
  Example: `/lookup build_version` (finds 4 occurrences)
  Example: `/lookup plz` (finds 2 ZIP codes)

📋 `/keys` - Show all unique keys
  Example: `/keys`

📄 `/view` - View your document

🔢 `/count_key <key>` - Count occurrences of a key
  Example: `/count_key build_version` → shows 4

🔢 `/count_value <value>` - Count occurrences of a value
  Example: `/count_value 256 KB` → shows 2

✏️ `/update <key> <value>` - Update all occurrences
  Example: `/update model_name "MacBook Air"`

🗑️ `/delete <key>` - Delete all occurrences
  Example: `/delete memory`

🔧 `/alter <key> <operation>` - Apply operation to values
  Operations: +1, -1, *2, /2, uppercase, lowercase, +text, :text
  Example: `/alter plz +1` (adds 1 to all plz values)

📂 `/load <name>` - Load sample data (hardware, insurance)
  Example: `/load insurance`

📊 `/stats` - Show document statistics

🔄 `/reset` - Reset to default
    """
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /lookup <key>\nExample: /lookup build_version")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    key = context.args[0]
    doc = user_data[user_id]["document"]
    
    try:
        # Try regular lookup first
        results = nested_lookup(key, doc)
        
        # If nothing found, try wildcard
        if not results:
            results = nested_lookup(key, doc, wild=True)
        
        if not results:
            await update.message.reply_text(f"Key '{key}' not found")
            return
        
        response = f"🔍 Found {len(results)} occurrence(s) of '{key}':\n\n"
        for i, val in enumerate(results[:10], 1):
            if isinstance(val, dict):
                response += f"{i}. {json.dumps(val)[:100]}...\n"
            else:
                response += f"{i}. `{str(val)[:50]}`\n"
        
        if len(results) > 10:
            response += f"\n... and {len(results) - 10} more"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def show_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    doc = user_data[user_id]["document"]
    
    try:
        all_keys = get_all_keys(doc)
        keys_list = sorted(list(all_keys))
        
        if not keys_list:
            await update.message.reply_text("No keys found")
            return
        
        response = f"📋 *All Keys:* ({len(keys_list)} total)\n\n"
        response += "\n".join([f"• `{k}`" for k in keys_list[:30]])
        if len(keys_list) > 30:
            response += f"\n\n... and {len(keys_list) - 30} more"
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    doc = user_data[user_id]["document"]
    formatted = json.dumps(doc, indent=2, ensure_ascii=False)
    if len(formatted) > 4000:
        formatted = formatted[:4000] + "\n... (truncated)"
    await update.message.reply_text(f"```json\n{formatted}\n```", parse_mode='Markdown')

async def count_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /count_key <key>\nExample: /count_key build_version")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    key = context.args[0]
    doc = user_data[user_id]["document"]
    
    try:
        count = get_occurrence_of_key(doc, key)
        await update.message.reply_text(f"🔢 Key '{key}' appears {count} time(s)")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def count_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /count_value <value>\nExample: /count_value '256 KB'")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    value = " ".join(context.args)
    doc = user_data[user_id]["document"]
    
    try:
        count = get_occurrence_of_value(doc, value)
        await update.message.reply_text(f"🔢 Value '{value}' appears {count} time(s)")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def update_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /update <key> <new_value>\nExample: /update model_name 'MacBook Air'")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    key = context.args[0]
    new_value = " ".join(context.args[1:])
    
    # Try to parse as JSON
    if new_value.startswith(('{', '[')):
        try:
            new_value = json.loads(new_value)
        except:
            pass
    
    doc = user_data[user_id]["document"]
    
    try:
        old_count = len(nested_lookup(key, doc))
        if old_count == 0:
            await update.message.reply_text(f"Key '{key}' not found")
            return
        
        nested_update(doc, key, new_value, in_place=True, treat_as_element=True)
        user_data[user_id]["document"] = doc
        await update.message.reply_text(f"✅ Updated '{key}' {old_count} time(s)")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def delete_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /delete <key>\nExample: /delete memory")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    key = context.args[0]
    doc = user_data[user_id]["document"]
    
    try:
        old_count = len(nested_lookup(key, doc))
        if old_count == 0:
            await update.message.reply_text(f"Key '{key}' not found")
            return
        
        nested_delete(doc, key, in_place=True)
        user_data[user_id]["document"] = doc
        await update.message.reply_text(f"🗑️ Deleted '{key}' {old_count} time(s)")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def alter_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /alter <key> <operation>\n"
            "Operations: +1, -1, *2, /2, uppercase, lowercase, +text, :text\n"
            "Example: /alter plz +1\n"
            "Example: /alter processor_name uppercase"
        )
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    key = context.args[0]
    operation = context.args[1]
    doc = user_data[user_id]["document"]
    
    try:
        def callback(value):
            if isinstance(value, (int, float)):
                if operation == "+1":
                    return value + 1
                elif operation == "-1":
                    return value - 1
                elif operation == "*2":
                    return value * 2
                elif operation == "/2":
                    return value / 2
            elif isinstance(value, str):
                if operation == "uppercase":
                    return value.upper()
                elif operation == "lowercase":
                    return value.lower()
                elif operation.startswith("+"):
                    return value + operation[1:]
                elif operation.startswith(":"):
                    return operation[1:] + value
            return value
        
        old_count = len(nested_lookup(key, doc))
        if old_count == 0:
            await update.message.reply_text(f"Key '{key}' not found")
            return
        
        nested_alter(doc, key, callback, in_place=True)
        user_data[user_id]["document"] = doc
        await update.message.reply_text(f"🔧 Applied '{operation}' to {old_count} occurrence(s)")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def load_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /load <name>\nAvailable: hardware, insurance")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"document": DEFAULT_DOCUMENT.copy()}
    
    name = context.args[0].lower()
    
    if name in AVAILABLE_DOCUMENTS:
        user_data[user_id]["document"] = AVAILABLE_DOCUMENTS[name].copy()
        await update.message.reply_text(f"✅ Loaded '{name}' document. Use /view to see it.")
    else:
        await update.message.reply_text(f"❌ Unknown document '{name}'. Available: {', '.join(AVAILABLE_DOCUMENTS.keys())}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    doc = user_data[user_id]["document"]
    
    try:
        all_keys = get_all_keys(doc)
        total_keys = len(all_keys)
        doc_size = len(json.dumps(doc))
        
        response = f"""
📊 *Document Statistics*

• Total unique keys: `{total_keys}`
• Document size: `{doc_size}` characters
• Keys found:
{chr(10).join([f"  • `{k}`" for k in list(all_keys)[:15]])}
{f"  • ... and {total_keys - 15} more" if total_keys > 15 else ""}
"""
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    user_data[user_id]["document"] = DEFAULT_DOCUMENT.copy()
    await update.message.reply_text("🔄 Document reset to default")

# ===== MAIN =====

def main():
    print("🤖 Starting bot...")
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lookup", lookup))
    app.add_handler(CommandHandler("keys", show_keys))
    app.add_handler(CommandHandler("view", view))
    app.add_handler(CommandHandler("count_key", count_key))
    app.add_handler(CommandHandler("count_value", count_value))
    app.add_handler(CommandHandler("update", update_key))
    app.add_handler(CommandHandler("delete", delete_key))
    app.add_handler(CommandHandler("alter", alter_key))
    app.add_handler(CommandHandler("load", load_document))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("reset", reset))
    
    webhook_url = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
    
    if webhook_url:
        print(f"🚀 Starting webhook on port {PORT}")
        print(f"🔗 URL: https://{webhook_url}/webhook")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=f"https://{webhook_url}/webhook"
        )
    else:
        print("Starting polling mode...")
        app.run_polling()

if __name__ == "__main__":
    main()            "processor_speed": "2.7 GHz",
            "core_details": {
                "build_version": "4",
                "l2_cache(per_core)": "256 KB"
            }
        },
        "number_of_cores": "4",
        "memory": "256 KB"
    },
    "os_details": {
        "product_version": "10.13.6",
        "build_version": "17G65"
    }
}

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"document": DEFAULT_DOCUMENT.copy()}
    
    welcome = """
🤖 *Nested Lookup Bot*

*Complete Commands:*

🔍 `/lookup <key>` - Find all values for a key
🎯 `/wild <pattern>` - Find keys matching a pattern
📋 `/keys` - Show all unique keys
📄 `/view` - View your document
✏️ `/update <key> <value>` - Update all occurrences
🗑️ `/delete <key>` - Delete all occurrences
🔧 `/alter <key> <operation>` - Apply operation to values
🔢 `/count_key <key>` - Count occurrences of a key
🔢 `/count_value <value>` - Count occurrences of a value
📝 `/set` - Set new document (reply with JSON)
🔄 `/reset` - Reset to default

*Examples:*
/lookup nested
/alter numbers +1
/count_key build_version
"""
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /lookup <key>")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    key = context.args[0]
    doc = user_data[user_id]["document"]
    
    try:
        results = nested_lookup(key, doc)
        
        if not results:
            await update.message.reply_text(f"Key '{key}' not found")
            return
        
        if len(results) == 1:
            await update.message.reply_text(f"Found: `{results[0]}`", parse_mode='Markdown')
        else:
            response = f"Found {len(results)} values:\n"
            for i, val in enumerate(results[:10], 1):
                response += f"{i}. `{str(val)[:50]}`\n"
            if len(results) > 10:
                response += f"... and {len(results) - 10} more"
            await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def wild_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /wild <pattern>")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    pattern = context.args[0]
    doc = user_data[user_id]["document"]
    
    try:
        results = nested_lookup(pattern, doc, wild=True)
        
        if not results:
            await update.message.reply_text(f"No keys matching '{pattern}' found")
            return
        
        response = f"Found {len(results)} matching values:\n"
        for i, val in enumerate(results[:10], 1):
            response += f"{i}. `{str(val)[:50]}`\n"
        if len(results) > 10:
            response += f"... and {len(results) - 10} more"
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def show_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    doc = user_data[user_id]["document"]
    
    try:
        all_keys = get_all_keys(doc)
        keys_list = sorted(list(all_keys))
        
        if not keys_list:
            await update.message.reply_text("No keys found")
            return
        
        response = f"📋 *All Keys:* ({len(keys_list)} total)\n\n"
        response += "\n".join([f"• `{k}`" for k in keys_list[:30]])
        if len(keys_list) > 30:
            response += f"\n\n... and {len(keys_list) - 30} more"
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    doc = user_data[user_id]["document"]
    formatted = json.dumps(doc, indent=2, ensure_ascii=False)
    if len(formatted) > 4000:
        formatted = formatted[:4000] + "\n... (truncated)"
    await update.message.reply_text(f"```json\n{formatted}\n```", parse_mode='Markdown')

async def update_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /update <key> <new_value>")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    key = context.args[0]
    new_value = " ".join(context.args[1:])
    
    # Try to parse as JSON
    if new_value.startswith(('{', '[')):
        try:
            new_value = json.loads(new_value)
        except:
            pass
    
    doc = user_data[user_id]["document"]
    
    try:
        old_count = len(nested_lookup(key, doc))
        if old_count == 0:
            await update.message.reply_text(f"Key '{key}' not found")
            return
        
        nested_update(doc, key, new_value, in_place=True, treat_as_element=True)
        user_data[user_id]["document"] = doc
        await update.message.reply_text(f"✅ Updated '{key}' {old_count} time(s)")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def delete_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /delete <key>")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    key = context.args[0]
    doc = user_data[user_id]["document"]
    
    try:
        old_count = len(nested_lookup(key, doc))
        if old_count == 0:
            await update.message.reply_text(f"Key '{key}' not found")
            return
        
        nested_delete(doc, key, in_place=True)
        user_data[user_id]["document"] = doc
        await update.message.reply_text(f"🗑️ Deleted '{key}' {old_count} time(s)")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def alter_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /alter <key> <operation>\n"
            "Operations: +1, -1, *2, /2, uppercase, lowercase\n"
            "Example: /alter numbers +1"
        )
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    key = context.args[0]
    operation = context.args[1]
    doc = user_data[user_id]["document"]
    
    try:
        # Define callback based on operation
        def callback(value):
            if isinstance(value, (int, float)):
                if operation == "+1":
                    return value + 1
                elif operation == "-1":
                    return value - 1
                elif operation == "*2":
                    return value * 2
                elif operation == "/2":
                    return value / 2
            elif isinstance(value, str):
                if operation == "uppercase":
                    return value.upper()
                elif operation == "lowercase":
                    return value.lower()
                elif operation.startswith("+"):
                    return value + operation[1:]
                elif operation.startswith(":"):
                    return operation[1:] + value
            return value
        
        old_count = len(nested_lookup(key, doc))
        if old_count == 0:
            await update.message.reply_text(f"Key '{key}' not found")
            return
        
        nested_alter(doc, key, callback, in_place=True)
        user_data[user_id]["document"] = doc
        await update.message.reply_text(f"🔧 Applied '{operation}' to {old_count} occurrence(s)")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def count_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /count_key <key>")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    key = context.args[0]
    doc = user_data[user_id]["document"]
    
    try:
        count = get_occurrence_of_key(doc, key)
        await update.message.reply_text(f"🔢 Key '{key}' appears {count} time(s)")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def count_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /count_value <value>")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    value = " ".join(context.args)
    doc = user_data[user_id]["document"]
    
    try:
        count = get_occurrence_of_value(doc, value)
        await update.message.reply_text(f"🔢 Value '{value}' appears {count} time(s)")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def set_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if update.message.reply_to_message:
        json_text = update.message.reply_to_message.text
    elif context.args:
        json_text = " ".join(context.args)
    else:
        await update.message.reply_text("Reply to a message with JSON or use: /set {\"key\": \"value\"}")
        return
    
    try:
        new_doc = json.loads(json_text)
        if user_id not in user_data:
            user_data[user_id] = {"document": new_doc}
        else:
            user_data[user_id]["document"] = new_doc
        await update.message.reply_text("✅ Document updated!")
    except json.JSONDecodeError as e:
        await update.message.reply_text(f"❌ Invalid JSON: {str(e)}")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    user_data[user_id]["document"] = DEFAULT_DOCUMENT.copy()
    await update.message.reply_text("🔄 Document reset to default")

def main():
    print("🤖 Starting bot...")
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add all command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lookup", lookup))
    app.add_handler(CommandHandler("wild", wild_lookup))
    app.add_handler(CommandHandler("keys", show_keys))
    app.add_handler(CommandHandler("view", view))
    app.add_handler(CommandHandler("update", update_key))
    app.add_handler(CommandHandler("delete", delete_key))
    app.add_handler(CommandHandler("alter", alter_key))
    app.add_handler(CommandHandler("count_key", count_key))
    app.add_handler(CommandHandler("count_value", count_value))
    app.add_handler(CommandHandler("set", set_document))
    app.add_handler(CommandHandler("reset", reset))
    
    webhook_url = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
    
    if webhook_url:
        print(f"🚀 Starting webhook on port {PORT}")
        print(f"🔗 URL: https://{webhook_url}/webhook")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=f"https://{webhook_url}/webhook"
        )
    else:
        print("Starting polling mode...")
        app.run_polling()

if __name__ == "__main__":
    main()🔍 `/lookup <key>` - Find a key
📋 `/keys` - Show all keys
📄 `/view` - View document
✏️ `/update <key> <value>` - Update a key
🗑️ `/delete <key>` - Delete a key
🔄 `/reset` - Reset document
"""
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /lookup <key>")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    key = context.args[0]
    results = nested_lookup(key, user_data[user_id]["document"])
    
    if results:
        await update.message.reply_text(f"Found: {results}")
    else:
        await update.message.reply_text(f"Key '{key}' not found")

async def show_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    all_keys = get_all_keys(user_data[user_id]["document"])
    keys_list = sorted(list(all_keys))
    await update.message.reply_text(f"Keys: {keys_list}")

async def view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    doc = user_data[user_id]["document"]
    formatted = json.dumps(doc, indent=2, ensure_ascii=False)
    if len(formatted) > 4000:
        formatted = formatted[:4000] + "\n... (truncated)"
    await update.message.reply_text(f"```json\n{formatted}\n```", parse_mode='Markdown')

async def update_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /update <key> <new_value>")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    key = context.args[0]
    new_value = " ".join(context.args[1:])
    
    doc = user_data[user_id]["document"]
    old_count = len(nested_lookup(key, doc))
    
    if old_count == 0:
        await update.message.reply_text(f"Key '{key}' not found")
        return
    
    nested_update(doc, key, new_value, in_place=True, treat_as_element=True)
    user_data[user_id]["document"] = doc
    await update.message.reply_text(f"Updated '{key}' {old_count} time(s)")

async def delete_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /delete <key>")
        return
    
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    
    key = context.args[0]
    doc = user_data[user_id]["document"]
    old_count = len(nested_lookup(key, doc))
    
    if old_count == 0:
        await update.message.reply_text(f"Key '{key}' not found")
        return
    
    nested_delete(doc, key, in_place=True)
    user_data[user_id]["document"] = doc
    await update.message.reply_text(f"Deleted '{key}' {old_count} time(s)")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("Use /start first")
        return
    user_data[user_id]["document"] = DOCUMENT.copy()
    await update.message.reply_text("Document reset!")

def main():
    print("🤖 Starting bot...")
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lookup", lookup))
    app.add_handler(CommandHandler("keys", show_keys))
    app.add_handler(CommandHandler("view", view))
    app.add_handler(CommandHandler("update", update_key))
    app.add_handler(CommandHandler("delete", delete_key))
    app.add_handler(CommandHandler("reset", reset))
    
    port = int(os.environ.get('PORT', 10000))
    webhook_url = os.environ.get('RENDER_EXTERNAL_URL')
    
    if webhook_url:
        print(f"🚀 Starting webhook on port {port}")
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=webhook_url + '/webhook'
        )
    else:
        print("Starting polling mode...")
        app.run_polling()

if __name__ == "__main__":
    main()
