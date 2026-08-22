from collections.abc import Collection

from tree_sitter import Node

from slopo.indexing.parsing.base import CodeUnit, hash_body


def code_unit(
    *,
    name: str,
    start: Node,
    end: Node,
    body: Node | None,
    source: bytes,
    comment_types: Collection[str],
) -> CodeUnit:
    unit_source = _without_comments(start, end, source, comment_types)
    return CodeUnit(
        name=name,
        body=unit_source,
        start_line=start.start_point[0] + 1,
        end_line=end.end_point[0] + 1,
        body_node_count=count_named_nodes(body) if body is not None else 0,
        body_hash=hash_body(unit_source),
    )


def node_text(node: Node | None) -> str | None:
    if node is None or node.text is None:
        return None
    return node.text.decode()


def first_descendant_by_field(node: Node, field: str) -> Node | None:
    direct = node.child_by_field_name(field)
    if direct is not None:
        return direct
    for child in node.named_children:
        nested = first_descendant_by_field(child, field)
        if nested is not None:
            return nested
    return None


def next_named_sibling(node: Node, expected_type: str) -> Node | None:
    sibling = node.next_named_sibling
    if sibling is None or sibling.type != expected_type:
        return None
    return sibling


def count_named_nodes(node: Node) -> int:
    count = 1 if node.is_named else 0
    for child in node.children:
        count += count_named_nodes(child)
    return count


def _without_comments(
    start: Node,
    end: Node,
    source: bytes,
    comment_types: Collection[str],
) -> str:
    spans: list[tuple[int, int]] = []
    common_parent = _common_parent(start, end)
    _collect_comment_spans(
        common_parent,
        spans,
        comment_types,
        start.start_byte,
        end.end_byte,
    )

    pieces: list[bytes] = []
    cursor = start.start_byte
    for comment_start, comment_end in sorted(spans):
        if comment_end <= start.start_byte or comment_start >= end.end_byte:
            continue
        clipped_start = max(comment_start, start.start_byte)
        clipped_end = min(comment_end, end.end_byte)
        pieces.append(source[cursor:clipped_start])
        cursor = clipped_end
    pieces.append(source[cursor : end.end_byte])
    return b"".join(pieces).decode()


def _common_parent(left: Node, right: Node) -> Node:
    left_ancestors: set[int] = set()
    current: Node | None = left
    while current is not None:
        left_ancestors.add(current.id)
        current = current.parent

    current = right
    while current is not None:
        if current.id in left_ancestors:
            return current
        current = current.parent
    return left


def _collect_comment_spans(
    node: Node,
    spans: list[tuple[int, int]],
    comment_types: Collection[str],
    start_byte: int,
    end_byte: int,
) -> None:
    if node.end_byte <= start_byte or node.start_byte >= end_byte:
        return
    if node.type in comment_types:
        spans.append((node.start_byte, node.end_byte))
        return
    for child in node.children:
        _collect_comment_spans(child, spans, comment_types, start_byte, end_byte)
