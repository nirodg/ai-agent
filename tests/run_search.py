import os, sys
sys.path.insert(0, "/home/dorin/work/eorghe.com/ai-agent")
from dotenv import load_dotenv
load_dotenv("/home/dorin/work/eorghe.com/ai-agent/.env")
os.environ.setdefault("LLM_PROVIDER", "openrouter")

from app.llm.factory import build_agent
from app.agents.enrichment_agent import build_enrichment_prompt, _extract_profile
from app.llm.settings import get_current_system_prompt

company, depth = "eorghe srl", "balanced"
print(f"Searching: {company!r}  depth={depth}\n")

full_sys = get_current_system_prompt()
agent, base_model = build_agent(full_sys, temperature=0.0)
result = agent.invoke({"messages": [{"role": "user", "content": build_enrichment_prompt(company, depth)}]})
raw = result["messages"][-1].content
print("=== RAW (first 600) ===\n", raw[:600], "\n\n[parsing...]\n")

fp  = _extract_profile(base_model, raw)
pd_ = fp.model_dump()
print("company_name:", pd_["company_name"])
print("core_product:", pd_["core_product"][:200])
print("pain_points :", pd_["pain_points"])
print("\nSUCCESS")
