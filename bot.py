# bot.py
import os
import logging
import requests
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB Connection
mongo_uri = os.getenv('MONGODB_URI')
client = MongoClient(mongo_uri)
db = client.telegramBot
users_collection = db.users

# Telegram Bot Token and Channel ID
token = os.getenv('BOT_TOKEN')
updates_channel = os.getenv('OP_CHANNEL')
app = Flask(__name__)

# Terabox domains
terabox_domains = [
    "www.mirrobox.com", "www.nephobox.com", "freeterabox.com", "www.freeterabox.com", "1024tera.com",
    # more domains...
]

def is_terabox_link(link):
    return any(domain in link for domain in terabox_domains)

async def check_subscription(chat_id, application):
    try:
        member = await application.bot.get_chat_member(updates_channel, chat_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking subscription: {e}")
        return False

async def send_start_message(chat_id, application):
    await application.bot.send_photo(chat_id, 'https://i.ibb.co/RhccGh9/7ec413813c52.jpg', caption="""
    👋 *Welcome to TeraBox Video Player Bot!*\n\n
    *Paste your TeraBox link and watch your video instantly—no TeraBox app needed!*\n\n
    Please subscribe to our [Updates Channel](https://t.me/NOOBPrivate) and click /start again to begin using the bot.
    """, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton('Join Channel to Use Me', url='https://t.me/NOOBPrivate'),
        InlineKeyboardButton('How to use Bot', url='https://t.me/NOOBX_xBot?start=getFile-1426_SoxlF2VivnV4ptlX')
    ]]))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    is_subscribed = await check_subscription(chat_id, context.application)

    if is_subscribed:
        await context.bot.send_photo(chat_id, 'https://i.ibb.co/RhccGh9/7ec413813c52.jpg', caption="""
        🎉 *Welcome back!* 😊\n\n*Send a TeraBox link to watch or download your video.* 🍿
        """, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Any Help?", url="https://t.me/NOOBPrivateChats")
        ]]))
    else:
        await send_start_message(chat_id, context.application)

async def stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    try:
        user_count = users_collection.count_documents({})
        link_count = users_collection.aggregate([
            {'$unwind': '$links'},
            {'$count': 'count'}
        ]).next()['count']

        await context.bot.send_photo(chat_id, 'https://i.ibb.co/RhccGh9/7ec413813c52.jpg', caption=f"""
        📊 *Current Bot Stats:*\n\n
        👥 *Total Users:* {user_count}\n
        🔗 *Links Processed:* {link_count}
        """, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✨ Dear my friend✨", url="tg://settings")
        ]]))
    except Exception as e:
        logger.error(f"Error retrieving stats: {e}")
        await context.bot.send_message(chat_id, "❌ *An error occurred while retrieving statistics. Please try again later.*")

async def broad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    owner_id = os.getenv('OWNER_ID')
    if str(chat_id) != owner_id:
        await context.bot.send_message(chat_id, "❌ *You do not have permission to use this command.*")
        return

    message = update.message.text.partition(' ')[2]
    users = users_collection.find()
    
    for user in users:
        try:
            await context.bot.send_message(user['_id'], f"📢 *Broadcast Message:*\n\n{message}")
        except Exception as e:
            logger.error(f"Failed to send message to {user['_id']}: {e}")

    await context.bot.send_message(chat_id, "✅ *Broadcast message sent to all users.*")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    text = update.message.text

    if text.startswith('/start') or text.startswith('/stat') or text.startswith('/broad'):
        return

    is_subscribed = await check_subscription(chat_id, context.application)
    if not is_subscribed:
        await send_start_message(chat_id, context.application)
        return

    if not is_terabox_link(text):
        await context.bot.send_message(chat_id, "❌ *That is not a valid TeraBox link.*")
        return

    await context.bot.send_message(chat_id, "🔄 *Processing your link...*")
    try:
        response = requests.get(f'https://tera.ronok.workers.dev/?link={text}&apikey=0b010c132e2cbd862cbd8a6ae430dd51d3a0d5ea')
        download_url = response.json().get('url')

        await context.bot.send_photo(chat_id, 'https://i.ibb.co/RhccGh9/7ec413813c52.jpg', caption="""
        ✅ *Your video is ready!*\n\n📥 *Click the button below to view or download it.*
        """, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton('ᢱ Watch/Download ⎙', url=download_url)
        ]]))
    except Exception as e:
        logger.error(f"Error processing link: {e}")
        await context.bot.send_message(chat_id, "❌ *There was an error processing your link. Please try again later.*")

# Flask route for health check
@app.route('/')
def home():
    return "TeraBox Bot is running!"

if __name__ == '__main__':
    # Initialize the bot application
    application = ApplicationBuilder().token(token).build()

    # Register command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('stat', stat))
    application.add_handler(CommandHandler('broad', broad))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot in polling mode
    application.run_polling()

    # Flask server
    app.run(port=os.getenv('PORT', 8080))
