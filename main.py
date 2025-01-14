import os
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler, filters, ContextTypes
from uuid import uuid4
from typing import List, Optional

BOT_TOKEN = os.getenv("BOT_TOKEN", "your token here")
JSON_URL = 'https://raw.githubusercontent.com/trickzin/ItemID/refs/heads/main/assets/itemData.json'
ICON_URL_BASE = 'https://raw.githubusercontent.com/trickzin/ff-resources/main/pngs/300x300/'

data: List[dict] = []

def fetch_data() -> None:
    global data
    try:
        response = requests.get(JSON_URL)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")

def escape_markdown(text: str) -> str:
    escape_chars = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{char}" if char in escape_chars else char for char in text)

def search_items(keyword: str) -> List[dict]:
    if keyword.isdigit():
        return [item for item in data if item['itemID'] == keyword]
    else:
        return [item for item in data if keyword.lower() in item['description'].lower() or keyword.lower() in item.get('icon', '').lower()]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Welcome! This bot helps you find items by their description or itemID.\n\n"
        "Use the following commands:\n"
        "/search <keyword> - Search for items by keyword.\n"
        "/help - Learn more about how to use the bot.\n\n"
        "Developed by https://t.me/trickzqw"
    )

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "To use this bot, send a search keyword to find items or use the /search command.\n\n"
        "Commands:\n"
        "/search <keyword> - Search for items based on description or itemID.\n"
        "/help - Show this help message.\n"
        "For more info or to report issues, contact the developer: https://t.me/trickzqw"
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args:
        keyword = " ".join(context.args).strip()
        results = search_items(keyword)

        if results:
            result = results[0]
            icon_url = f"{ICON_URL_BASE}{result['icon']}.png"
            description2 = result.get('description2', 'No additional description available.')

            response_text = (
                f"*Name*: `{escape_markdown(result['description'])}`\n"
                f"*Item ID*: `{escape_markdown(result['itemID'])}`\n"
                f"*Description*: `{escape_markdown(description2)}`\n"
                f"*Icon Name*: `{escape_markdown(result['icon'])}`"
            )

            new_message = await update.message.reply_text(
                response_text,
                parse_mode='MarkdownV2',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👁️", callback_data=f"show_preview:{result['itemID']}:{result['icon']}"),
                     InlineKeyboardButton("🖼️ Create Sticker", callback_data=f"create_sticker:{result['itemID']}:{result['icon']}")]
                ])
            )
        else:
            await update.message.reply_text("No items found matching your search keyword.")
    else:
        await update.message.reply_text("Please provide a keyword to search. Example: /search sword")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyword = update.message.text.strip()
    escaped_text = escape_markdown(keyword)
    results = search_items(keyword)

    if results:
        result = results[0]
        icon_url = f"{ICON_URL_BASE}{result['icon']}.png"
        description2 = result.get('description2', 'No additional description available.')
        
        response_text = (
            f"*Name*: `{escape_markdown(result['description'])}`\n"
            f"*Item ID*: `{escape_markdown(result['itemID'])}`\n"
            f"*Description*: `{escape_markdown(description2)}`\n"
            f"*Icon Name*: `{escape_markdown(result['icon'])}`"
        )
        new_message = await update.message.reply_text(
            response_text,
            parse_mode='MarkdownV2',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👁️", callback_data=f"show_preview:{result['itemID']}:{result['icon']}"),
                 InlineKeyboardButton("🖼️ Create Sticker", callback_data=f"create_sticker:{result['itemID']}:{result['icon']}")]
            ])
        )
    else:
        await update.message.reply_text("No items found matching your search keyword.")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action, item_id, icon_name = query.data.split(':')
    
    if action == 'show_preview':
        result = next((item for item in data if item['itemID'] == item_id), None)
        if result:
            icon_url = f"{ICON_URL_BASE}{icon_name}.png"
            response = requests.get(icon_url)
            if response.status_code == 200:
                media = InputMediaPhoto(icon_url, caption=f"*Name* `{escape_markdown(result['description'])}`\n*Item ID* `{escape_markdown(result['itemID'])}`\n*Icon Name* `{escape_markdown(result['icon'])}`", parse_mode="MarkdownV2")
            else:
                media = InputMediaPhoto(media="https://via.placeholder.com/2048?text=trick+7", caption=f"*Name* `{escape_markdown(result['description'])}`\n*Item ID* `{escape_markdown(result['itemID'])}`\n*Icon Name* `{escape_markdown(result['icon'])}`", parse_mode="MarkdownV2")
            
            if query.message.caption != media.caption or query.message.reply_markup:
                await query.edit_message_media(media=media)
                await query.edit_message_reply_markup(reply_markup=None)
        else:
            await query.edit_message_text("Item not found.")
    
    elif action == 'create_sticker':
        result = next((item for item in data if item['itemID'] == item_id), None)
        if result:
            icon_url = f"{ICON_URL_BASE}{icon_name}.png"
            response = requests.get(icon_url)

            if response.status_code == 200:
                sticker_file = response.content
                await query.message.reply_sticker(sticker=sticker_file)
            else:
                await query.edit_message_text("Failed to retrieve icon for sticker creation.")
    else:
        await query.edit_message_text("Invalid action.")

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query.query
    if not query:
        return

    results = []

    items = search_items(query)
    for item in items:
        results.append(
            InlineQueryResultArticle(
                id=uuid4(),
                title=f"Finding {item['description']}",
                input_message_content=InputTextMessageContent(
                    message_text=f"*Name* `{escape_markdown(item['description'])}`\n"
                                 f"*Item ID* `{escape_markdown(item['itemID'])}`\n"
                                 f"*Icon Name* `{escape_markdown(item['icon'])}`",
                    parse_mode='MarkdownV2'
                ),
                description=f"Search result for {item['description']}"
            )
        )

    await update.inline_query.answer(results)

def main() -> None:
    fetch_data()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(InlineQueryHandler(inline_query))
    app.run_polling()

if __name__ == '__main__':
    main()
