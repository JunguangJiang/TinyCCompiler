import codecs


def parse_escape(s):
    return codecs.escape_decode(bytes(s, "ascii"))[0].decode("ascii")


def match_rule(ctx, rule):
    """判断ctx.getRuleIndex()==rule是否成立.若ctx无getRuleIndex()则返回False."""
    if hasattr(ctx, 'getRuleIndex'):
        return ctx.getRuleIndex() == rule
    else:
        return False


def match_texts(ctx, texts):
    """判断ctx.getText() in texts是否成立.若ctx无getText()则返回False. texts是一个字符串列表"""
    if hasattr(ctx, 'getText'):
        return ctx.getText() in texts
    else:
        return False


def match_text(ctx, text):
    """判断ctx.getText() == text是否成立.若ctx无getText()则返回False"""
    return match_texts(ctx, [text])