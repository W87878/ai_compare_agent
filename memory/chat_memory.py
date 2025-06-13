from langchain.memory import ConversationBufferMemory

def get_memory():
    return ConversationBufferMemory(
        return_messages=False,
        memory_key="history"
    )