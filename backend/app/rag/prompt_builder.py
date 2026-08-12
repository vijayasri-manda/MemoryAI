"""
Prompt builder: assembles the final LLM prompt from memories + conversation.
Produces a system prompt that injects retrieved memories before the user query.
"""

from __future__ import annotations

from app.core.config import settings
from app.services.llm_service import ChatMessage


SYSTEM_TEMPLATE = """\
You are a helpful, intelligent AI assistant with persistent long-term memory.
You remember important information about the user from previous conversations.

{memory_section}

Current date/time: {current_datetime}

Instructions:
- Use your retrieved memories to provide personalized, context-aware responses.
- If memories are relevant to the user's question, refer to them naturally.
- If no memories are relevant, respond normally without mentioning memory.
- Be concise, accurate, and helpful.
- Format code with proper syntax highlighting when applicable.
"""

SUMMARY_SECTION_TEMPLATE = """\
━━━ CONVERSATION SUMMARIES ━━━
{summaries}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

MEMORY_SECTION_TEMPLATE = """\
━━━ RELEVANT MEMORIES FROM PREVIOUS CONVERSATIONS ━━━
{memories}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

NO_MEMORY_SECTION = "(No relevant memories retrieved for this query.)"


class PromptBuilder:
    """
    Assembles the final list of ChatMessages for the LLM.
    Injects retrieved summaries and memories into the system prompt.
    """

    def build(
        self,
        user_query: str,
        conversation_history: list[dict],   # list of {role, content}
        retrieved_memories: list[str],
        current_datetime: str,
        summaries: list[str] | None = None,
    ) -> list[ChatMessage]:
        """
        Build the complete message list for the LLM.
        """
        sections = []

        if summaries:
            summary_text = "\n".join(f"• {s}" for s in summaries)
            sections.append(SUMMARY_SECTION_TEMPLATE.format(summaries=summary_text))

        if retrieved_memories:
            numbered = "\n".join(
                f"[{i + 1}] {mem}" for i, mem in enumerate(retrieved_memories)
            )
            sections.append(MEMORY_SECTION_TEMPLATE.format(memories=numbered))

        if not sections:
            memory_section = NO_MEMORY_SECTION
        else:
            memory_section = "\n\n".join(sections)

        # Build system prompt
        system_content = SYSTEM_TEMPLATE.format(
            memory_section=memory_section,
            current_datetime=current_datetime,
        )

        messages: list[ChatMessage] = [ChatMessage(role="system", content=system_content)]

        # Inject recent conversation history
        max_history = 20
        for msg in conversation_history[-max_history:]:
            if msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append(ChatMessage(role=msg["role"], content=msg["content"]))

        # Ensure current user query is at the end
        if not messages or messages[-1].content != user_query or messages[-1].role != "user":
            messages.append(ChatMessage(role="user", content=user_query))

        return messages

    def build_summary_prompt(self, conversation_text: str) -> list[ChatMessage]:
        """Build a prompt to summarize a conversation."""
        return [
            ChatMessage(
                role="system",
                content=(
                    "You are an expert at summarizing conversations. "
                    "Create a concise, factual summary that captures: "
                    "key topics discussed, decisions made, user preferences revealed, "
                    "projects mentioned, and any action items. "
                    "Be specific and preserve important technical details."
                ),
            ),
            ChatMessage(
                role="user",
                content=(
                    f"Please summarize this conversation:\n\n{conversation_text}\n\n"
                    "Provide a structured summary with sections for: "
                    "Main Topics, Key Decisions, User Preferences, Projects/Goals, Action Items."
                ),
            ),
        ]
