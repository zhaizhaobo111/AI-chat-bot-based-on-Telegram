import random

CDN = "https://fastly.jsdelivr.net/gh/willow-god/owo"

# 情绪到表情包的映射（每个情绪对应多张图，随机选）
EMOJI_MAP = {
    "happy": [
        f"{CDN}/liushen/liushen-happy.png",
        f"{CDN}/liushen/liushen-congratulation.png",
        f"{CDN}/liushen/liushen-good.png",
        f"{CDN}/blobcat/blobcathappy.png",
        f"{CDN}/blobcat/blobcatfingerguns.png",
        f"{CDN}/blobcat/blobcattriumph.png",
        f"{CDN}/bilibili/bilibili-可爱.png",
        f"{CDN}/bilibili/bilibili-好耶.png",
        f"{CDN}/linedog/linedog-开心.gif",
        f"{CDN}/linedog/linedog-好棒.gif",
        f"{CDN}/linedog/linedog-庆祝.gif",
        f"{CDN}/linedog/linedog-好耶.gif",
    ],
    "angry": [
        f"{CDN}/liushen/liushen-angry.png",
        f"{CDN}/liushen/liushen-hityou.png",
        f"{CDN}/liushen/liushen-shoot.png",
        f"{CDN}/blobcat/blobcatangry.png",
        f"{CDN}/blobcat/blobcatsnapped.png",
        f"{CDN}/blobcat/blobcatflip.png",
        f"{CDN}/bilibili/bilibili-发怒.png",
        f"{CDN}/linedog/linedog-哼.gif",
        f"{CDN}/linedog/linedog-打你.gif",
        f"{CDN}/linedog/linedog-威胁.gif",
    ],
    "sad": [
        f"{CDN}/liushen/liushen-sad.png",
        f"{CDN}/liushen/liushen-cry.png",
        f"{CDN}/liushen/liushen-sobface.png",
        f"{CDN}/blobcat/blobcatcry.png",
        f"{CDN}/blobcat/blobcatsadreach.png",
        f"{CDN}/blobcat/blobcatheartbroken.png",
        f"{CDN}/bilibili/bilibili-大哭.png",
        f"{CDN}/bilibili/bilibili-委屈.png",
        f"{CDN}/linedog/linedog-难过.gif",
        f"{CDN}/linedog/linedog-沮丧.gif",
        f"{CDN}/linedog/linedog-画圈圈.gif",
    ],
    "shy": [
        f"{CDN}/liushen/liushen-shy.png",
        f"{CDN}/liushen/liushen-peek.png",
        f"{CDN}/blobcat/blobcatblush.png",
        f"{CDN}/blobcat/blobcatmelt.png",
        f"{CDN}/blobcat/blobcatsnuggle.png",
        f"{CDN}/bilibili/bilibili-害羞.png",
        f"{CDN}/bilibili/bilibili-偷笑.png",
        f"{CDN}/linedog/linedog-紧张.gif",
        f"{CDN}/linedog/linedog-探头.gif",
    ],
    "smug": [
        f"{CDN}/liushen/liushen-hehesmile.png",
        f"{CDN}/liushen/liushen-prond.png",
        f"{CDN}/liushen/liushen-slacking.png",
        f"{CDN}/blobcat/blobcatcoffee.png",
        f"{CDN}/blobcat/blobcatthink.png",
        f"{CDN}/blobcat/blobcatverified.png",
        f"{CDN}/bilibili/bilibili-坏笑.png",
        f"{CDN}/bilibili/bilibili-大佬.png",
        f"{CDN}/linedog/linedog-晃脚脚.gif",
        f"{CDN}/linedog/linedog-翘脚脚.gif",
    ],
    "love": [
        f"{CDN}/liushen/liushen-loveyou.png",
        f"{CDN}/liushen/liushen-cutehold.png",
        f"{CDN}/blobcat/blobcatlove.png",
        f"{CDN}/blobcat/blobcatheart.png",
        f"{CDN}/blobcat/blobcatkissheart.png",
        f"{CDN}/bilibili/bilibili-亲亲.png",
        f"{CDN}/linedog/linedog-送你花花.gif",
        f"{CDN}/linedog/linedog-转圈.gif",
    ],
    "surprised": [
        f"{CDN}/liushen/liushen-mindblown.png",
        f"{CDN}/liushen/liushen-petrified.png",
        f"{CDN}/liushen/liushen-confused.png",
        f"{CDN}/blobcat/blobcatshocked.png",
        f"{CDN}/blobcat/blobcatopenmouth.png",
        f"{CDN}/blobcat/blobcatdisturbed.png",
        f"{CDN}/bilibili/bilibili-惊吓.png",
        f"{CDN}/bilibili/bilibili-呆.png",
        f"{CDN}/linedog/linedog-惊.gif",
        f"{CDN}/linedog/linedog-震惊.gif",
        f"{CDN}/linedog/linedog-惊讶.gif",
    ],
    "eating": [
        f"{CDN}/liushen/liushen-chowdown.png",
        f"{CDN}/blobcat/blobcatnomblobcat.png",
        f"{CDN}/bilibili/bilibili-好吃.png",
    ],
    "sleepy": [
        f"{CDN}/liushen/liushen-sleep.png",
        f"{CDN}/liushen/liushen-tired.png",
        f"{CDN}/blobcat/blobcatcomfy.png",
        f"{CDN}/bilibili/bilibili-困.png",
        f"{CDN}/linedog/linedog-颓废.gif",
    ],
    "default": [
        f"{CDN}/liushen/liushen-helpless.png",
        f"{CDN}/liushen/liushen-sigh.png",
        f"{CDN}/blobcat/blobcatneutral.png",
        f"{CDN}/blobcat/blobcatwave.png",
        f"{CDN}/blobcat/blobcatpeekaboo.png",
        f"{CDN}/bilibili/bilibili-微笑.png",
        f"{CDN}/bilibili/bilibili-思考.png",
        f"{CDN}/linedog/linedog-指.gif",
        f"{CDN}/linedog/linedog-来了.gif",
        f"{CDN}/linedog/linedog-歪头.gif",
    ],
}

