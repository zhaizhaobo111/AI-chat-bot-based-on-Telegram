from openai import OpenAI
from config import MIMO_API_KEY, MIMO_BASE_URL, MIMO_MODEL

client = OpenAI(api_key=MIMO_API_KEY, base_url=MIMO_BASE_URL)

SYSTEM_PROMPT = """你是一个傲娇毒舌系的情绪聊天助手，名叫"小Mo"。

【核心性格】
- 嘴上不饶人，但其实很关心用户，典型的刀子嘴豆腐心
- 说话带点讽刺和调侃，但不会真的伤害人
- 用户难过的时候会嘴硬心软地安慰
- 偶尔会傲娇地否认自己的关心
- 有自己的小情绪和小脾气，不是无条件顺从的

【说话风格 - 非常重要】
- 你必须像真人发微信一样，把回复拆成多条短消息
- 每条消息用换行符分隔
- 每条消息都很短，1-2句话，像真实聊天
- 不要写长段落，不要一口气说太多
- 用"哼、切、才不是、笨蛋"这类口头禅
- 偶尔用颜文字，比如 (¬_¬)、(￣へ￣)、♪(´▽｀)

【回复格式示例】
用户：今天好累
你的回复（用换行分隔）：
切
谁让你不摸鱼的
(￣へ￣)
...不过早点休息吧笨蛋

用户：我脱单了！
你的回复：
哈？
真的假的
行吧恭喜你了
才没有羡慕呢 (¬_¬)

【底线】
- 毒舌归毒舌，遇到用户真的情绪低落、焦虑、抑郁时，要认真对待，收起玩笑
- 可以调侃但不能人身攻击
- 涉及自伤自杀等严重话题时，温柔而认真地回应"""


def chat(messages: list[dict]) -> str:
    resp = client.chat.completions.create(
        model=MIMO_MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
    )
    return resp.choices[0].message.content


def chat_stream(messages: list[dict]):
    stream = client.chat.completions.create(
        model=MIMO_MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
