import pytest
from app.prompts import build_system_prompt
from app.projects.models import Project


def test_build_system_prompt_services():
    """Тест промпта для бизнес-типа services"""
    project = Project(
        id="test",
        name="Test",
        business_type="services",
        tone="formal",  # было "professional"
        allow_price_discussion=False,
    )
    
    prompt = build_system_prompt(project)
    
    assert "продажи услуг" in prompt or "услуг" in prompt
    assert "формальный" in prompt or "Вы" in prompt
    assert "не подлежит обсуждению" in prompt


def test_build_system_prompt_with_item_context():
    """Тест промпта с контекстом объявления"""
    project = Project(
        id="test",
        name="Test",
        business_type="goods",
    )
    
    item_context = "Название: iPhone 13\nЦена: 50000 ₽"
    prompt = build_system_prompt(project, item_context=item_context)
    
    assert "iPhone 13" in prompt
    assert "50000 ₽" in prompt


def test_build_system_prompt_friendly_tone():
    """Тест дружелюбного тона"""
    project = Project(
        id="test",
        name="Test",
        business_type="goods",
        tone="friendly",
    )
    
    prompt = build_system_prompt(project)
    
    assert "дружелюбно" in prompt


def test_build_system_prompt_allow_price_discussion():
    """Тест разрешения торга"""
    project = Project(
        id="test",
        name="Test",
        business_type="auto",
        allow_price_discussion=True,
    )
    
    prompt = build_system_prompt(project)
    
    assert "может просить скидку" in prompt
    assert "окончательное решение" in prompt


def test_build_system_prompt_extra_instructions():
    """Тест дополнительных инструкций"""
    project = Project(
        id="test",
        name="Test",
        business_type="services",
        extra_instructions="Всегда предлагай записаться на консультацию",
    )
    
    prompt = build_system_prompt(project)
    
    assert "консультацию" in prompt
    assert "Дополнительные указания" in prompt


def test_build_system_prompt_realestate():
    """Тест промпта для недвижимости"""
    project = Project(
        id="test",
        name="Test",
        business_type="real_estate",  # было "realestate"
    )
    
    prompt = build_system_prompt(project)
    
    assert "недвижимости" in prompt


def test_build_system_prompt_unknown_business_type():
    """Тест дефолтного промпта для неизвестного типа бизнеса"""
    project = Project(
        id="test",
        name="Test",
        business_type="other",  # было "unknown_type"
    )
    
    prompt = build_system_prompt(project)
    
    assert "Avito" in prompt
    assert "вежливо" in prompt or "клиентов" in prompt
