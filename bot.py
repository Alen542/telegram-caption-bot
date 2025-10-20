import asyncio
import re
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode
from collections import defaultdict
import logging

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot Token - Environment variable থেকে নেওয়া
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable not found!")
    raise ValueError("BOT_TOKEN is required")

# Authorized User IDs (তোমার user IDs এখানে লিখো)
AUTHORIZED_USERS = [
    123456789,  # প্রথম user ID
    987654321,  # দ্বিতীয় user ID (যদি থাকে)
]

# Group ID যেখানে bot কাজ করবে
WORKING_GROUP_ID = -1003147912587  # তোমার group ID

# Bot এবং Dispatcher Initialize
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Video processing queue tracker
processing_queue = defaultdict(list)
is_processing = defaultdict(bool)

# Logging function
def log(message, important=False):
    """Terminal এ timestamp সহ log করা"""
    if important:
        logger.info(message)

# Caption Modification Function
def modify_caption(original_caption):
    """Caption modify করার main function"""
    if not original_caption:
        return None
    
    extension_match = re.search(r'(\.\w+)$', original_caption)
    extension = extension_match.group(1) if extension_match else '.mp4'
    
    caption_without_ext = original_caption.replace(extension, '')
    
    # Step 1: ZEE5 specific pattern remove
    caption_without_ext = re.sub(r'\.Bn\.mp4a\.\d+kbps\.', '.', caption_without_ext, flags=re.IGNORECASE)
    caption_without_ext = re.sub(r'\.mp4a\.\d+kbps\.', '.', caption_without_ext, flags=re.IGNORECASE)
    caption_without_ext = re.sub(r'\.Bna\.\d+kbps\.', '.', caption_without_ext, flags=re.IGNORECASE)
    
    # Step 2: Platform names এবং technical details remove
    patterns_to_remove = [
        r'\.(JioHotstar|DSNP|SUNNXT|ZEE5)\.',
        r'\.WEB-DL\.',
        r'\.(Bengali|Tamil|Bn)\.',
        r'\.AAC\.\d+\.\d+\.',
        r'\.x264\.',
    ]
    
    for pattern in patterns_to_remove:
        caption_without_ext = re.sub(pattern, '.', caption_without_ext, flags=re.IGNORECASE)
    
    # Step 3: Uploader name replace
    parts = caption_without_ext.split('.')
    if len(parts) > 0 and parts[-1]:
        parts[-1] = '@SBRipssbot'
    
    modified = '.'.join(parts)
    modified = re.sub(r'\.+', ' ', modified)
    modified = re.sub(r'\s+', ' ', modified).strip()
    modified = modified + extension
    
    final_caption = f"<b>{modified}</b>"
    
    return final_caption

# Authorization Check
def is_authorized(user_id):
    return user_id in AUTHORIZED_USERS

# Check if from working group
def is_from_working_group(message: Message):
    if message.chat.type in ['group', 'supergroup']:
        return message.chat.id == WORKING_GROUP_ID
    return False

# /start Command Handler
@dp.message(Command("start"))
async def send_welcome(message: Message):
    user_id = message.from_user.id
    
    if not is_authorized(user_id):
        await message.reply(
            f"❌ তুমি এই bot ব্যবহার করার জন্য authorized নও।\n\n"
            f"Your User ID: {user_id}"
        )
        return
    
    welcome_message = (
        "🎬 <b>Video Caption Modifier Bot</b>\n\n"
        "আমি একটি automatic caption modification bot। "
        "আমার কাজ হলো video এর caption modify করে তোমাকে পাঠানো।\n\n"
        "<b>কিভাবে ব্যবহার করবে:</b>\n"
        "1️⃣ আমাকে caption সহ video পাঠাও (Private chat)\n"
        "2️⃣ অথবা Private Group এ video post/forward করো\n"
        "3️⃣ আমি automatically caption modify করব\n\n"
        "📝 <b>Note:</b> Video download/upload হবে না, শুধু caption change হবে।\n\n"
        "✅ তুমি authorized user!\n\n"
        "🎯 <b>Features:</b>\n"
        "• একসাথে একাধিক video পাঠালে একটা একটা করে process হবে\n"
        "• Caption automatically bold হবে\n"
        "• সব platform support করে (ZEE5, JioHotstar, SUNNXT)\n"
        "• Private group এও কাজ করে\n"
        "• Forward করা video ও handle করে\n\n"
        "<b>Commands:</b>\n"
        "/test - Group access test করো"
    )
    
    await message.reply(welcome_message, parse_mode=ParseMode.HTML)

