import tree_sitter_python
from tree_sitter import Language, Node, Parser

from slopo.indexing.parsing.base import CodeUnit, hash_body

_LANGUAGE = Language(tree_sitter_python.language())
_PARSER = Parser(_LANGUAGE)

_COMMENT_TYPES = {"comment"}


def parse(source: bytes) -> list[CodeUnit]:
    tree = _PARSER.parse(source)
    units: list[CodeUnit] = []
    _collect_units(tree.root_node, source, units)
    return units


def _collect_units(node: Node, source: bytes, units: list[CodeUnit]) -> None:
    definition = _data_only_dataclass_definition(node)
    if node.type == "function_definition" or definition is not None:
        named_definition = definition if definition is not None else node
        name_node = named_definition.child_by_field_name("name")
        name = (
            name_node.text.decode() if (name_node and name_node.text) else "<unknown>"
        )
        body = _body_without_comments(node, source)
        units.append(
            CodeUnit(
                name=name,
                body=body,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                body_node_count=_count_body_nodes(named_definition),
                body_hash=hash_body(body),
            )
        )
    for child in node.children:
        _collect_units(child, source, units)


def _data_only_dataclass_definition(node: Node) -> Node | None:
    if node.type != "decorated_definition":
        return None
    definition = node.child_by_field_name("definition")
    if definition is None or definition.type != "class_definition":
        return None
    decorators = [child for child in node.named_children if child.type == "decorator"]
    if not any(_is_dataclass_decorator(decorator) for decorator in decorators):
        return None
    if not _has_declarative_class_body(definition):
        return None
    return definition


def _is_dataclass_decorator(decorator: Node) -> bool:
    if len(decorator.named_children) != 1:
        return False
    target = decorator.named_children[0]
    if target.type == "call":
        function = target.child_by_field_name("function")
        if function is None:
            return False
        target = function
    if target.type == "identifier":
        return target.text == b"dataclass"
    if target.type != "attribute":
        return False
    owner = target.child_by_field_name("object")
    name = target.child_by_field_name("attribute")
    return (
        owner is not None
        and owner.type == "identifier"
        and owner.text == b"dataclasses"
        and name is not None
        and name.type == "identifier"
        and name.text == b"dataclass"
    )


def _has_declarative_class_body(definition: Node) -> bool:
    body = definition.child_by_field_name("body")
    if body is None:
        return False
    return all(_is_declarative_class_statement(child) for child in body.named_children)


def _is_declarative_class_statement(node: Node) -> bool:
    if node.type in _COMMENT_TYPES or node.type == "pass_statement":
        return True
    if _is_docstring(node):
        return True
    return (
        node.type == "expression_statement"
        and len(node.named_children) == 1
        and node.named_children[0].type == "assignment"
    )


def _body_without_comments(unit: Node, source: bytes) -> str:
    comment_spans: list[tuple[int, int]] = []
    _collect_comment_spans(unit, comment_spans)

    pieces: list[bytes] = []
    cursor = unit.start_byte
    for start, end in sorted(comment_spans):
        pieces.append(source[cursor:start])
        cursor = end
    pieces.append(source[cursor : unit.end_byte])
    return b"".join(pieces).decode()


def _collect_comment_spans(node: Node, spans: list[tuple[int, int]]) -> None:
    if node.type in _COMMENT_TYPES or _is_docstring(node):
        spans.append((node.start_byte, node.end_byte))
        return
    for child in node.children:
        _collect_comment_spans(child, spans)


def _count_body_nodes(definition: Node) -> int:
    body = definition.child_by_field_name("body")
    if body is None:
        return 0
    return _count_named_nodes(body)


def _count_named_nodes(node: Node) -> int:
    if _is_docstring(node):
        return 0
    count = 1 if node.is_named else 0
    for child in node.children:
        count += _count_named_nodes(child)
    return count


def _is_docstring(node: Node) -> bool:
    # A docstring is a bare string as the first statement of a module, class, or
    # function body. It carries no behavior, so it is stripped like a comment.
    if node.type != "expression_statement":
        return False
    if [c.type for c in node.named_children] != ["string"]:
        return False
    parent = node.parent
    return (
        parent is not None
        and parent.type in {"module", "block"}
        and (node == parent.named_children[0])
    )
