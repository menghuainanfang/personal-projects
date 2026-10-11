export function textRange(range: Range): Range {
  const normalized = range.cloneRange();
  if (
    range.startContainer.nodeType === Node.TEXT_NODE &&
    range.endContainer.nodeType === Node.TEXT_NODE
  )
    return normalized;
  const document = range.startContainer.ownerDocument!;
  const walker = document.createTreeWalker(
    range.commonAncestorContainer,
    NodeFilter.SHOW_TEXT,
  );
  const nodes: Text[] = [];
  while (walker.nextNode()) {
    const node = walker.currentNode as Text;
    if (
      node.length &&
      range.comparePoint(node, node.length) !== -1 &&
      range.comparePoint(node, 0) !== 1
    )
      nodes.push(node);
  }
  if (nodes.length) {
    normalized.setStart(
      nodes[0],
      range.startContainer === nodes[0] ? range.startOffset : 0,
    );
    const last = nodes[nodes.length - 1];
    normalized.setEnd(
      last,
      range.endContainer === last ? range.endOffset : last.length,
    );
  }
  return normalized;
}
