import tree_sitter_dart_fluid
from tree_sitter import Language, Node, Parser

from slopo.indexing.parsing.base import CodeUnit
from slopo.indexing.parsing.tree_sitter_support import (
    code_unit,
    first_descendant_by_field,
    next_named_sibling,
    node_text,
)

_PARSER = Parser(Language(tree_sitter_dart_fluid.language()))
_COMMENT_TYPES = {"comment", "documentation_comment"}


def parse(source: bytes) -> list[CodeUnit]:
    tree = _PARSER.parse(source)
    units: list[CodeUnit] = []
    _collect_units(tree.root_node, source, units)
    return units


def _collect_units(node: Node, source: bytes, units: list[CodeUnit]) -> None:
    unit = _unit(node, source)
    if unit is not None:
        units.append(unit)

    if node.type not in {"method_signature", "lambda_expression"}:
        for child in node.children:
            _collect_units(child, source, units)


def _unit(node: Node, source: bytes) -> CodeUnit | None:
    if node.type in {"method_signature", "function_signature"}:
        body = next_named_sibling(node, "function_body")
        if body is None:
            return None
        return code_unit(
            name=node_text(first_descendant_by_field(node, "name")) or "<unknown>",
            start=node,
            end=body,
            body=body,
            source=source,
            comment_types=_COMMENT_TYPES,
        )

    if node.type in {"lambda_expression", "function_expression"}:
        body = node.child_by_field_name("body")
        if body is None:
            return None
        return code_unit(
            name=_expression_name(node),
            start=node,
            end=node,
            body=body,
            source=source,
            comment_types=_COMMENT_TYPES,
        )
    return None


def _expression_name(node: Node) -> str:
    declared = first_descendant_by_field(node, "name")
    if declared is not None and node.type == "lambda_expression":
        return node_text(declared) or "<unknown>"

    parent = node.parent
    while parent is not None and parent.type not in {
        "program",
        "class_body",
        "function_body",
    }:
        name = parent.child_by_field_name("name")
        if name is not None and not _contains(name, node):
            return node_text(name) or "<unknown>"
        if parent.type == "static_final_declaration":
            identifier = next(
                (child for child in parent.named_children if child.type == "identifier"),
                None,
            )
            return node_text(identifier) or "<unknown>"
        parent = parent.parent
    return "<unknown>"


def _contains(candidate: Node, node: Node) -> bool:
    return candidate.start_byte <= node.start_byte and candidate.end_byte >= node.end_byte
