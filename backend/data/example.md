# Example knowledge base entry

This is a placeholder file so the RAG pipeline in Template 1 has something to
index out of the box. Delete this and add your own `.txt` or `.md` files —
class notes, a sponsor's API docs, research paper text, FAQ content, etc.

## How retrieval works here

When a user sends a message, the backend embeds the message and compares it
against embedded chunks of every file in this `data/` folder, then injects
the most relevant chunks into the LLM's context before generating a reply.

Try asking the chat: "What is this example file for?" — it should reference
this text in its answer, which confirms RAG is working end-to-end.
