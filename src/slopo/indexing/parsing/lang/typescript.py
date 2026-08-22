import tree_sitter_typescript
from tree_sitter import Language, Node, Parser

from slopo.indexing.parsing.base import CodeUnit
from slopo.indexing.parsing.tree_sitter_support import code_unit

_LANGUAGE = Language(tree_sitter_typescript.language_typescript())
_PARSER = Parser(_LANGUAGE)
_TSX_LANGUAGE = Language(tree_sitter_typescript.language_tsx())
_TSX_PARSER = Parser(_TSX_LANGUAGE)

_COMMENT_TYPES = {"comment"}

_UNIT_TYPES = {
    "function_declaration",
    "generator_function_declaration",
    "method_definition",
    "arrow_function",
    "function_expression",
}


def parse(source: bytes) -> list[CodeUnit]:
    return _parse(_PARSER, source)


def parse_tsx(source: bytes) -> list[CodeUnit]:
    return _parse(_TSX_PARSER, source)


def _parse(parser: Parser, source: bytes) -> list[CodeUnit]:
    tree = parser.parse(source)
    units: list[CodeUnit] = []
    _collect_units(tree.root_node, source, units)
    return units


def _collect_units(node: Node, source: bytes, units: list[CodeUnit]) -> None:
    if node.type in _UNIT_TYPES:
        units.append(
            code_unit(
                name=_unit_name(node),
                start=node,
                end=node,
                body=node.child_by_field_name("body"),
                source=source,
                comment_types=_COMMENT_TYPES,
            )
        )
    for child in node.children:
        _collect_units(child, source, units)


def _unit_name(node: Node) -> str:
    # Declarations and methods carry their own name. Arrow and function
    # expressions are anonymous, so the name comes from what they are bound to.
    name_node = node.child_by_field_name("name")
    if name_node is None and node.type in {"arrow_function", "function_expression"}:
        name_node = _binding_name_node(node)
    return name_node.text.decode() if (name_node and name_node.text) else "<unknown>"


def _binding_name_node(node: Node) -> Node | None:
    parent = node.parent
    if parent is None:
        return None
    if parent.type == "variable_declarator":  # const f = () => ...
        return parent.child_by_field_name("name")
    if parent.type == "pair":  # { f: () => ... }
        return parent.child_by_field_name("key")
    if parent.type == "assignment_expression":  # x.f = () => ...
        left = parent.child_by_field_name("left")
        if left is not None and left.type == "member_expression":
            return left.child_by_field_name("property")
        return left
    return None

