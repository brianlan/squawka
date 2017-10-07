def flatten(x):
    """1-order flatten method"""
    return [j for i in x for j in (i if isinstance(i, list) else [i])]
