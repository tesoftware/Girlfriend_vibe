import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

from llm_client import LLMClient
from memory_manager import MemoryManager

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

llm_client = LLMClient()
memory_manager = MemoryManager()

CHAT_LOGS_DIR = "chat_logs"
if not os.path.exists(CHAT_LOGS_DIR):
    os.makedirs(CHAT_LOGS_DIR)


def load_prompt(prompt_name):
    prompt_path = os.path.join("prompts", f"{prompt_name}.txt")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/chat")
def chat_page():
    return send_from_directory("static", "chat.html")


@app.route("/api/config", methods=["GET"])
def get_config():
    config = memory_manager.get_config()
    return jsonify(config)


@app.route("/api/soul-name", methods=["GET"])
def get_soul_name():
    config = memory_manager.get_config()
    soul_name = config.get("soul_name", "")
    return jsonify({"soul_name": soul_name})


@app.route("/api/config", methods=["POST"])
def update_config():
    data = request.json
    config = memory_manager.get_config()

    if "llm" in data:
        config["llm"] = data["llm"]
        llm_client.reload_config()

    memory_manager.save_config(config)
    return jsonify({"success": True})


@app.route("/api/provider", methods=["POST"])
def set_provider():
    data = request.json
    provider = data.get("provider")
    if provider:
        llm_client.set_provider(provider)
        return jsonify({"success": True, "provider": provider})
    return jsonify({"success": False, "error": "Provider not specified"}), 400


@app.route("/api/test-connection", methods=["POST"])
def test_connection():
    result = llm_client.test_connection()
    return jsonify(result)


@app.route("/api/memories", methods=["GET"])
def get_memories():
    memory_files = memory_manager.get_memory_files()
    memories = {}
    for mf in memory_files:
        memories[mf["id"]] = memory_manager.get_memory_content(mf["id"])
    return jsonify({"files": memory_files, "contents": memories})


@app.route("/api/memories/<file_id>", methods=["GET"])
def get_memory(file_id):
    content = memory_manager.get_memory_content(file_id)
    return jsonify({"id": file_id, "content": content})


@app.route("/api/memories/<file_id>", methods=["POST"])
def append_memory(file_id):
    data = request.json
    content = data.get("content", "")
    if memory_manager.append_memory(file_id, content):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "File not found"}), 404


@app.route("/api/memories/<file_id>", methods=["PUT"])
def update_memory(file_id):
    data = request.json
    content = data.get("content", "")
    if memory_manager.update_memory(file_id, content):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "File not found"}), 404


