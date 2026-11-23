from app.models import Artifact, PatchCandidate
from app.repositories.base import Repository
from app.repositories.errors import Conflict


class PatchRepository(Repository[PatchCandidate]):
    def add(self, record: PatchCandidate) -> PatchCandidate:
        artifact = Repository(self.session, Artifact).get(record.diff_artifact_id)
        if artifact.kind != "diff" or artifact.sha256 != record.patch_hash:
            raise Conflict("Candidate hash and diff artifact metadata must match.")
        if record.version == 1:
            if record.supersedes_candidate_id is not None:
                raise Conflict("The first candidate cannot supersede another candidate.")
        else:
            if record.supersedes_candidate_id is None:
                raise Conflict("A revised candidate requires its predecessor.")
            previous = self.get(record.supersedes_candidate_id)
            if previous.incident_id != record.incident_id or previous.version + 1 != record.version:
                raise Conflict("Candidate revisions must form an ordered incident history.")
        return super().add(record)
