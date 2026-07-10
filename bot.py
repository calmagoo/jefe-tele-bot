import os
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from nested_lookup import nested_lookup, get_all_keys, nested_update, nested_delete

BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

DOCUMENT = {
    "example": {
        "nested": {
            "key": "value",
            "numbers": [1, 2, 3, 4, 5]
        },
        "another_key": "Hello World"
    },
    "list_example": [
        {"name": "item1", "value": 100},
        {"name": "item2", "value": 200}
    ]
}

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"document": DOCUMENT.copy()}
    
    welcome = """
🤖 *Nested Lookup Bot*

*Commands:*
🔍 `/lookup <key>` - Find a key
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
