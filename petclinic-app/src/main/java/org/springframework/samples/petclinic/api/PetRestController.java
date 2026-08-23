package org.springframework.samples.petclinic.api;

import java.util.Optional;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.samples.petclinic.owner.Owner;
import org.springframework.samples.petclinic.owner.OwnerRepository;
import org.springframework.samples.petclinic.owner.Pet;
import org.springframework.web.bind.annotation.*;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/api/owners/{ownerId}/pets")
public class PetRestController {

	private final OwnerRepository owners;

	public PetRestController(OwnerRepository owners) {
		this.owners = owners;
	}

	/** GET /api/owners/{ownerId}/pets/{petId} */
	@GetMapping("/{petId}")
	public ResponseEntity<Pet> getPet(@PathVariable int ownerId, @PathVariable int petId) {
		Optional<Owner> ownerOpt = owners.findById(ownerId);
		if (ownerOpt.isEmpty()) {
			return ResponseEntity.notFound().build();
		}
		Pet pet = ownerOpt.get().getPet(petId);
		if (pet == null) {
			return ResponseEntity.notFound().build();
		}
		return ResponseEntity.ok(pet);
	}

	/**
	 * POST /api/owners/{ownerId}/pets — same duplicate-name / future-birthdate rules as
	 * the form.
	 */
	@PostMapping
	@ResponseStatus(HttpStatus.CREATED)
	public ResponseEntity<Pet> addPet(@PathVariable int ownerId, @Valid @RequestBody Pet pet) {
		Optional<Owner> ownerOpt = owners.findById(ownerId);
		if (ownerOpt.isEmpty()) {
			return ResponseEntity.notFound().build();
		}
		Owner owner = ownerOpt.get();
		if (pet.getName() != null && owner.getPet(pet.getName(), true) != null) {
			throw new IllegalArgumentException("Pet name '" + pet.getName() + "' already exists for this owner");
		}
		pet.setId(null);
		owner.addPet(pet);
		Owner savedOwner = owners.saveAndFlush(owner);
		Pet saved = savedOwner.getPet(pet.getName());
		return ResponseEntity.status(HttpStatus.CREATED).body(saved);
	}

	/** PUT /api/owners/{ownerId}/pets/{petId} */
	@PutMapping("/{petId}")
	public ResponseEntity<Pet> updatePet(@PathVariable int ownerId, @PathVariable int petId,
			@Valid @RequestBody Pet petUpdate) {
		Optional<Owner> ownerOpt = owners.findById(ownerId);
		if (ownerOpt.isEmpty()) {
			return ResponseEntity.notFound().build();
		}
		Owner owner = ownerOpt.get();
		Pet existing = owner.getPet(petId);
		if (existing == null) {
			return ResponseEntity.notFound().build();
		}
		existing.setName(petUpdate.getName());
		existing.setBirthDate(petUpdate.getBirthDate());
		existing.setType(petUpdate.getType());
		owners.saveAndFlush(owner);
		return ResponseEntity.ok(existing);
	}

	/** DELETE /api/owners/{ownerId}/pets/{petId} */
	@DeleteMapping("/{petId}")
	public ResponseEntity<Void> deletePet(@PathVariable int ownerId, @PathVariable int petId) {
		Optional<Owner> ownerOpt = owners.findById(ownerId);
		if (ownerOpt.isEmpty()) {
			return ResponseEntity.notFound().build();
		}
		Owner owner = ownerOpt.get();
		Pet pet = owner.getPet(petId);
		if (pet == null) {
			return ResponseEntity.notFound().build();
		}
		owner.getPets().remove(pet);
		owners.saveAndFlush(owner);
		return ResponseEntity.noContent().build();
	}

}
