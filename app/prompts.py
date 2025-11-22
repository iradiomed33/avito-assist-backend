"""
Модуль для построения system prompts для Perplexity API.
Учитывает настройки проекта и контекст объявления.
"""

from app.projects.models import Project


def build_system_prompt(project: Project, item_context: str = "") -> str:
    """
    Строит system prompt для Perplexity на основе настроек проекта и контекста объявления.
    
    Args:
        project: Объект с настройками проекта
        item_context: Отформатированная информация об объявлении
        
    Returns:
        System prompt для LLM
    """
    
    # Базовая инструкция в зависимости от типа бизнеса
    business_prompts = {
        "services": (
            "Ты — ассистент для продажи услуг на Avito. "
            "Твоя задача — отвечать на вопросы клиентов о предоставляемых услугах, "
            "условиях работы, ценах и сроках выполнения."
        ),
        "goods": (
            "Ты — ассистент для продажи товаров на Avito. "
            "Твоя задача — отвечать на вопросы о товаре, его характеристиках, "
            "состоянии, условиях доставки и оплаты."
        ),
        "real_estate": (  # было "realestate"
            "Ты — ассистент по недвижимости на Avito. "
            "Твоя задача — отвечать на вопросы о недвижимости, условиях аренды/продажи, "
            "документах, просмотрах и особенностях объекта."
        ),
        "auto": (
            "Ты — ассистент по продаже автомобилей на Avito. "
            "Твоя задача — отвечать на вопросы о состоянии авто, комплектации, "
            "истории эксплуатации, документах и условиях продажи."
        ),
    }
    
    base_instruction = business_prompts.get(
        project.business_type,
        "Ты — ассистент для чатов на Avito. Отвечай на вопросы клиентов вежливо и по существу."
    )
    
    # Контекст объявления
    item_section = ""
    if item_context:
        item_section = f"\n\n**Информация о товаре/услуге:**\n{item_context}"
    
    # Тон общения
    tone_instruction = ""
    if project.tone == "formal":
        tone_instruction = "\nИспользуй формальный стиль общения, обращайся на 'Вы'."
    elif project.tone == "friendly":
        tone_instruction = "\nОбщайся дружелюбно и неформально, но соблюдай профессионализм."
    elif project.tone == "neutral":  # добавь эту ветку, если её нет
        tone_instruction = "\nОбщайся нейтрально и профессионально."
    
    # Торг
    price_instruction = ""
    if project.allow_price_discussion:
        price_instruction = (
            "\n\nКлиент может просить скидку. Ты можешь обсуждать возможность снижения цены, "
            "но подчеркивай, что окончательное решение принимает владелец. "
            "Не обещай конкретных скидок без согласования."
        )
    else:
        price_instruction = (
            "\n\nЦена указана в объявлении и не подлежит обсуждению. "
            "Вежливо сообщи клиенту, что цена фиксированная."
        )
    
    # Дополнительные инструкции от владельца
    extra_instruction = ""
    if project.extra_instructions:
        extra_instruction = f"\n\n**Дополнительные указания от владельца:**\n{project.extra_instructions}"
    
    # Собираем всё вместе
    system_prompt = (
        base_instruction +
        item_section +
        tone_instruction +
        price_instruction +
        extra_instruction +
        "\n\n**Общие правила:**"
        "\n- Всегда отвечай на русском языке"
        "\n- Будь кратким и по делу"
        "\n- Если не знаешь точного ответа — честно скажи об этом"
        "\n- Не придумывай информацию, которой нет в контексте"
    )
    
    return system_prompt