# /test Command
@dp.message(Command("test"))
async def test_group_access(message: Message):
    user_id = message.from_user.id
    
    if not is_authorized(user_id):
        await message.reply("❌ Unauthorized")
        return
    
    try:
        test_msg = await bot.send_message(
            chat_id=WORKING_GROUP_ID,
            text="🧪 <b>Bot Test Message</b>\n\n✅ Bot group এ access পেয়েছে এবং message পাঠাতে পারছে!",
            parse_mode=ParseMode.HTML
        )
        
        response = (
            "✅ <b>Group Access Test Successful!</b>\n\n"
            f"👥 Group ID: <code>{WORKING_GROUP_ID}</code>\n"
            f"📨 Test Message ID: <code>{test_msg.message_id}</code>\n"
            f"✅ Bot successfully posted to the group!\n\n"
            "এখন group এ video post/forward করে দেখো কাজ করছে কিনা।"
        )
        
        await message.reply(response, parse_mode=ParseMode.HTML)
        
        await asyncio.sleep(2)
        await bot.delete_message(WORKING_GROUP_ID, test_msg.message_id)
        
    except Exception as e:
        error_response = (
            "❌ <b>Group Access Test Failed!</b>\n\n"
            f"👥 Group ID: <code>{WORKING_GROUP_ID}</code>\n"
            f"❌ Error: <code>{str(e)}</code>\n\n"
            "<b>Possible issues:</b>\n"
            "1. Bot group এ add করা নেই\n"
            "2. Bot admin না\n"
            "3. Group ID ভুল আছে\n"
            "4. Bot এর Privacy Mode off করা নেই\n\n"
            "<b>Solution:</b>\n"
            "• Bot কে group এ admin বানাও\n"
            "• @BotFather থেকে Privacy Mode off করো\n"
            "• Group ID ঠিক আছে কিনা check করো"
        )
        await message.reply(error_response, parse_mode=ParseMode.HTML)

# Group Video Handler
@dp.message(F.video, F.chat.type.in_(['group', 'supergroup']))
async def handle_group_video(message: Message):
    if not is_from_working_group(message):
        return
    
    try:
        original_caption = message.caption
        
        if not original_caption:
            return
        
        modified_caption = modify_caption(original_caption)
        file_id = message.video.file_id
        
        await bot.send_video(
            chat_id=message.chat.id,
            video=file_id,
            caption=modified_caption,
            parse_mode=ParseMode.HTML,
            supports_streaming=True
        )
        
    except Exception as e:
        log(f"❌ Group video error: {str(e)}", important=True)

# Private Chat Video Handler
@dp.message(F.video, F.chat.type == 'private')
async def handle_private_video(message: Message):
    user_id = message.from_user.id
    
    if not is_authorized(user_id):
        await message.reply(
            f"❌ তুমি এই bot ব্যবহার করার জন্য authorized নও।\n\n"
            f"Your User ID: {user_id}"
        )
        return
    
    processing_queue[user_id].append(message)
    
    if not is_processing[user_id]:
        await process_video_queue(user_id)

async def process_video_queue(user_id):
    is_processing[user_id] = True
    
    while processing_queue[user_id]:
        message = processing_queue[user_id][0]
        
        try:
            original_caption = message.caption
            
            if not original_caption:
                await message.reply("⚠️ Video তে caption নেই! Caption সহ video পাঠাও।")
                processing_queue[user_id].pop(0)
                continue
            
            processing_msg = await message.reply("⏳ Caption modify করছি...")
            
            modified_caption = modify_caption(original_caption)
            file_id = message.video.file_id
            
            await bot.send_video(
                chat_id=message.chat.id,
                video=file_id,
                caption=modified_caption,
                parse_mode=ParseMode.HTML,
                supports_streaming=True
            )
            
            try:
                await bot.delete_message(message.chat.id, processing_msg.message_id)
            except:
                pass
            
            await message.reply("✅ Caption successfully modified!")
            
            processing_queue[user_id].pop(0)
            await asyncio.sleep(0.5)
            
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")
            processing_queue[user_id].pop(0)
            await asyncio.sleep(0.5)
    
    is_processing[user_id] = False
    
    if not processing_queue[user_id]:
        del processing_queue[user_id]
        del is_processing[user_id]

# Other Messages Handler
@dp.message()
async def handle_other_messages(message: Message):
    if message.chat.type in ['group', 'supergroup']:
        return
    
    user_id = message.from_user.id
    
    if not is_authorized(user_id):
        await message.reply(
            f"❌ তুমি এই bot ব্যবহার করার জন্য authorized নও।\n\n"
            f"Your User ID: {user_id}"
        )
    else:
        await message.reply(
            "⚠️ আমাকে caption সহ video পাঠাও।\n"
            "অন্য কোনো message পাঠানোর দরকার নেই।"
        )

# Main Function
async def main():
    log("🤖 Bot Starting...", important=True)
    
    try:
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        log(f"❌ Bot crashed: {str(e)}", important=True)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("🛑 Bot stopped", important=True)
