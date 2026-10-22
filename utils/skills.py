"""
Skill vocabulary used by the offline (demo-mode) engine.

In live mode the LLM understands synonyms on its own; in demo mode we
need a small dictionary so that, e.g., "PostgreSQL" counts as SQL.
"""
import re

KNOWN_SKILLS = {
    "python": ["python"],
    "sql": ["sql", "mysql", "postgresql", "postgres", "sqlite"],
    "git": ["git", "github", "gitlab"],
    "rest": ["rest api", "rest apis", "restful", "rest"],
    "django": ["django"],
    "flask": ["flask"],
    "fastapi": ["fastapi"],
    "docker": ["docker", "container"],
    "aws": ["aws", "ec2", "s3", "lambda", "amazon web services"],
    "pandas": ["pandas"],
    "pytest": ["pytest", "unittest", "unit test", "unit testing"],
    "react": ["react", "react.js", "reactjs"],
    "linux": ["linux", "bash", "shell scripting"],
    "javascript": ["javascript", "js"],
    "java": ["java"],
}


def aliases_for(skill: str) -> list[str]:
    """Turn a JD skill phrase into the list of words that count as a match.

    "Django or Flask"       -> ["django", "flask"]
    "REST API development"  -> ["rest api", "rest apis", "restful", "rest"]
    """
    parts = re.split(r"\s*(?:/|,|\bor\b|\(|\))\s*", skill.lower())
    result: list[str] = []
    for part in filter(None, (p.strip() for p in parts)):
        matched = False
        for key, syns in KNOWN_SKILLS.items():
            if re.search(rf"\b{re.escape(key)}\b", part):
                result.extend(syns)
                matched = True
        if not matched:
            result.append(part)
    return list(dict.fromkeys(result))  # de-duplicate, keep order


def find_evidence(text: str, aliases: list[str]) -> str | None:
    """Return the resume line that best proves a skill, or None if absent.

    Experience bullets ("- Built REST APIs in Flask ...") are preferred over a
    plain skills list, because they show the skill was actually used.
    """
    matches = []
    for line in text.splitlines():
        low = line.lower()
        if any(re.search(rf"(?<![a-z]){re.escape(a)}(?![a-z])", low) for a in aliases):
            matches.append(line)
    if not matches:
        return None
    bullets = [m for m in matches if m.lstrip().startswith(("-", "•", "*"))]
    return (bullets or matches)[0].strip(" -•*\t")[:140]
