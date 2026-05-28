from openai import OpenAI
from config import MIMO_API_KEY, MIMO_BASE_URL, MIMO_MODEL
from personalities import get_preset, DEFAULT_PRESET

client = OpenAI(api_key=MIMO_API_KEY, base_url=MIMO_BASE_URL)

# 用户人设 {user_id: preset_name}
user_modes: dict[int, str] = {}


def get_system_prompt(user_id: int) -> str:
    mode = user_modes.get(user_id, DEFAULT_PRESET)
    return get_preset(mode)["prompt"]


def set_user_mode(user_id: int, mode: str):
    user_modes[user_id] = mode


def get_user_mode(user_id: int) -> str:
    return user_modes.get(user_id, DEFAULT_PRESET)


def chat(messages: list[dict], user_id: int) -> str:
    resp = client.chat.completions.create(
        model=MIMO_MODEL,
        messages=[{"role": "system", "content": get_system_prompt(user_id)}, *messages],
    )
    return resp.choices[0].message.content


def chat_stream(messages: list[dict], user_id: int):
    stream = client.chat.completions.create(
        model=MIMO_MODEL,
        messages=[{"role": "system", "content": get_system_prompt(user_id)}, *messages],
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
