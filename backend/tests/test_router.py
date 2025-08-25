# tests/full_flow_http.py
# -*- coding: utf-8 -*-
"""
交互式端到端体验脚本（HTTP 版）
- 依赖：后端 FastAPI 已启动（默认 http://localhost:8000）
- 自动适配常见字段名；打印完整 JSON 便于排错
- 流程：/health -> /chat/route -> 问答循环(/chat/answer) -> /chat/finish -> /chat/dimension-result
"""
import os
import sys
import json
import time
from typing import Any, Dict, Optional

import requests

API_BASE = os.getenv("API_BASE", "http://localhost:8000")


def _pretty(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return str(obj)


def _post(path: str, payload: Dict[str, Any]) -> requests.Response:
    url = API_BASE.rstrip("/") + path
    return requests.post(url, json=payload, timeout=60)


def _get(path: str) -> requests.Response:
    url = API_BASE.rstrip("/") + path
    return requests.get(url, timeout=30)


def _field(payload: Dict[str, Any], *candidates: str, default=None):
    for k in candidates:
        if k in payload and payload[k] is not None:
            return payload[k]
    return default


def health_check() -> bool:
    try:
        r = _get("/health")
        ok = r.ok
        print("\n=== /health ===")
        print(r.status_code, r.text)
        return ok
    except Exception as e:
        print("健康检查失败：", e)
        return False


def route_session(user_id: str, initial_text: str) -> Dict[str, Any]:
    """尽量兼容字段名：text/query/message"""
    payload_variants = [
        {"user_id": user_id, "text": initial_text},
        {"user_id": user_id, "query": initial_text},
        {"user_id": user_id, "message": initial_text},
        {"text": initial_text},  # 最小化
    ]
    last_err = None
    for p in payload_variants:
        try:
            r = _post("/chat/route", p)
            if r.ok:
                print("\n=== /chat/route payload ===")
                print(_pretty(p))
                print("\n=== /chat/route response ===")
                print(_pretty(r.json()))
                return r.json()
            last_err = (r.status_code, r.text)
        except Exception as e:
            last_err = repr(e)
    raise RuntimeError(f"/chat/route 调用失败: {last_err}")


def ask_next_question(session_id: str) -> Optional[Dict[str, Any]]:
    """有些实现会提供 /chat/question；也可能直接在 /answer 返回下一题"""
    try:
        r = _post("/chat/question", {"session_id": session_id})
        if r.ok:
            print("\n=== /chat/question response ===")
            print(_pretty(r.json()))
            return r.json()
    except Exception:
        pass
    return None


def send_answer(session_id: str, answer_text: str) -> Dict[str, Any]:
    """尽量兼容字段名：answer/answer_text/text/message"""
    payload_variants = [
        {"session_id": session_id, "answer": answer_text},
        {"session_id": session_id, "answer_text": answer_text},
        {"session_id": session_id, "text": answer_text},
        {"session_id": session_id, "message": answer_text},
        # 有些实现可能还需要 echo question_id，但通常后端在 session 里维护指针
    ]
    last_err = None
    for p in payload_variants:
        try:
            r = _post("/chat/answer", p)
            if r.ok:
                print("\n=== /chat/answer payload ===")
                print(_pretty(p))
                print("\n=== /chat/answer response ===")
                print(_pretty(r.json()))
                return r.json()
            last_err = (r.status_code, r.text)
        except Exception as e:
            last_err = repr(e)
    raise RuntimeError(f"/chat/answer 调用失败: {last_err}")


def finish_session(session_id: str) -> Dict[str, Any]:
    try:
        r = _post("/chat/finish", {"session_id": session_id})
        if r.ok:
            print("\n=== /chat/finish response ===")
            print(_pretty(r.json()))
            return r.json()
        raise RuntimeError(f"/chat/finish 失败: {r.status_code} {r.text}")
    except Exception as e:
        raise RuntimeError(f"/chat/finish 调用异常: {e}")


def fetch_dimension_result(session_id: str, pnm: Optional[str] = None) -> Dict[str, Any]:
    payload = {"session_id": session_id}
    if pnm:
        payload["pnm"] = pnm
    try:
        r = _post("/chat/dimension-result", payload)
        if r.ok:
            print("\n=== /chat/dimension-result response ===")
            print(_pretty(r.json()))
            return r.json()
        raise RuntimeError(f"/chat/dimension-result 失败: {r.status_code} {r.text}")
    except Exception as e:
        raise RuntimeError(f"/chat/dimension-result 调用异常: {e}")


def main():
    print("API_BASE =", API_BASE)
    if not health_check():
        print("后端未就绪。请先运行：uvicorn app.main:app --reload")
        sys.exit(2)

    # 1) 路由阶段：建议先用能命中词典的句子体验
    #   例如：夜间呼吸困难 + 进食咳嗽（会命中 Breathing / Swallowing）
    default_text = "I wake up breathless at night and cough when eating."
    user_text = input(f"\n请输入你的开场描述（回车用默认）\n> ") or default_text

    route_res = route_session(user_id="demo_user", initial_text=user_text)
    session_id = _field(route_res, "session_id", "sid", "sessionId")
    if not session_id:
        print("未返回 session_id，响应：", _pretty(route_res))
        sys.exit(3)

    # 打印已经锁定的 pnm/term（如果有）
    current_pnm = _field(route_res, "pnm", "current_pnm")
    current_term = _field(route_res, "term", "current_term")
    print(f"\n当前定位：pnm={current_pnm} term={current_term}")

    # 2) 问答循环
    #   从 /chat/route 的响应里，尝试取首题；否则调用 /chat/question
    q_obj = _field(route_res, "question", "next_question")
    if not q_obj:
        q_res = ask_next_question(session_id)
        q_obj = _field(q_res or {}, "question", "next_question")

    turns = 0
    MAX_TURNS = 12
    while turns < MAX_TURNS and q_obj:
        q_text = _field(q_obj, "text", "prompt", "question_text", "main")
        print("\n=== 问题 ===")
        print(q_text or str(q_obj))
        ans = input("\n你的回答：\n> ").strip()
        if not ans:
            ans = "Prefer not to say."

        ans_res = send_answer(session_id, ans)

        # 可能返回下一题/跟进题/或结束标记
        q_obj = _field(ans_res, "next_question", "question", "followup_question")
        done_flag = _field(ans_res, "done", "is_done", "finished", default=False)
        fsm_state = _field(ans_res, "fsm_state", default="")
        turns += 1

        # 打印 info 提示卡（如果有）
        info_cards = _field(ans_res, "info_cards", "info", default=[])
        if info_cards:
            print("\n=== 信息卡（仅打印标题）===")
            for i, card in enumerate(info_cards, 1):
                title = card.get("title") or f"Card {i}"
                print(f"- {title}")

        if done_flag or (fsm_state and fsm_state.upper() in {"FINISH", "FINISHED", "DONE"}):
            print("\n会话标记完成。")
            break

        # 小憩，避免刷屏
        time.sleep(0.2)

    # 3) 结束并取结果
    finish_res = finish_session(session_id)

    # 如果后端支持按维度取结果，再取一次当前维度
    if current_pnm:
        try:
            fetch_dimension_result(session_id, current_pnm)
        except Exception as e:
            print("dimension-result 获取失败：", e)

    print("\n=== 全流程结束 ===")


if __name__ == "__main__":
    main()
