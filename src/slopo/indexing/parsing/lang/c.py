import tree_sitter_c
from tree_sitter import Language, Node, Parser

from slopo.indexing.parsing.base import CodeUnit
from slopo.indexing.parsing.tree_sitter_support import code_unit, node_text

_PARSER = Parser(Language(tree_sitter_c.language()))
_COMMENT_TYPES = {"comment"}


def parse(source: bytes) -> list[CodeUnit]:
    tree = _PARSER.parse(source)
    units: list[CodeUnit] = []
    _collect_units(tree.root_node, source, units)
    return units


def _collect_units(node: Node, source: bytes, units: list[CodeUnit]) -> None:
    if node.type == "function_definition":
        body = node.child_by_field_name("body")
        if body is not None:
            units.append(
                code_unit(
                    name=node_text(_declarator_name(node)) or "<unknown>",
                    start=node,
                    end=node,
                    body=body,
                    source=source,
                    comment_types=_COMMENT_TYPES,
                )
            )
    for child in node.children:
        _collect_units(child, source, units)


def _declarator_name(node: Node) -> Node | None:
    declarator = node.child_by_field_name("declarator")
    while declarator is not None:
        if declarator.type in {"identifier", "field_identifier"}:
            return declarator
        nested = declarator.child_by_field_name("declarator")
        if nested is None:
            return next(
                (
                    child
                    for child in declarator.named_children
                    if child.type in {"identifier", "field_identifier"}
                ),
                None,
            )
        declarator = nested
    return None
