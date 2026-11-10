"""通用同级重排：父字段授权、保护边界、履约及实际服务交付。"""

import json

import pytest

from core.errors import GenerationStatus
from services.single_step_edit import source_digest
from services.widget_edit_contract import (
    ChildrenOrder,
    apply_children_orders,
    apply_edit_output,
    dump_rows,
    validate_edit_diff,
    validate_intent,
)
from services.widget_generation_service import WidgetGenerationService
from test_semantic_widget_edit import _intent, _nodes, _request, _rows
from test_semantic_widget_edit import edit_run as edit_run
from test_semantic_widget_edit import source as source


def _order_intent(**changes):
    values = {
        "mode": "reorder", "dimensions": ["layout"], "targets": ["title", "value"],
        "childrenOrders": [{"parentId": "root", "children": ["value", "title"]}],
    }
    values.update(changes)
    return _intent(**values)


@pytest.mark.parametrize("kind", ["Row", "Column", "Stack"])
def test_order_changes_only_parent_references(source, kind):
    rows = _rows(source)
    _nodes(rows)[0]["component"] = kind
    original = dump_rows(rows)
    intent = _order_intent()
    validate_intent(intent, original, "2x4", None)
    result = _rows(apply_children_orders(original, intent))
    expected = _rows(original)
    _nodes(expected)[0]["children"] = ["value", "title"]
    assert result == expected


@pytest.mark.parametrize("mutation", [
    "missing_parent", "duplicate_parent", "duplicate_child", "new_child", "delete_child",
    "protected_parent", "protected_child", "outside_scope", "patch", "size", "noop",
])
def test_invalid_plan_rejected_before_execution(source, mutation):
    intent = _order_intent()
    order = intent.childrenOrders[0]
    if mutation == "missing_parent":
        order.parentId = "unknown"
    elif mutation == "duplicate_parent":
        intent.childrenOrders.append(order.model_copy(deep=True))
    elif mutation == "duplicate_child":
        order.children = ["value", "value"]
    elif mutation == "new_child":
        order.children = ["value", "unknown"]
    elif mutation == "delete_child":
        order.children = ["value"]
    elif mutation == "protected_parent":
        intent.protectedTargets = ["root"]
    elif mutation == "protected_child":
        intent.protectedTargets = ["title"]
    elif mutation == "outside_scope":
        intent.targets = ["title"]
    elif mutation == "patch":
        intent.mode = "patch"
    elif mutation == "size":
        intent.targetSize = "2x2"
    else:
        order.children = ["title", "value"]
    with pytest.raises(ValueError):
        validate_intent(intent, source, "2x4", None)


def test_protected_descendant_cannot_move_with_branch(source):
    rows = _rows(source)
    nodes = _nodes(rows)
    nodes[0]["children"] = ["group", "value"]
    nodes.append({"id": "group", "component": "Column", "children": ["title"]})
    intent = _order_intent(
        targets=["group", "value"], protectedTargets=["title"],
        childrenOrders=[{"parentId": "root", "children": ["value", "group"]}],
    )
    with pytest.raises(ValueError, match="保护"):
        validate_intent(intent, dump_rows(rows), "2x4", None)


def test_dynamic_template_is_not_a_static_order(source):
    rows = _rows(source)
    _nodes(rows)[0]["children"] = {"componentId": "title", "dataBinding": "/items"}
    with pytest.raises(ValueError, match="动态列表"):
        validate_intent(_order_intent(), dump_rows(rows), "2x4", None)


@pytest.mark.parametrize("mode", ["layout", "reorder"])
def test_parent_order_permission_does_not_authorize_styles(source, mode):
    intent = _order_intent(mode=mode)
    result = _rows(apply_children_orders(source, intent))
    _nodes(result)[0]["styles"]["height"] = 100
    with pytest.raises(ValueError):
        validate_edit_diff(source, dump_rows(result), intent)


def test_layout_order_is_hard_goal_even_when_partial_allowed(source):
    intent = _order_intent(mode="layout", allowPartial=True)
    rows = _rows(source)
    _nodes(rows)[1]["styles"]["height"] = 50
    payload = {"sourceDigest": source_digest(source), "genui": rows}
    with pytest.raises(ValueError, match="EDIT_ORDER_UNMET"):
        apply_edit_output(source, json.dumps(payload), intent, recover=True)


def test_unchanged_must_already_satisfy_order(source):
    intent = _order_intent(outcome="unchanged")
    with pytest.raises(ValueError, match="unchanged"):
        validate_intent(intent, source, "2x4", None)
    intent.childrenOrders = [ChildrenOrder(parentId="root", children=["title", "value"])]
    validate_intent(intent, source, "2x4", None)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["reorder", "layout"])
async def test_order_service_saves_with_full_validation(edit_run, source, mode):
    edit_run.intent = _order_intent(mode=mode)
    expected = apply_children_orders(source, edit_run.intent)
    payload = {"sourceDigest": source_digest(source), "genui": _rows(expected)}
    edit_run.outputs = [json.dumps(payload)]
    response = await WidgetGenerationService().generate_widget_card_compact_dsl(_request())
    assert response.status == GenerationStatus.SUCCESS
    assert len(edit_run.saved) == 1
    assert _rows(edit_run.saved[0].genui) == _rows(expected)
    phases = [phase for phase, _messages in edit_run.calls]
    expected_phases = ["edit_intent"]
    if mode == "layout":
        expected_phases.append("edit_execute")
    assert phases == expected_phases
    assert edit_run.source.genui == source


@pytest.mark.asyncio
async def test_satisfied_order_keeps_explicit_runtime_update(edit_run, source):
    edit_run.intent = _order_intent(
        outcome="unchanged",
        childrenOrders=[{"parentId": "root", "children": ["title", "value"]}],
    )
    response = await WidgetGenerationService().generate_widget_card_compact_dsl(
        _request(title="新卡片名称"),
    )
    assert response.status == GenerationStatus.SUCCESS
    assert len(edit_run.saved) == 1
    assert edit_run.saved[0].cardSpec.get("title") == "新卡片名称"
    assert edit_run.saved[0].genui == source
    assert len(edit_run.calls) == 1


@pytest.mark.asyncio
async def test_invalid_order_exhausts_intent_only_and_never_saves(edit_run):
    edit_run.intent = _order_intent(protectedTargets=["title"])
    response = await WidgetGenerationService().generate_widget_card_compact_dsl(_request())
    assert response.status == GenerationStatus.FAILED
    assert not edit_run.saved
    assert len(edit_run.calls) == 3
    assert all(phase == "edit_intent" for phase, _messages in edit_run.calls)
