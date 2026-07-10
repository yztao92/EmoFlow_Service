#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话质量测试脚本示例

用法:
    python scripts/qa_chat_test_example.py --base-url http://localhost:8000
"""

import argparse
import json
import uuid

import requests


QA_EMAIL = "qa-test@emoflow.internal"
QA_PASSWORD = "QaTest2024!"


def login(base_url: str) -> str:
    resp = requests.post(
        f"{base_url}/auth/qa",
        json={"username": QA_EMAIL, "password": QA_PASSWORD},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    print(f"登录成功: user_id={data['user']['id']}, unlimited={data['user']['unlimited_chat']}")
    return data["jwt"]


def clear_memories(base_url: str, token: str) -> None:
    resp = requests.delete(f"{base_url}/test/memory", headers={"token": token}, timeout=30)
    resp.raise_for_status()
    print("清除记忆:", resp.json())


def write_memories(base_url: str, token: str, memories: list[str]) -> None:
    resp = requests.put(
        f"{base_url}/test/memory",
        headers={"token": token},
        json={"memories": memories, "replace": True},
        timeout=30,
    )
    resp.raise_for_status()
    print("写入记忆:", resp.json())


def chat(base_url: str, token: str, session_id: str, message: str) -> str:
    resp = requests.post(
        f"{base_url}/chat",
        headers={"token": token},
        json={"session_id": session_id, "user_message": message},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    answer = data["response"]["answer"]
    print(f"用户: {message}")
    print(f"助手: {answer}")
    return answer


def main() -> None:
    parser = argparse.ArgumentParser(description="EmoFlow 对话质量测试示例")
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()

    token = login(args.base_url)
    clear_memories(args.base_url, token)
    write_memories(
        args.base_url,
        token,
        [
            "2026-07-01 用户提到最近工作压力很大，经常加班到很晚",
            "2026-07-05 用户说周末去公园散步，心情好了一些",
        ],
    )

    session_id = f"qa-{uuid.uuid4().hex[:8]}"
    chat(args.base_url, token, session_id, "你好，还记得我上次跟你聊过什么吗？")


if __name__ == "__main__":
    main()
