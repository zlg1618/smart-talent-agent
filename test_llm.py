"""大模型连通性测试。

用法：python test_llm.py
"""

from app.llm import get_llm_client
from app.services.ai_service import llm_status


def main():
    client = get_llm_client()
    print("大模型状态：", llm_status())

    if not client.available():
        print("\n大模型不可用，Agent 将回退到规则引擎。")
        print("如需启用本地模型：")
        print("  1. 安装并启动 Ollama")
        print("  2. ollama pull deepseek-r1:7b")
        print("  3. 确认服务地址 http://127.0.0.1:11434 可访问")
        return

    answer = client.invoke("你是人才发展助手。", "用一句话说明什么是人才盘点九宫格。")
    print("\n模型返回：")
    print(answer)


if __name__ == "__main__":
    main()
