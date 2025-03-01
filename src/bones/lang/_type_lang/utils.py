

def ctxLabel(ctx):
    label = type(ctx).__name__
    if label.endswith('Context'): label = label[:-7].lower()
    return label

