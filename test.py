from pageindex import PageIndexClient

from src.config import settings


search_prompt = f"""
You are given a question and have a tree structure of a document.
Each node contains a node id, node title, and a corresponding summary.
Your task is to find all nodes that are likely to contain the answer to the question.

Question: {"Compare the concentration of 'Pure-Play' cybersecurity firms in the South-West against the National Average"}

Please reply in the following JSON format:
{{
    "node_list": ["node_id_1", "node_id_2", ..., "node_id_n"]
}}
Only return node_id values that appear in the tree. Do not invent node_ids.
Directly return the final JSON structure. Do not output anything else.
"""


client = PageIndexClient(api_key=settings.pageindex_api_key)
for chunk in client.chat_completions(
        messages=[{"role": "user", "content": search_prompt}],
        doc_id="pi-cmmd2tt3k00990hobdgfx363t",
        enable_citations=True,
        stream=True,
    ):
    print(chunk, end='', flush=True)