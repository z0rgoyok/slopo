import tree_sitter_swift
from tree_sitter import Language, Node, Parser

from slopo.indexing.parsing.base import CodeUnit
from slopo.indexing.parsing.tree_sitter_support import code_unit, node_text

_PARSER = Parser(Language(tree_sitter_swift.language()))
_COMMENT_TYPES = {"comment"}
_DECLARATION_TYPES = {
    "function_declaration",
    "init_declaration",
    "deinit_declaration",
    "subscript_declaration",
}


def parse(source: bytes) -> list[CodeUnit]:
    tree = _PARSER.parse(source)
    units: list[CodeUnit] = []
    _collect_units(tree.root_node, source, units)
    return units


def _collect_units(node: Node, source: bytes, units: list[CodeUnit]) -> None:
    if node.type in _DECLARATION_TYPES:
        body = node.child_by_field_name("body")
        if body is not None:
            units.append(
                code_unit(
                    name=node_text(node.child_by_field_name("name"))
                    or node.type.removesuffix("_declaration"),
                    start=node,
                    end=node,
                    body=body,
                    source=source,
                    comment_types=_COMMENT_TYPES,
                )
            )
    elif node.type == "lambda_literal":
        body = next(
            (child for child in node.named_children if child.type == "statements"),
            None,
        )
        if body is not None:
            units.append(
                code_unit(
                    name=_lambda_name(node),
                    start=node,
                    end=node,
                    body=body,
                    source=source,
                    comment_types=_COMMENT_TYPES,
                )
            )
    for child in node.children:
        _collect_units(child, source, units)


def _lambda_name(node: Node) -> str:
    parent = node.parent
    while parent is not None and parent.type not in {"source_file", "function_body"}:
        name = parent.child_by_field_name("name")
        if name is not None:
            return node_text(name) or "<unknown>"
        parent = parent.parent
    return "<unknown>"
