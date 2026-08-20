package org.springframework.samples.petclinic.api;

import java.time.LocalDate;
import java.util.Collection;
import java.util.Comparator;
import java.util.Optional;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.samples.petclinic.owner.Owner;
import org.springframework.samples.petclinic.owner.OwnerRepository;
import org.springframework.samples.petclinic.owner.Pet;
import org.springframework.samples.petclinic.owner.Visit;
import org.springframework.web.bind.annotation.*;

import jakarta.validation.Valid;

/**
 * JSON API for Visit. Nested under owner/pet, same as the real VisitController's
 * /owners/{ownerId}/pets/{petId}/visits/new mapping — minus the "/new" since this is a
 * create endpoint, not a form.
 */
@RestController
@RequestMapping("/api/owners/{ownerId}/pets/{petId}/visits")
public class VisitRestController {

	private final OwnerRepository owners;

	public VisitRestController(OwnerRepository owners) {
		this.owners = owners;
	}

	/** GET /api/owners/{ownerId}/pets/{petId}/visits */
	@GetMapping
	public ResponseEntity<Collection<Visit>> getVisits(@PathVariable int ownerId, @PathVariable int petId) {
		Optional<Owner> ownerOpt = owners.findById(ownerId);
		if (ownerOpt.isEmpty()) {
			return ResponseEntity.notFound().build();
		}
		Pet pet = ownerOpt.get().getPet(petId);
		if (pet == null) {
			return ResponseEntity.notFound().build();
		}
		return ResponseEntity.ok(pet.getVisits());
	}

	/**
	 * POST /api/owners/{ownerId}/pets/{petId}/visits — same future-date rule as the form.
	 */
	@PostMapping
	@ResponseStatus(HttpStatus.CREATED)
	public ResponseEntity<Visit> addVisit(@PathVariable int ownerId, @PathVariable int petId,
			@Valid @RequestBody Visit visit) {
		Optional<Owner> ownerOpt = owners.findById(ownerId);
		if (ownerOpt.isEmpty()) {
			return ResponseEntity.notFound().build();
		}
		Owner owner = ownerOpt.get();
		if (owner.getPet(petId) == null) {
			return ResponseEntity.notFound().build();
		}
		if (visit.getDate() != null && !visit.getDate().isAfter(LocalDate.now())) {
			throw new IllegalArgumentException("Visit date must be in the future");
		}
		owner.addVisit(petId, visit);
		Owner savedOwner = owners.save(owner);
		Pet savedPet = savedOwner.getPet(petId);
		Visit saved = savedPet.getVisits()
			.stream()
			.max(Comparator.comparing(Visit::getId, Comparator.nullsFirst(Comparator.naturalOrder())))
			.orElse(visit);
		return ResponseEntity.status(HttpStatus.CREATED).body(saved);
	}

}
