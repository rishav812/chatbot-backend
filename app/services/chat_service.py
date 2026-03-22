import os
from openai import AsyncOpenAI
from langchain_openai import OpenAIEmbeddings
from app.services.embedding_service import similarity_search
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

# Initialize models
embedding_model = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# AsyncOpenAI client for chat completions
openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

async def generate_chat_response(db, query: str, chat_history: list = None) -> str:
    """
    RAG Logic:
    1. Embed user query
    2. Search DB for nearest chunks
    3. Feed context + query to LLM
    4. Return conversational response
    """
    if chat_history is None:
        chat_history = []

    # 1. Embed the query
    try:
         query_vector = await embedding_model.aembed_query(query)
    except Exception as e:
         print(f"Error embedding query: {e}")
         return "I'm currently unable to process your request."

    # 2. Similarity Search (Fetch top 5 chunks)
    # Lower distance = higher score
    results = await similarity_search(db, query_embedding=query_vector, top_k=5)
    
    context_text = ""
    if results:
        # Join chunks together
        context_text = "\n\n".join([r["content"] for r in results])
    else:
        context_text = "No prior documents or context found in the database."

    prompt = PromptTemplate(
        template="""You are Rishav's AI assistant. You act as a representative for Rishav based on the documents uploaded to your knowledge base.
            Use the following pieces of retrieved context about Rishav to answer the user's question. 
            If the answer is not in the context, politely state that you don't have that information.
            Keep the answer natural, friendly, and professional. Do not invent information about Rishav.

            Context: {context}

            Question: {question}

            Answer:""",
        input_variables=['context', 'question']
    )


    model = ChatOpenAI(
        model="gpt-4", 
        temperature=0
    )

    rag_chain = (
        {"context": lambda _: context_text, "question": RunnablePassthrough()}
        | prompt 
        | model 
        | StrOutputParser()
    )

    # invoke takes the raw query string because RunnablePassthrough routes it to 'question'
    response = rag_chain.invoke(query)
    return response
