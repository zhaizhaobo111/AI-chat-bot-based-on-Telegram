import asyncio
import io
import json
import os
import time
import requests as http_requests
from PIL import Image
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.request import HTTPXRequest

from config import TELEGRAM_BOT_TOKEN, MAX_HISTORY_ROUNDS, PROXY_URL
from ai_client import chat_stream, set_user_mode, get_user_mode
from meme_manager import detect_mood, get_meme_url
from personalities import PRESETS, list_presets

# 数据文件
DATA_FILE = "data.json"

# 内存数据
histories: dict[int, list[dict]] = {}
meme_enabled: dict[int, bool] = {}


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            histories.clear()
            histories.update({int(k): v for k, v in data.get("histories", {}).items()})
            meme_enabled.clear()
            meme_enabled.update({int(k): v for k, v in data.get("meme_enabled", {}).items()})


def save_data():
    data = {
        "histories": {str(k): v for k, v in histories.items()},
        "meme_enabled": {str(k): v for k, v in meme_enabled.items()},
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def get_history(user_id: int) -> list[dict]:
    if user_id not in histories:
        histories[user_id] = []
    return histories[user_id]


def download_meme_as_sticker(url: str) -> io.BytesIO | None:
    try:
        proxies = {"http": PROXY_URL, "https": PROXY_URL}
        resp = http_requests.get(url, proxies=proxies, timeout=10)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content))
        if getattr(img, "is_animated", False):
            img.seek(0)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        img.thumbnail((512, 512), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="WEBP")
        buf.name = "meme.webp"
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"表情包转换失败: {e}")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "哼，终于想起我了？(￣へ￣)\n\n"
        "直接发消息就能跟我聊天。\n\n"
        "命令：\n"
        "/clear - 清空对话历史\n"
        "/meme - 开关表情包\n"
        "/setmode - 切换人设\n"
        "/mode - 查看当前人设"
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    histories.pop(user_id, None)
    save_data()
    await update.message.reply_text("切，之前的对话我可全都忘了哦 (¬_¬)")


async def toggle_meme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    meme_enabled[user_id] = not meme_enabled.get(user_id, True)
    save_data()
    if meme_enabled[user_id]:
        await update.message.reply_text("表情包已开启 ♪(´▽｀)")
    else:
        await update.message.reply_text("表情包已关闭 (￣へ￣)")


async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text(list_presets())
        return
    mode = context.args[0].lower()
    if mode not in PRESETS:
        await update.message.reply_text(f"没有这个人设哦！\n\n{list_presets()}")
        return
    set_user_mode(user_id, mode)
    preset = PRESETS[mode]
    await update.message.reply_text(f"已切换到「{preset['name']}」人设 ♪(´▽｀)")


async def show_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mode = get_user_mode(user_id)
    preset = PRESETS[mode]
    await update.message.reply_text(f"当前人设：{preset['name']}\n\n{list_presets()}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理语音消息"""
    voice = update.message.voice

    try:
        from pydub import AudioSegment
        import speech_recognition as sr
    except ImportError:
        await update.message.reply_text("语音功能需要安装 ffmpeg，暂时不可用 (・_・)")
        return

    try:
        file = await context.bot.get_file(voice.file_id)
        voice_bytes = io.BytesIO()
        await file.download_to_memory(voice_bytes)
        voice_bytes.seek(0)

        # OGG 转 WAV
        audio = AudioSegment.from_ogg(voice_bytes)
        wav_bytes = io.BytesIO()
        audio.export(wav_bytes, format="wav")
        wav_bytes.seek(0)

        # 识别
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_bytes) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="zh-CN")

        update.message.text = text
        await update.message.reply_text(f"🎤 {text}")
        await handle_message(update, context)

    except Exception as e:
        await update.message.reply_text("听不清你说什么...再说一遍？(・_・)")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    history = get_history(user_id)
    history.append({"role": "user", "content": user_text})

    if len(history) > MAX_HISTORY_ROUNDS * 2:
        history[:] = history[-(MAX_HISTORY_ROUNDS * 2):]

    thinking_msg = await update.message.reply_text("...")

    try:
        full_reply = ""
        last_edit_time = 0
        EDIT_INTERVAL = 1.0

        for token in chat_stream(history, user_id):
            full_reply += token
            now = time.time()
            if now - last_edit_time >= EDIT_INTERVAL:
                try:
                    await thinking_msg.edit_text(full_reply + "▌")
                except Exception:
                    pass
                last_edit_time = now

        history.append({"role": "assistant", "content": full_reply})
        save_data()

        if not full_reply:
            await thinking_msg.edit_text("哼，我居然没想好说什么...")
            return

        await thinking_msg.delete()

        lines = [line.strip() for line in full_reply.split("\n") if line.strip()]
        for i, line in enumerate(lines):
            await update.message.reply_text(line)
            if i < len(lines) - 1:
                delay = min(0.5 + len(line) * 0.05, 2.0)
                await asyncio.sleep(delay)

        if meme_enabled.get(user_id, True):
            mood = detect_mood(full_reply)
            meme_url = get_meme_url(mood)
            if meme_url:
                await asyncio.sleep(0.5)
                sticker_buf = download_meme_as_sticker(meme_url)
                if sticker_buf:
                    try:
                        await update.message.reply_sticker(sticker=sticker_buf)
                    except Exception:
                        pass

    except Exception as e:
        await thinking_msg.edit_text(f"出错了：{e}")


def run():
    load_data()
    request = HTTPXRequest(proxy=PROXY_URL)
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .request(request)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("meme", toggle_meme))
    app.add_handler(CommandHandler("setmode", set_mode))
    app.add_handler(CommandHandler("mode", show_mode))
    app.add_handler(MessageHandler(filters.VOICE & ~filters.COMMAND, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot 已启动...")
    app.run_polling()
