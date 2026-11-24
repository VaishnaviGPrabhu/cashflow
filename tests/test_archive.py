from pipeline.storage import LocalArchive, S3Archive


class FakeS3:
    def __init__(self):
        self.uploads = []

    def upload_file(self, filename, bucket, key):
        self.uploads.append((filename, bucket, key))


def test_local_archive_copies_files(tmp_path):
    src = tmp_path / "a.csv"
    src.write_text("x\n1\n")
    locations = LocalArchive(tmp_path / "archive").save("run1", [src])
    assert (tmp_path / "archive" / "run1" / "a.csv").read_text() == "x\n1\n"
    assert locations == [str(tmp_path / "archive" / "run1" / "a.csv")]


def test_s3_archive_uploads_with_run_scoped_keys(tmp_path):
    src = tmp_path / "a.csv"
    src.write_text("x\n")
    fake = FakeS3()
    locations = S3Archive("my-bucket", prefix="raw/", client=fake).save("run1", [src])
    assert fake.uploads == [(str(src), "my-bucket", "raw/run1/a.csv")]
    assert locations == ["s3://my-bucket/raw/run1/a.csv"]
