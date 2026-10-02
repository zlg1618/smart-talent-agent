"""Agent 流程测试（覆盖 7 个核心场景）。

用法：python test_agent.py

不依赖大模型：模型不可用时自动回退到规则引擎，
因此该脚本在任何环境下都能验证 Agent 的路由与状态逻辑。
"""

import uuid

from app.config.database import SessionLocal
from app.services import employee_service
from app.services.ai_service import AIService


def run_case(service: AIService, title: str, messages: list[str]):
    thread_id = f"test-{uuid.uuid4().hex[:8]}"
    print("=" * 70)
    print(f"场景：{title}   thread_id={thread_id}")
    print("=" * 70)

    for i, message in enumerate(messages, 1):
        print(f"\n[第 {i} 轮] 用户：{message}")
        resp = service.chat(thread_id, message)
        print(f"  意图：{resp['request_type']}  主题：{resp['active_topic']}  "
              f"LLM：{resp['llm_used']}")
        print(f"  条件：{resp['conditions']}")
        answer = (resp["answer"] or "").strip()
        preview = answer[:600] + ("..." if len(answer) > 600 else "")
        print(f"  回答：\n{preview}")
    print()


def main():
    db = SessionLocal()
    try:
        employees = employee_service.list_employees(db)
        sample_name = employees[0].name if employees else "张伟"
    finally:
        db.close()

    service = AIService()

    cases = [
        ("正常盘点", ["对技术中心做一次人才盘点"]),
        ("多轮记忆 + 偏好筛选", ["做一次人才盘点", "只看明星人才"]),
        (
            "修改条件后重新盘点",
            ["做一次人才盘点", "部门改成销售部", "重新做一次盘点"],
        ),
        ("指定周期与职级", ["看一下 2024H2 的 P6 人才盘点"]),
        ("继任地图", ["看一下关键岗位继任地图"]),
        ("人才梯队", ["分析一下人才梯队有没有断层"]),
        ("个人发展计划", [f"给{sample_name}生成一份个人发展计划"]),
        ("组织诊断", ["做一次组织诊断"]),
        ("无关对话", ["今天天气怎么样"]),
    ]

    for title, messages in cases:
        run_case(service, title, messages)

    print("Agent 流程测试执行完毕。")


if __name__ == "__main__":
    main()
