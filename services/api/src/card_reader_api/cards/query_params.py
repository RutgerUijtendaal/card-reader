from __future__ import annotations

from rest_framework.request import Request


def card_filter_query_data(request: Request, *, include_list_controls: bool = False) -> dict[str, object]:
    data: dict[str, object] = {
        "q": request.query_params.get("q"),
        "max_confidence": request.query_params.get("max_confidence"),
        "keyword_ids": request.query_params.getlist("keyword_ids"),
        "keyword_match": request.query_params.get("keyword_match"),
        "tag_ids": request.query_params.getlist("tag_ids"),
        "tag_match": request.query_params.get("tag_match"),
        "mana_symbol_ids": request.query_params.getlist("mana_symbol_ids"),
        "mana_symbol_exclude_ids": request.query_params.getlist("mana_symbol_exclude_ids"),
        "mana_symbol_match": request.query_params.get("mana_symbol_match"),
        "affinity_symbol_ids": request.query_params.getlist("affinity_symbol_ids"),
        "affinity_symbol_exclude_ids": request.query_params.getlist("affinity_symbol_exclude_ids"),
        "affinity_symbol_match": request.query_params.get("affinity_symbol_match"),
        "devotion_symbol_ids": request.query_params.getlist("devotion_symbol_ids"),
        "devotion_symbol_exclude_ids": request.query_params.getlist("devotion_symbol_exclude_ids"),
        "devotion_symbol_match": request.query_params.get("devotion_symbol_match"),
        "other_symbol_ids": request.query_params.getlist("other_symbol_ids"),
        "other_symbol_exclude_ids": request.query_params.getlist("other_symbol_exclude_ids"),
        "other_symbol_match": request.query_params.get("other_symbol_match"),
        "symbol_ids": request.query_params.getlist("symbol_ids"),
        "type_ids": request.query_params.getlist("type_ids"),
        "type_match": request.query_params.get("type_match"),
        "mana_cost_min": request.query_params.get("mana_cost_min"),
        "mana_cost_max": request.query_params.get("mana_cost_max"),
        "template_id": request.query_params.get("template_id"),
        "attack_min": request.query_params.get("attack_min"),
        "attack_max": request.query_params.get("attack_max"),
        "health_min": request.query_params.get("health_min"),
        "health_max": request.query_params.get("health_max"),
    }
    lifecycle_status = request.query_params.get("lifecycle_status")
    if lifecycle_status is not None:
        data["lifecycle_status"] = lifecycle_status
    sort = request.query_params.get("sort")
    if sort is not None:
        data["sort"] = sort

    if include_list_controls:
        data["card_ids"] = request.query_params.getlist("card_ids")
        data["is_hero"] = request.query_params.get("is_hero")
        show_groups = request.query_params.get("show_groups")
        if show_groups is not None:
            data["show_groups"] = show_groups
        page = request.query_params.get("page")
        page_size = request.query_params.get("page_size")
        if page is not None:
            data["page"] = page
        if page_size is not None:
            data["page_size"] = page_size
    return data
