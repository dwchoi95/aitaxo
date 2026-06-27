from src.common.config import Config
from src.gold.gold_finalizer import GoldFinalizer


def test_annotator_parse_multilabel_and_uncovered(tmp_path):
    g = GoldFinalizer(Config())
    g.out = tmp_path
    (tmp_path / "annotation_annotator1.csv").write_text(
        "item_id,detail_file,labels,uncovered,notes\n"
        "g1,items/g1.md,GE4.2;AE3.2,no,\n"
        "g2,items/g2.md,,yes,none fit\n")
    parsed = g._load_ann("annotation_annotator1.csv")
    assert parsed["g1"] == {"GE4.2", "AE3.2"}
    assert parsed["g2"] == {"UNCOVERED"}
