"""
Structured output contract for the Spec Agent stage.

Kept in its own module (not inside spec_agent.py) because code_agent.py will need
to import this same ChangeSpec type later, once that stage is built.
"""

from pydantic import BaseModel, Field

# The only files the Code Agent is ever allowed to touch, mapped to their relative
# path from petclinic-app/src/main/java/org/springframework/samples/petclinic/.
# Deliberately still a fixed, known menu (not open repo exploration) — just widened
# from API-only to also include the core domain entities, since some changes
# (e.g. JPA cascade behavior) genuinely can't be implemented at the API layer alone.
ALLOWED_TARGET_FILES: dict[str, str] = {
	"OwnerRestController.java": "api",
	"PetRestController.java": "api",
	"VisitRestController.java": "api",
	"PetTypeRestController.java": "api",
	"ApiExceptionHandler.java": "api",
	"Owner.java": "owner",
	"Pet.java": "owner",
	"Visit.java": "owner",
	"PetType.java": "owner",
}

# Domain entities are higher blast-radius than a single REST controller — a change
# here affects every endpoint that touches that entity, not just one. Flagged
# separately so prompts can ask for extra caution on these specifically.
DOMAIN_FILES = {"Owner.java", "Pet.java", "Visit.java", "PetType.java"}

MAX_EXISTING_FILES = 3
MAX_NEW_FILES = 1


class NewFile(BaseModel):
	filename: str = Field(description="Name for the new file, e.g. 'PetHealthController.java'")
	reason: str = Field(description="Why a new file is needed rather than extending an existing one")


class ChangeSpec(BaseModel):
	"""The Spec Agent's structured output — the plan a human approves before any code is written."""

	issue_number: int
	issue_title: str

	target_files: list[str] = Field(
		description=f"Existing files to modify. Must be a subset of {list(ALLOWED_TARGET_FILES.keys())}. "
		f"Maximum {MAX_EXISTING_FILES} files."
	)
	new_files: list[NewFile] = Field(
		default_factory=list,
		description=f"New files to create, if the change genuinely can't fit into an existing file. "
		f"Maximum {MAX_NEW_FILES}.",
	)

	description: str = Field(description="Plain-English summary of what the change does and why")
	acceptance_criteria: list[str] = Field(description="Concrete, checkable conditions the change must satisfy")

	def validate_budget(self) -> list[str]:
		"""
		Returns a list of human-readable violations, empty if the spec is within budget.
		Called explicitly (not a pydantic validator) so run_sdlc.py can show the human
		*why* a spec was rejected, rather than just raising an exception.
		"""
		problems = []

		if len(self.target_files) > MAX_EXISTING_FILES:
			problems.append(f"{len(self.target_files)} existing files requested, max is {MAX_EXISTING_FILES}")

		unknown = [f for f in self.target_files if f not in ALLOWED_TARGET_FILES]
		if unknown:
			problems.append(f"Unknown target file(s) not in the allowed set: {unknown}")

		if len(self.new_files) > MAX_NEW_FILES:
			problems.append(f"{len(self.new_files)} new files requested, max is {MAX_NEW_FILES}")

		if not self.target_files and not self.new_files:
			problems.append("Spec names no files to change at all")

		return problems
