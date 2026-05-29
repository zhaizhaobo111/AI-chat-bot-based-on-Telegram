import asyncio
import io
import json
import os
import time
import requests as http_requests
from PIL import Image
from telegram import Update
from telegram.constants import ChatAction
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

        await update.message.reply_text(f"🎤 {text}")

        # 直接处理，不修改 update.message.text
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        history = get_history(user_id)
        history.append({"role": "user", "content": text})

        if len(history) > MAX_HISTORY_ROUNDS * 2:
            history[:] = history[-(MAX_HISTORY_ROUNDS * 2):]

        await send_typing(context, chat_id)
        full_reply = ""
        last_typing_time = time.time()

        for token in chat_stream(history, user_id):
            full_reply += token
            now = time.time()
            if now - last_typing_time >= 4:
                await send_typing(context, chat_id)
                last_typing_time = now

        history.append({"role": "assistant", "content": full_reply})
        save_data()

        if full_reply:
            lines = [line.strip() for line in full_reply.split("\n") if line.strip()]
            for i, line in enumerate(lines):
                await update.message.reply_text(line)
                if i < len(lines) - 1:
                    await send_typing(context, chat_id)
                    await asyncio.sleep(min(0.5 + len(line) * 0.05, 2.0))

            if meme_enabled.get(user_id, True):
                mood = detect_mood(full_reply)
                meme_url = get_meme_url(mood)
                if meme_url:
                    sticker_buf = download_meme_as_sticker(meme_url)
                    if sticker_buf:
                        try:
                            await update.message.reply_sticker(sticker=sticker_buf)
                        except Exception:
                            pass

    except Exception as e:
        await update.message.reply_text("听不清你说什么...再说一遍？(・_・)")


async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理贴纸消息"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # 贴纸没有文字内容，用 emoji 作为描述
    sticker = update.message.sticker
    emoji = sticker.emoji or "表情"
    user_text = f"[用户发了一个贴纸: {emoji}]"

    history = get_history(user_id)
    history.append({"role": "user", "content": user_text})

    if len(history) > MAX_HISTORY_ROUNDS * 2:
        history[:] = history[-(MAX_HISTORY_ROUNDS * 2):]

    try:
        await send_typing(context, chat_id)

        full_reply = ""
        last_typing_time = time.time()

        for token in chat_stream(history, user_id):
            full_reply += token
            now = time.time()
            if now - last_typing_time >= 4:
                await send_typing(context, chat_id)
                last_typing_time = now

        history.append({"role": "assistant", "content": full_reply})
        save_data()

        if full_reply:
            lines = [line.strip() for line in full_reply.split("\n") if line.strip()]
            for i, line in enumerate(lines):
                await update.message.reply_text(line)
                if i < len(lines) - 1:
                    await send_typing(context, chat_id)
                    await asyncio.sleep(min(0.5 + len(line) * 0.05, 2.0))

            if meme_enabled.get(user_id, True):
                mood = detect_mood(full_reply)
                meme_url = get_meme_url(mood)
                if meme_url:
                    sticker_buf = download_meme_as_sticker(meme_url)
                    if sticker_buf:
                        try:
                            await update.message.reply_sticker(sticker=sticker_buf)
                        except Exception:
                            pass

    except Exception as e:
        await update.message.reply_text(f"出错了：{e}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理图片消息"""
    from vision import analyze_image

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_bytes = io.BytesIO()
    await file.download_to_memory(image_bytes)
    image_bytes.seek(0)

    analysis = analyze_image(image_bytes.getvalue())

    user_text = f"[用户发送了一张图片]\n{analysis}"
    if update.message.caption:
        user_text = f"[用户发送了一张图片，说: {update.message.caption}]\n{analysis}"

    # 直接调用 AI 处理，不修改 update.message.text
    history = get_history(user_id)
    history.append({"role": "user", "content": user_text})

    if len(history) > MAX_HISTORY_ROUNDS * 2:
        history[:] = history[-(MAX_HISTORY_ROUNDS * 2):]

    try:
        await send_typing(context, chat_id)

        full_reply = ""
        last_typing_time = time.time()

        for token in chat_stream(history, user_id):
            full_reply += token
            now = time.time()
            if now - last_typing_time >= 4:
                await send_typing(context, chat_id)
                last_typing_time = now

        history.append({"role": "assistant", "content": full_reply})
        save_data()

        if not full_reply:
            await update.message.reply_text("哼，我居然没想好说什么...")
            return

        lines = [line.strip() for line in full_reply.split("\n") if line.strip()]
        for i, line in enumerate(lines):
            await update.message.reply_text(line)
            if i < len(lines) - 1:
                await send_typing(context, chat_id)
                delay = min(0.5 + len(line) * 0.05, 2.0)
                await asyncio.sleep(delay)

        if meme_enabled.get(user_id, True):
            mood = detect_mood(full_reply)
            meme_url = get_meme_url(mood)
            if meme_url:
                sticker_buf = download_meme_as_sticker(meme_url)
                if sticker_buf:
                    try:
                        await update.message.reply_sticker(sticker=sticker_buf)
                    except Exception:
                        pass

        try:
            await update.message.set_reaction("👍")
        except Exception:
            pass

    except Exception as e:
        await update.message.reply_text(f"出错了：{e}")


async def send_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    except Exception:
        pass


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    chat_id = update.effective_chat.id

    # 如果是引用回复，把被引用的内容也带上
    reply_to = update.message.reply_to_message
    if reply_to and reply_to.text:
        user_text = f"[引用: {reply_to.text}]\n{user_text}"

    history = get_history(user_id)
    history.append({"role": "user", "content": user_text})

    if len(history) > MAX_HISTORY_ROUNDS * 2:
        history[:] = history[-(MAX_HISTORY_ROUNDS * 2):]

    try:
        # 显示"正在输入"
        await send_typing(context, chat_id)

        full_reply = ""
        last_typing_time = time.time()

        for token in chat_stream(history, user_id):
            full_reply += token
            now = time.time()
            # 每4秒续一次 typing 状态（Telegram 约5秒过期）
            if now - last_typing_time >= 4:
                await send_typing(context, chat_id)
                last_typing_time = now

        history.append({"role": "assistant", "content": full_reply})
        save_data()

        if not full_reply:
            await update.message.reply_text("哼，我居然没想好说什么...")
            return

        # 逐条发送，每条之间保持 typing 状态
        lines = [line.strip() for line in full_reply.split("\n") if line.strip()]
        for i, line in enumerate(lines):
            await update.message.reply_text(line)
            if i < len(lines) - 1:
                await send_typing(context, chat_id)
                delay = min(0.5 + len(line) * 0.05, 2.0)
                await asyncio.sleep(delay)

        # 发送表情包
        if meme_enabled.get(user_id, True):
            mood = detect_mood(full_reply)
            meme_url = get_meme_url(mood)
            if meme_url:
                sticker_buf = download_meme_as_sticker(meme_url)
                if sticker_buf:
                    try:
                        await update.message.reply_sticker(sticker=sticker_buf)
                    except Exception:
                        pass

    except Exception as e:
        await update.message.reply_text(f"出错了：{e}")


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
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo))
    app.add_handler(MessageHandler(filters.Sticker.ALL & ~filters.COMMAND, handle_sticker))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot 已启动...")
    app.run_polling()
