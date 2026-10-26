import json
import re
import requests


def parse_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def call_llm(api_key, base_url, model, system_prompt, user_content):
    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.3,
        },
        timeout=600,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"API returns {resp.status_code}: {resp.text[:300]}")
    content = resp.json()["choices"][0]["message"]["content"]
    return parse_json(content)