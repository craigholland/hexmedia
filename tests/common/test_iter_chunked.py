from hexmedia.common.iter import chunked


def test_chunked_basic():
    data = list(range(10))
    chunks = list(chunked(data, 3))
    assert chunks == [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]


def test_chunked_size_one():
    data = [1, 2, 3]
    assert list(chunked(data, 1)) == [[1], [2], [3]]


def test_chunked_size_gt_len():
    data = [1, 2, 3]
    assert list(chunked(data, 10)) == [[1, 2, 3]]


def test_chunked_generator_input():
    def gen():
        for i in range(5):
            yield i * i

    assert list(chunked(gen(), 2)) == [[0, 1], [4, 9], [16]]
