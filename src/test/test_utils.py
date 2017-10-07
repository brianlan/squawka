import sys
sys.path.append('..')

from ..utils import flatten


def test_flatten():
    x = [1, [3, 4], 2, [7, 8, 9], -1, 'a', ['b', 'c'], 0]
    assert flatten(x) == [1, 3, 4, 2, 7, 8, 9, -1, 'a', 'b', 'c', 0]

    y = [[1, 2], [3, 4], [5, 6]]
    assert flatten(y) == [1, 2, 3, 4, 5, 6]

    z = [[[1, 2], [3, 4]], [[5, 6], [7, 8 ]]]
    assert flatten(z) == [[1, 2], [3, 4], [5, 6], [7, 8]]
