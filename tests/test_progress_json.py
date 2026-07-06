from scripts.generate_progress import build_progress_json, _status_to_canonical


def test_status_mapping():
    assert _status_to_canonical("✅ Complete") == "done"
    assert _status_to_canonical("🚧 In Progress (K-1)") == "in-progress"
    assert _status_to_canonical("🔜 Ready to build") == "pending"
    assert _status_to_canonical("💭 Your call") == "pending"
    assert _status_to_canonical("") == "pending"


def test_build_progress_json_shape():
    epics = {1: {"num": 1, "title": "Epic 1 — Foo", "status": "✅ Complete", "file": "EPIC_01_foo.md"},
             4: {"num": 4, "title": "Epic 4 — Bar", "status": "💭 Your call", "file": "EPIC_04_bar.md"}}
    commits = [{"epics": [1]}, {"epics": [1]}, {"epics": []}]
    doc = build_progress_json(epics, commits)
    assert doc["source"] == "epics" and doc["project"] == "StudyBuddy OnDemand"
    feats = {f["id"]: f for f in doc["features"]}
    assert feats["Epic 1"]["status"] == "done" and feats["Epic 1"]["commits"] == 2
    assert feats["Epic 1"]["name"] == "Foo"      # "Epic N —" prefix stripped
    assert feats["Epic 4"]["status"] == "pending" and feats["Epic 4"]["commits"] == 0
