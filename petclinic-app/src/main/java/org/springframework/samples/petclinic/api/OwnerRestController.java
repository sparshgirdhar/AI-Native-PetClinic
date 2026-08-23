package org.springframework.samples.petclinic.api;

import java.util.ArrayList;
import java.util.List;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.samples.petclinic.owner.Owner;
import org.springframework.samples.petclinic.owner.OwnerRepository;
import org.springframework.samples.petclinic.owner.Pet;
import org.springframework.samples.petclinic.owner.Visit;
import org.springframework.web.bind.annotation.*;

import jakarta.validation.Valid;

/**
 * JSON API for Owner, sitting alongside the existing Thymeleaf OwnerController. Calls the
 * same OwnerRepository the MVC controller uses — no duplicated logic. Intended consumer:
 * mcp-server.
 */
@RestController
@RequestMapping("/api/owners")
public class OwnerRestController {

	private final OwnerRepository owners;

	public OwnerRestController(OwnerRepository owners) {
		this.owners = owners;
	}

	/**
	 * GET /api/owners?lastName=Franklin&page=1 Mirrors OwnerController.processFindForm —
	 * empty lastName returns all owners.
	 */
	@GetMapping
	public List<Owner> findByLastName(@RequestParam(defaultValue = "") String lastName,
			@RequestParam(defaultValue = "1") int page) {
		Pageable pageable = PageRequest.of(page - 1, 20);
		Page<Owner> result = owners.findByLastNameStartingWith(lastName.strip(), pageable);
		return result.getContent();
	}

	/** GET /api/owners/{ownerId} — full owner including nested pets and visits. */
	@GetMapping("/{ownerId}")
	public ResponseEntity<Owner> getOwner(@PathVariable int ownerId) {
		return owners.findById(ownerId).map(ResponseEntity::ok).orElseGet(() -> ResponseEntity.notFound().build());
	}

	/** POST /api/owners — create a new owner. */
	@PostMapping
	@ResponseStatus(HttpStatus.CREATED)
	public Owner createOwner(@Valid @RequestBody Owner owner) {
		owner.setId(null); // ignore any client-supplied id, mirrors
							// dataBinder.setDisallowedFields("id")
		return owners.save(owner);
	}

	/** PUT /api/owners/{ownerId} — update an existing owner. */
	@PutMapping("/{ownerId}")
	public ResponseEntity<Owner> updateOwner(@PathVariable int ownerId, @Valid @RequestBody Owner ownerUpdate) {
		return owners.findById(ownerId).map(existing -> {
			ownerUpdate.setId(ownerId);
			return ResponseEntity.ok(owners.save(ownerUpdate));
		}).orElseGet(() -> ResponseEntity.notFound().build());
	}

	/**
	 * GET /api/owners/{ownerId}/visits — returns all visits for all pets owned by the
	 * owner.
	 */
	@GetMapping("/{ownerId}/visits")
	public ResponseEntity<List<VisitWithPetName>> getVisitsByOwner(@PathVariable int ownerId) {
		return owners.findById(ownerId).map(owner -> {
			List<VisitWithPetName> visits = new ArrayList<>();
			for (Pet pet : owner.getPets()) {
				if (pet.getVisits() != null) {
					for (Visit visit : pet.getVisits()) {
						visits.add(new VisitWithPetName(pet.getName(), visit.getDate(), visit.getDescription()));
					}
				}
			}
			return ResponseEntity.ok(visits);
		}).orElseGet(() -> ResponseEntity.notFound().build());
	}

	public static class VisitWithPetName {

		private String petName;

		private java.time.LocalDate date;

		private String description;

		public VisitWithPetName(String petName, java.time.LocalDate date, String description) {
			this.petName = petName;
			this.date = date;
			this.description = description;
		}

		public String getPetName() {
			return petName;
		}

		public void setPetName(String petName) {
			this.petName = petName;
		}

		public java.time.LocalDate getDate() {
			return date;
		}

		public void setDate(java.time.LocalDate date) {
			this.date = date;
		}

		public String getDescription() {
			return description;
		}

		public void setDescription(String description) {
			this.description = description;
		}

	}

}
