import asyncio
import io
import time
import requests as http_requests
from PIL import Image
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.request import HTTPXRequest

from config import TELEGRAM_BOT_TOKEN, MAX_HISTORY_ROUNDS, PROXY_URL
from ai_client import chat_stream
from meme_manager import detect_mood, get_meme_url

# 每个用户的对话历史
histories: dict[int, list[dict]] = {}
# 表情包开关
meme_enabled: dict[int, bool] = {}


def get_history(user_id: int) -> list[dict]:
    if user_id not in histories:
        histories[user_id] = []
    return histories[user_id]


def download_meme_as_sticker(url: str) -> io.BytesIO | None:
    """下载图片并转为 Telegram 贴纸格式 (WebP, 512x512)"""
    try:
        proxies = {"http": PROXY_URL, "https": PROXY_URL}
        resp = http_requests.get(url, proxies=proxies, timeout=10)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content))
        # GIF 取第一帧
        if getattr(img, "is_animated", False):
            img.seek(0)
        # 转为 RGBA
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        # 缩放到 512x512 以内
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
        "/meme - 开关表情包"
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    histories.pop(user_id, None)
    await update.message.reply_text("切，之前的对话我可全都忘了哦 (¬_¬)")


async def toggle_meme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    meme_enabled[user_id] = not meme_enabled.get(user_id, True)
    if meme_enabled[user_id]:
        await update.message.reply_text("表情包已开启 ♪(´▽｀)")
    else:
        await update.message.reply_text("表情包已关闭 (￣へ￣)")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    history = get_history(user_id)
    history.append({"role": "user", "content": user_text})

    if len(history) > MAX_HISTORY_ROUNDS * 2:
        history[:] = history[-(MAX_HISTORY_ROUNDS * 2):]

    # 显示"正在输入"
    thinking_msg = await update.message.reply_text("...")

    try:
        # 流式收集完整回复
        full_reply = ""
        last_edit_time = 0
        EDIT_INTERVAL = 1.0

        for token in chat_stream(history):
            full_reply += token
            now = time.time()
            if now - last_edit_time >= EDIT_INTERVAL:
                try:
                    await thinking_msg.edit_text(full_reply + "▌")
                except Exception:
                    pass
                last_edit_time = now

        history.append({"role": "assistant", "content": full_reply})

        if not full_reply:
            await thinking_msg.edit_text("哼，我居然没想好说什么...")
            return

        # 删除"思考中"消息
        await thinking_msg.delete()

        # 按换行拆分，逐条发送
        lines = [line.strip() for line in full_reply.split("\n") if line.strip()]
        for i, line in enumerate(lines):
            await update.message.reply_text(line)
            # 每条消息之间加随机延迟，模拟真人打字
            if i < len(lines) - 1:
                delay = min(0.5 + len(line) * 0.05, 2.0)
                await asyncio.sleep(delay)

        # 最后一条消息后发送表情包
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot 已启动...")
    app.run_polling()
