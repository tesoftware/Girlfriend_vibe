import os
import json
import re
from datetime import datetime


class MemoryManager:
    def __init__(self, memories_dir="memories", config_path="config.json"):
        self.memories_dir = memories_dir
        self.config_path = config_path
        self._ensure_directories()

    def _ensure_directories(self):
        if not os.path.exists(self.memories_dir):
            os.makedirs(self.memories_dir)

    def get_config(self):
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_config(self, config):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def get_memory_files(self):
        config = self.get_config()
        return config.get("memory_files", [])

    def get_memory_content(self, file_id):
        config = self.get_config()
        memory_files = config.get("memory_files", [])

        for mf in memory_files:
            if mf["id"] == file_id:
                file_path = os.path.join(self.memories_dir, mf["file"])
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        return f.read()
                return ""
        return ""

    def get_all_memories(self):
        memories = {}
        for mf in self.get_memory_files():
            memories[mf["id"]] = self.get_memory_content(mf["id"])
        return memories

    def append_memory(self, file_id, content):
        config = self.get_config()
        memory_files = config.get("memory_files", [])

        for mf in memory_files:
            if mf["id"] == file_id:
                file_path = os.path.join(self.memories_dir, mf["file"])
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write("\n" + content.strip() + "\n")
                return True
        return False

    def extract_name_from_basic(self, content):
        """从基本设定中提取姓名"""
        # 匹配格式: - 姓名: xxx 或 姓名: xxx 或 * 姓名: xxx
        patterns = [
            r"[-*]\s*姓名\s*[:：]\s*([^\n\r]+)",  # - 姓名: xxx 或 * 姓名: xxx
            r"^姓名\s*[:：]\s*([^\n\r]+)",  # 姓名: xxx (行首)
            r"姓名\s*[:：]\s*([^\n\r]+)",  # 姓名: xxx (任意位置)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                name = match.group(1).strip()
                # 移除可能的标记符号和空白
                name = re.sub(r'^[-*\s]+', '', name)
                name = re.sub(r'[-*\s]+$', '', name)
                if name:
                    return name
        return None

    def update_memory(self, file_id, content):
        config = self.get_config()
        memory_files = config.get("memory_files", [])

        for mf in memory_files:
            if mf["id"] == file_id:
                file_path = os.path.join(self.memories_dir, mf["file"])
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                
                # 如果保存的是基本设定，自动解析姓名并更新 soul_name
                if file_id == "basic":
                    name = self.extract_name_from_basic(content)
                    if name:
                        config["soul_name"] = name
                        self.save_config(config)
                
                return True
        return False

    def get_timeline(self):
        content = self.get_memory_content("experience")
        timeline = []

        pattern = r"##\s*(\d{4})-?(\d{2})?\s+(.+)"
        matches = re.findall(pattern, content)

        for match in matches:
            year = match[0]
            month = match[1] if match[1] else "01"
            title = match[2].strip()
            timeline.append({
                "date": f"{year}-{month}",
                "year": int(year),
                "month": int(month),
                "title": title,
            })

        timeline.sort(key=lambda x: (x["year"], x["month"]))
        return timeline

    def generate_soul(self):
        config = self.get_config()
        memory_files = config.get("memory_files", [])

        soul_content = "# 灵魂档案\n\n"
        soul_content += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        for mf in memory_files:
            content = self.get_memory_content(mf["id"])
            if content.strip():
                soul_content += f"---\n\n"
                soul_content += content
                soul_content += "\n\n"

        return soul_content

    def get_category_info(self, category_id):
        category_descriptions = {
            "basic": "基本设定，包括姓名、生日、昵称、性格特点、外貌特征、身体数据等",
            "social": "社会关系，包括父母、兄弟姐妹、闺蜜、朋友、同事等人际关系",
            "experience": "特殊经历，人生中的重大事件，塑造她性格和三观的关键经历",
            "daily": "日常琐事，日常作息、工作习惯、重复性的活动",
            "events": "事件记忆，与男友相处交往的重要事件和回忆",
            "preferences": "偏好习惯，喜好、厌恶、口头禅、小动作、小习惯",
            "values": "价值观，人生信念、处世态度、对事物的看法",
            "emotions": "情感模式，什么让她开心、难过、生气、感动等情绪触发点",
        }
        return category_descriptions.get(category_id, "")
