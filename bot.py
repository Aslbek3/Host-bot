import logging
import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.exceptions import TelegramBadRequest

# Bot configuration
API_TOKEN = '8012951804:AAFmcyU4LxRMkRzSPBuGIlIB_ZsMeFcNT4M'
CHANNEL_ID = -1003471150905
ADMIN_ID = 7586510077

# Logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Database setup
def init_db():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_number TEXT UNIQUE NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

async def check_subscription(user_id: int):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception as e:
        logging.error(f"Error checking subscription: {e}")
        return False

def get_subscription_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Kanalga obuna bo'lish", url=f"https://t.me/c/{str(CHANNEL_ID)[4:]}")],
        [InlineKeyboardButton(text="Tekshirish", callback_data="check_sub")]
    ])
    return keyboard

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    is_subscribed = await check_subscription(message.from_user.id)
    if not is_subscribed:
        await message.answer(
            "Botdan foydalanish uchun kanalimizga obuna bo'lishingiz kerak:",
            reply_markup=get_subscription_keyboard()
        )
        return

    welcome_text = "Xush kelibsiz! Faylni olish uchun uning raqamini yuboring."
    if message.from_user.id == ADMIN_ID:
        welcome_text += "\n\nSiz adminsiz. Fayl yuboring va unga raqam biriktiring."
    
    await message.answer(welcome_text)

@dp.callback_query(F.data == "check_sub")
async def process_check_sub(callback_query: types.CallbackQuery):
    is_subscribed = await check_subscription(callback_query.from_user.id)
    if is_subscribed:
        await callback_query.message.edit_text("Rahmat! Endi botdan foydalanishingiz mumkin.")
        # Create a dummy message to pass to cmd_start
        dummy_message = callback_query.message
        dummy_message.from_user = callback_query.from_user
        await cmd_start(dummy_message)
    else:
        await callback_query.answer("Siz hali obuna bo'lmagansiz!", show_alert=True)

# Admin file handling
admin_temp_data = {}

@dp.message(F.from_user.id == ADMIN_ID, F.document | F.video | F.photo | F.audio | F.voice)
async def handle_admin_file(message: types.Message):
    file_id = ""
    file_type = ""
    
    if message.document:
        file_id = message.document.file_id
        file_type = "document"
    elif message.video:
        file_id = message.video.file_id
        file_type = "video"
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
    elif message.audio:
        file_id = message.audio.file_id
        file_type = "audio"
    elif message.voice:
        file_id = message.voice.file_id
        file_type = "voice"
        
    admin_temp_data[ADMIN_ID] = {"file_id": file_id, "file_type": file_type}
    await message.answer("Fayl qabul qilindi. Endi ushbu fayl uchun raqam yuboring:")

@dp.message(F.from_user.id == ADMIN_ID, F.text.regexp(r'^\d+$'))
async def handle_admin_number(message: types.Message):
    if ADMIN_ID in admin_temp_data:
        file_number = message.text
        data = admin_temp_data[ADMIN_ID]
        
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO files (file_id, file_type, file_number) VALUES (?, ?, ?)",
                (data['file_id'], data['file_type'], file_number)
            )
            conn.commit()
            await message.answer(f"Fayl muvaffaqiyatli saqlandi! Raqam: {file_number}")
            del admin_temp_data[ADMIN_ID]
        except Exception as e:
            await message.answer(f"Xatolik yuz berdi: {e}")
        finally:
            conn.close()
    else:
        await handle_user_request(message)

@dp.message(F.text.regexp(r'^\d+$'))
async def handle_user_request(message: types.Message):
    is_subscribed = await check_subscription(message.from_user.id)
    if not is_subscribed:
        await message.answer(
            "Botdan foydalanish uchun kanalimizga obuna bo'lishingiz kerak:",
            reply_markup=get_subscription_keyboard()
        )
        return

    file_number = message.text
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, file_type FROM files WHERE file_number = ?", (file_number,))
    result = cursor.fetchone()
    conn.close()

    if result:
        file_id, file_type = result
        try:
            if file_type == "document":
                await message.answer_document(file_id)
            elif file_type == "video":
                await message.answer_video(file_id)
            elif file_type == "photo":
                await message.answer_photo(file_id)
            elif file_type == "audio":
                await message.answer_audio(file_id)
            elif file_type == "voice":
                await message.answer_voice(file_id)
        except Exception as e:
            await message.answer(f"Faylni yuborishda xatolik: {e}")
    else:
        await message.answer("Bunday raqamli fayl topilmadi.")

if __name__ == '__main__':
    init_db()
    async def main():
        await dp.start_polling(bot)
    
    asyncio.run(main())

