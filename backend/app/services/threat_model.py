"""Threat model generator for engagement targets."""


def generate_threat_model(target: dict) -> dict:
    target_type = target.get("target_type", "web")
    tech_stack = target.get("tech_stack") or []
    open_ports = target.get("open_ports") or []
    url = target.get("url")
    code_path = target.get("code_path")

    attack_surface = []
    risk_score = 0.0

    if url:
        attack_surface.append({"vector": "web_application", "detail": url, "risk": "high"})
        risk_score += 3.0
    if code_path:
        attack_surface.append({"vector": "source_code", "detail": code_path, "risk": "high"})
        risk_score += 2.5
    if open_ports:
        attack_surface.append(
            {"vector": "network_services", "detail": str(open_ports), "risk": "medium"}
        )
        risk_score += min(len(open_ports) * 0.5, 3.0)
    if target.get("ip_address"):
        attack_surface.append(
            {"vector": "host", "detail": target["ip_address"], "risk": "medium"}
        )
        risk_score += 1.5

    for tech in tech_stack:
        t = tech.lower()
        if t in ("php", "wordpress", "django", "flask", "node", "react"):
            attack_surface.append({"vector": "framework", "detail": tech, "risk": "medium"})
            risk_score += 0.5

    recommended_agents = ["ReconAgent"]
    if target_type in ("web", "network") or url:
        recommended_agents.append("ExploitAgent")
    if code_path or target_type == "code":
        recommended_agents.append("SASTAgent")
    if risk_score >= 5:
        recommended_agents.append("PostExploitAgent")

    recommended_agents = list(dict.fromkeys(recommended_agents))
    risk_score = min(risk_score / 10.0, 1.0)

    return {
        "attack_surface": attack_surface,
        "risk_score": round(risk_score, 3),
        "recommended_agents": recommended_agents,
    }
