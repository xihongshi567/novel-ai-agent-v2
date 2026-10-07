"""M7 评测用 MockBackend：按调用类型返回预设结果，零网络零真实 LLM。

分支判定依据 prompts/ 里的提示词特征词，与 tests/test_offline.py 的 MockBackend
同模式，但增加 summarize/审校/追踪 的可失败开关，供缺口评测注入故障。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel_agent.llm import LLMBackend, Message


class MockBackend(LLMBackend):
    name = "mock"
    writer_model = "mock-writer"

    def __init__(self) -> None:
        self.call_log: list[str] = []
        # 故障注入开关
        self.fail_summarize = False  # summarize 返回不可解析文本
        self.invalid_review = False  # 审校返回非 JSON
        self.novel_text: str | None = None  # 自定义正文（确定性）

    def chat(
        self, messages, *, model=None, temperature=0.85, max_tokens=None, stop=None, **_
    ):
        text = messages[-1].content if messages else ""
        self.call_log.append(text[:60])

        if "「状态变化」与「连续性条目」" in text:
            return json.dumps({
                "character_status": [{"name": "林尘", "status": "坠崖后获得传承"}],
                "timeline": [{"event": "林尘坠崖获得传承"}],
                "foreshadows": [{"description": "林霸仍在青云村"}],
                "foreshadows_resolved": [],
                "possessions": [{"owner": "林尘", "item": "传承之力", "acquired": True}],
                "promises": [{"maker": "林尘", "receiver": "妹妹", "content": "买桃花簪", "made": True}],
                "facts": [],
            }, ensure_ascii=False)
        if "压缩成一份【前情提要摘要】" in text or "前情提要" in text:
            if self.fail_summarize:
                return "这一段讲的是主角成长的故事，语言风格朴实。"
            return "林尘被林霸欺辱坠崖，在崖底古洞获得上古传承，实力初现。"
        if "审校" in text and "score" in text:
            if self.invalid_review:
                return "今天的文笔不错，节奏也合适。"
            return json.dumps({
                "score": 8,
                "issues": [{"severity": "low", "type": "pacing", "location": "中段",
                            "description": "节奏稍快", "suggestion": "增加细节"}],
                "overall": "整体合格，人物动机清晰。",
                "deviation": {"deviated": False, "degree": "", "description": ""},
                "continuity_violations": [],
            }, ensure_ascii=False)
        if "故事前提/主线" in text or "premise" in text:
            return json.dumps({
                "premise": "孤儿少年偶得上古传承，在乱世中崛起复仇并守护所爱。",
                "themes": ["成长", "复仇", "守护"],
                "volumes": [{
                    "title": "觉醒之卷",
                    "summary": "主角觉醒传承，踏入修炼界。",
                    "chapters": [
                        {"title": "废柴少年", "beat": "林尘被族人欺辱，意外坠崖获得传承"},
                        {"title": "初试身手", "beat": "林尘回村击退来犯之敌"},
                    ],
                }],
            }, ensure_ascii=False)
        if "characters" in text and "设定集" in text:
            return json.dumps({
                "characters": [{
                    "id": "char_linchen", "name": "林尘", "role": "主角",
                    "summary": "废柴少年，实为上古血脉", "personality": "坚韧隐忍",
                    "motivation": "为父母复仇、守护妹妹", "abilities": "上古传承之力",
                }],
                "locations": [{"id": "loc_qingyun", "name": "青云村", "summary": "主角故乡"}],
                "factions": [],
                "lore": [{"id": "lore_xiulian", "name": "修炼体系", "summary": "炼气→筑基→金丹"}],
            }, ensure_ascii=False)
        if "单章写作计划" in text:
            return json.dumps({
                "title": "废柴少年", "pov": "林尘", "setting": "青云村",
                "characters": ["林尘", "林霸"],
                "beat": "林尘被堂兄林霸当众羞辱并夺走灵石，绝望中跌落悬崖，获得上古传承。",
                "goal": "建立主角困境与转折", "conflict": "弱小 vs 欺压",
                "ending": "传承入体，林尘睁开双眼",
            }, ensure_ascii=False)
        if "本章正文" in text or "字数要求" in text or "字（中文字符）" in text:
            if self.novel_text is not None:
                return self.novel_text
            return _default_novel_text()
        return "好的，这是模拟回复。"


def _default_novel_text() -> str:
    return (
        "夕阳斜挂在青云山的山脊上，把整座小村染成一片昏黄。林尘蹲在村口的石磨旁，"
        "手里紧紧攥着一块指甲大小的下品灵石。这是他三个月来进山采药换来的全部收获，"
        "明日便是妹妹小溪的生辰，他答应了要给她买一支桃花簪。「哟，废物尘儿，还藏着宝贝呢？」"
        "林霸带着两个狗腿子逼近，一掌拍在林尘肩头，夺走灵石，一脚把他踹翻在地。"
        "围观的人不少，却没有一个上前。林尘咬着牙站起来，转身朝后山跑去。"
        "他来到一处熟悉的断崖，脚下云雾翻涌，深不见底。「凭什么……就因为我是庶出？」"
        "身后叫骂声越来越近，林霸狞笑着又是一掌，林尘脚下一滑，仰面跌落悬崖。\n\n"
        "不知过了多久，他缓缓睁开眼，面前是一扇布满符文的石门。"
    )


if __name__ == "__main__":
    b = MockBackend()
    print("mock backend ok")
