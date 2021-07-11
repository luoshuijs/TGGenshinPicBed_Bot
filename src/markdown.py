def markdown_escape(text: str):
    md_reserved = ['\\', '`', '*', '_', '{', '}', '[', ']', '<', '>', '(', ')', '#', '+', '-', '.', '!', '|', '~']
    escaped_str = text
    for c in md_reserved:
        escaped_str = escaped_str.replace(c, '\\'+c)
    return escaped_str
