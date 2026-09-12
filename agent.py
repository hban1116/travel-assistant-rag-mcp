"""Agent — routes to RAG and/or MCP tools, synthesizes final answer via Groq."""
import os
import re
import json
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

import prompts as P
import rag
import mcp_clients as mcp

load_dotenv()

LLM_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
llm = ChatGroq(model=LLM_MODEL, temperature=0)


def _classify(question: str) -> str:
    chain = PromptTemplate.from_template(P.ROUTER_PROMPT) | llm | StrOutputParser()
    raw = chain.invoke({"question": question}).strip().upper()
    for tok in ["COMBINED", "WEATHER", "CURRENCY", "KB", "NONE"]:
        if tok in raw:
            return tok
    return "KB"


def _history_str(history):
    return "\n".join(f"{m['role']}: {m['content']}" for m in history[-6:])


def _safe_tool_call(fn, *args, **kwargs):
    try:
        res = fn(*args, **kwargs)
        if isinstance(res, dict) and res.get("error"):
            return {"error": res["error"]}
        return res
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def _parse_amount(text: str):
    m = re.search(r"(\d[\d,]*\.?\d*)", text.replace(" ", ""))
    amount = float(m.group(1).replace(",", "")) if m else None
    codes = re.findall(r"\b([A-Z]{3})\b", text.upper())
    frm = codes[0] if len(codes) >= 1 else "INR"
    to = codes[1] if len(codes) >= 2 else "SGD"
    return amount, frm, to


def handle_message(user_input: str, history=None, preferences=None) -> dict:
    history = history or []
    preferences = preferences or {}
    route = _classify(user_input)

    if route == "KB":
        r = rag.rag_search(user_input)
        return {"type": "rag", "answer": r["answer"], "sources": r["sources"]}

    if route == "WEATHER":
        w = _safe_tool_call(mcp.get_weather_sync, "Singapore", 3)
        if w.get("error"):
            return {"type": "error",
                    "answer": "Weather service is unavailable right now.",
                    "tool_data": w}
        lines = [f"- {d['date']}: {d['tmin_c']}-{d['tmax_c']}C, rain {d['rain_mm']}mm"
                 for d in w["days"]]
        return {"type": "weather",
                "answer": "3-day Singapore forecast [Source: MCP weather tool]:\n" + "\n".join(lines),
                "tool_data": w}

    if route == "CURRENCY":
        amount, frm, to = _parse_amount(user_input)
        if amount is None:
            return {"type": "error", "answer": "I couldn't detect an amount to convert."}
        c = _safe_tool_call(mcp.convert_currency_sync, amount, frm, to)
        if c.get("error"):
            return {"type": "error",
                    "answer": "Currency service is unavailable right now.",
                    "tool_data": c}
        return {"type": "currency",
                "answer": f"{amount} {frm} = {c['converted']:.2f} {to} "
                          f"(rate {c['rate']:.4f}) [Source: MCP currency tool]",
                "tool_data": c}

    # COMBINED
    r = rag.rag_search(user_input)
    w = _safe_tool_call(mcp.get_weather_sync, "Singapore", 5)

    c = None
    if re.search(r"\b(convert|inr|usd|sgd|budget|currency)\b", user_input, re.I):
        amount, frm, to = _parse_amount(user_input)
        if amount:
            c = _safe_tool_call(mcp.convert_currency_sync, amount, frm, to)

    chain = PromptTemplate.from_template(P.COMBINED_PROMPT) | llm | StrOutputParser()
    answer = chain.invoke({
        "kb": r["answer"],
        "weather": json.dumps(w, indent=2) if not w.get("error") else "tool unavailable",
        "currency": json.dumps(c, indent=2) if c else "not requested",
        "history": _history_str(history),
        "preferences": json.dumps(preferences),
        "question": user_input,
    })
    return {
        "type": "combined",
        "answer": answer,
        "sources": r["sources"],
        "tool_data": {"weather": w, "currency": c},
    }


if __name__ == "__main__":
    import json as _j
    for label, q in [
        ("KB", "What are must-visit attractions in Singapore?"),
        ("WEATHER", "Weather in Singapore next 3 days?"),
        ("CURRENCY", "Convert INR 50000 to SGD"),
        ("COMBINED", "Plan a 3-day Singapore itinerary for next week and adjust for weather"),
    ]:
        print(f"\n=== {label} ===")
        out = handle_message(q)
        print(_j.dumps(out, indent=2)[:600])