@app.route("/api/ask-question", methods=["POST"])
def ask_question():
    data = request.json
    category = data.get("category", "basic")

    prompt_template = load_prompt("ask_question")
    existing_content = memory_manager.get_memory_content(category)
    category_desc = memory_manager.get_category_info(category)

    prompt = prompt_template.format(
        category=category,
        category_desc=category_desc,
        existing_content=existing_content or "(No content yet)",
    )

    try:
        response = llm_client.chat(prompt)
        return jsonify({"success": True, "question": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/generate-memory", methods=["POST"])
def generate_memory():
    data = request.json
    user_prompt = data.get("prompt", "")
    category = data.get("category", "basic")

    prompt_template = load_prompt("generate_memory")
    basic_info = memory_manager.get_memory_content("basic")
    social_relations = memory_manager.get_memory_content("social")

    prompt = prompt_template.format(
        basic_info=basic_info or "(Not set yet)",
        social_relations=social_relations or "(Not set yet)",
        user_prompt=user_prompt,
        category=category,
    )

    try:
        response = llm_client.chat(prompt)
        return jsonify({"success": True, "memory": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/polish", methods=["POST"])
def polish_text():
    data = request.json
    input_text = data.get("text", "")

    prompt_template = load_prompt("polish")
    basic_info = memory_manager.get_memory_content("basic")

    prompt = prompt_template.format(
        input=input_text,
        basic_info=basic_info or "(Not set yet)",
    )

    try:
        response = llm_client.chat(prompt)
        return jsonify({"success": True, "polished": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/check-consistency", methods=["POST"])
def check_consistency():
    prompt_template = load_prompt("consistency")
    memories = memory_manager.get_all_memories()

    prompt = prompt_template.format(
        basic=memories.get("basic", "(Empty)"),
        social_relations=memories.get("social", "(Empty)"),
        special_experience=memories.get("experience", "(Empty)"),
        daily_chores=memories.get("daily", "(Empty)"),
        events=memories.get("events", "(Empty)"),
        preferences=memories.get("preferences", "(Empty)"),
        values=memories.get("values", "(Empty)"),
        emotions=memories.get("emotions", "(Empty)"),
    )

    try:
        response = llm_client.chat(prompt)
        return jsonify({"success": True, "result": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/generate-dialogue-style", methods=["POST"])
def generate_dialogue_style():
    prompt_template = load_prompt("dialogue_style")

    basic = memory_manager.get_memory_content("basic")
    preferences = memory_manager.get_memory_content("preferences")
    emotions = memory_manager.get_memory_content("emotions")

    prompt = prompt_template.format(
        basic=basic or "(Not set yet)",
        preferences=preferences or "(Not set yet)",
        emotions=emotions or "(Not set yet)",
    )

    try:
        response = llm_client.chat(prompt)
        return jsonify({"success": True, "dialogue_style": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/timeline", methods=["GET"])
def get_timeline():
    timeline = memory_manager.get_timeline()
    return jsonify({"timeline": timeline})


@app.route("/api/export-soul", methods=["POST"])
def export_soul():
    try:
        soul_content = memory_manager.generate_soul()
        return jsonify({"success": True, "content": soul_content})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat_with_girlfriend():
    data = request.json
    user_message = data.get("message", "")
    chat_history = data.get("history", [])

    if not user_message.strip():
        return jsonify({"success": False, "error": "Message is empty"}), 400

    prompt_template = load_prompt("chat")
    memories = memory_manager.get_all_memories()
    
    config = memory_manager.get_config()
    soul_name = config.get("soul_name", "TA")

    history_text = ""
    if chat_history:
        for msg in chat_history[-10:]:
            role = "男朋友" if msg.get("role") == "user" else soul_name
            history_text += f"{role}: {msg.get('content', '')}\n"

    prompt = prompt_template.format(
        soul_name=soul_name,
        basic=memories.get("basic", "(未设定)"),
        social_relations=memories.get("social", "(未设定)"),
        experience=memories.get("experience", "(未设定)"),
        preferences=memories.get("preferences", "(未设定)"),
        values=memories.get("values", "(未设定)"),
        emotions=memories.get("emotions", "(未设定)"),
        chat_history=history_text or "(这是你们今天的第一次对话)",
        user_message=user_message,
    )

    try:
        response = llm_client.chat(prompt)
        return jsonify({"success": True, "reply": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/save-chat", methods=["POST"])
def save_chat():
    data = request.json
    messages = data.get("messages", [])

    if not messages:
        return jsonify({"success": False, "error": "No messages to save"}), 400

    now = datetime.now()
    filename = now.strftime("%Y%m%d_%H%M%S") + ".md"
    filepath = os.path.join(CHAT_LOGS_DIR, filename)

    config = memory_manager.get_config()
    soul_name = config.get("soul_name", "TA")
    
    content_lines = [
        f"# 和{soul_name}的聊天记录",
        f"",
        f"**日期**: {now.strftime('%Y年%m月%d日 %H:%M:%S')}",
        f"",
        f"---",
        f"",
    ]

    for msg in messages:
        role = "我" if msg.get("role") == "user" else soul_name
        time_str = msg.get("time", "")
        content = msg.get("content", "")
        content_lines.append(f"**{role}** ({time_str})")
        content_lines.append(f"")
        content_lines.append(f"> {content}")
        content_lines.append(f"")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(content_lines))

    return jsonify({"success": True, "filename": filename, "path": filepath})


if __name__ == "__main__":
    config = memory_manager.get_config()
    port = config.get("app", {}).get("port", 4911)
    print(f"Starting Memory Workshop on http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=True)
