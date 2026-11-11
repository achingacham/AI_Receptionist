from backend.app.knowledge import YAMLKnowledgeProvider


def test_yaml_knowledge_provider_loads_entries(tmp_path):
    yaml_content = """
clinic:
  name: "Test Clinic"
entries:
  - id: "test-1"
    category: "services"
    keywords: ["hearing", "test"]
    question: "Do you test hearing?"
    answer: "Yes, we do comprehensive hearing assessments."
"""
    file_path = tmp_path / "test_kb.yaml"
    file_path.write_text(yaml_content)

    provider = YAMLKnowledgeProvider(file_path)
    assert len(provider.entries) == 1
    assert provider.entries[0]["id"] == "test-1"

    context = provider.get_grounding_context()
    assert "CLINIC KNOWLEDGE BASE (GROUNDING SOURCE OF TRUTH):" in context
    assert "GROUNDING GUARDRAIL DIRECTIVES:" in context
    assert "Do you test hearing?" in context
    assert "Yes, we do comprehensive hearing assessments." in context


def test_yaml_knowledge_provider_production_file():
    provider = YAMLKnowledgeProvider("data/clinic_knowledge.yaml")
    assert len(provider.entries) >= 5

    # Assert every entry has required fields for FTS5 forward compatibility
    for e in provider.entries:
        assert "id" in e
        assert "category" in e
        assert "keywords" in e and isinstance(e["keywords"], list) and len(e["keywords"]) > 0
        assert "question" in e
        assert "answer" in e

    context = provider.get_grounding_context()
    assert "Magnus Hearing and Speech Clinic" in context
    assert "STRICT FACTUAL BOUNDARY" in context