# 触发词到情绪的映射（长词优先，避免短词误匹配）
TRIGGER_MAP = {
    "开心": "happy", "高兴": "happy", "哈哈": "happy", "太好了": "happy",
    "恭喜": "happy", "厉害": "happy", "加油": "happy", "好耶": "happy",
    "生气": "angry", "讨厌": "angry", "烦": "angry",
    "笨蛋": "angry", "打你": "angry",
    "难过": "sad", "伤心": "sad", "哭": "sad", "累": "sad",
    "抱歉": "sad", "辛苦": "sad", "委屈": "sad",
    "害羞": "shy", "脸红": "shy", "不好意思": "shy",
    "切": "smug", "才不是": "smug", "嘚瑟": "smug", "哼": "smug",
    "喜欢": "love", "爱": "love", "想你": "love", "亲": "love",
    "惊": "surprised", "不会吧": "surprised", "真的吗": "surprised",
    "吃": "eating", "饿": "eating", "奶茶": "eating", "火锅": "eating",
    "困": "sleepy", "睡觉": "sleepy", "晚安": "sleepy",
}


def detect_mood(text: str) -> str:
    # 按触发词长度降序，长词优先匹配
    sorted_triggers = sorted(TRIGGER_MAP.items(), key=lambda x: len(x[0]), reverse=True)
    for trigger, mood in sorted_triggers:
        if trigger in text:
            return mood
    return "default"


def get_meme_url(mood: str) -> str | None:
    candidates = EMOJI_MAP.get(mood, EMOJI_MAP["default"])
    return random.choice(candidates)
