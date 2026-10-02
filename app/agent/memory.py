"""多轮对话记忆。

开发阶段使用内存 Checkpointer，生产环境可替换为数据库持久化实现。
"""

from langgraph.checkpoint.memory import InMemorySaver

_checkpointer = InMemorySaver()


def get_checkpointer() -> InMemorySaver:
    return _checkpointer
