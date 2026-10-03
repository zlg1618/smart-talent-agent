"""Agent 流程测试（覆盖核心双域 11 个场景）。

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
        ("组织架构与编制", ["看一下公司组织架构和编制达成情况"]),
        (
            "多轮记忆 + 改条件",
            ["看一下组织架构", "部门改成销售部", "重新看一下组织架构"],
        ),
        ("组织效能", ["分析一下各部门人效"]),
        ("岗位职级体系", ["技术中心的职级体系健康吗"]),
        ("组织变革", ["模拟一下组织变革方案的影响"]),
        ("能力差距", ["技术中心的能力差距在哪"]),
        ("任职资格匹配", [f"{sample_name} 能晋升到下一职级吗"]),
        ("人才池", ["看一下人才池的运行情况"]),
        ("发展项目", ["发展项目完成得怎么样"]),
        ("导师制", ["导师带教进展如何"]),
        ("无关对话", ["今天天气怎么样"]),
    ]

    for title, messages in cases:
        run_case(service, title, messages)

    print("Agent 流程测试执行完毕。")


if __name__ == "__main__":
    main()
