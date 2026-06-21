"""Cross-session memory block: compresses prior researched companies into a system-prompt suffix."""

from app.db import row_to_dict


def build_company_memory_block(profiles: list) -> str:
    if not profiles:
        return ""
    lines = [
        "\n\n---\n## 🧠 Companies You Have Already Researched\n",
        "Use this knowledge to avoid repetition and draw comparisons:\n",
    ]
    for row in profiles:
        p = row_to_dict(row)
        pain_summary = "; ".join(p["pain_points"][:2])
        lines.append(
            f"- **{p['company_name']}** ({p['created_at']}): "
            f"{p['core_product']}. Key pains: {pain_summary}."
        )
    return "\n".join(lines)
