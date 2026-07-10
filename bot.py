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

# ===== DATA =====
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
    "os_details": {"product_version": "10.13.6", "build_version": "17G65"},
    "name": "Test",
    "date": "YYYY-MM-DD HH:MM:SS"
}

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
