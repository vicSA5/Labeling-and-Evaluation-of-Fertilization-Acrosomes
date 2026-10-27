from core.channel_manager import scan
from core import progress


def make(tmp_path, names):
    for n in names:
        (tmp_path / n).write_bytes(b"")


def test_group_order_missing_unknown(tmp_path):
    make(tmp_path, ["10.1.tiff", "10.3.tiff", "10.4.tiff", "2.1.tif", "2.4.tif", "foo.tiff", "2.9.tiff"])
    samples, unknown = scan(tmp_path)
    assert [s.id for s in samples] == [2, 10]
    assert samples[0].missing == ["G"] and samples[1].missing == []
    assert unknown == ["2.9.tiff", "foo.tiff"]


def test_csv_roundtrip(tmp_path):
    make(tmp_path, ["8.1.tiff", "8.3.tiff"])
    samples, _ = scan(tmp_path)
    samples[0].label = "Intacto"
    progress.save(tmp_path / "p.csv", samples)
    assert progress.load(tmp_path / "p.csv") == {8: "Intacto"}
