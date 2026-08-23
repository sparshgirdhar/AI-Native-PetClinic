package org.springframework.samples.petclinic.api;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.springframework.samples.petclinic.owner.OwnerRepository;
import org.springframework.samples.petclinic.owner.PetType;
import org.springframework.samples.petclinic.owner.PetTypeRepository;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * JSON API for PetType reference data — feeds the pet-types MCP resource.
 */
@RestController
public class PetTypeRestController {

	private final PetTypeRepository types;

	private final OwnerRepository owners;

	public PetTypeRestController(PetTypeRepository types, OwnerRepository owners) {
		this.types = types;
		this.owners = owners;
	}

	/** GET /api/pettypes */
	@GetMapping("/api/pettypes")
	public List<PetType> listPetTypes() {
		return types.findPetTypes();
	}

	/** GET /api/pettypes/visit-counts */
	@GetMapping("/api/pettypes/visit-counts")
	public List<PetTypeVisitCount> listPetTypeVisitCounts() {
		List<PetType> petTypes = types.findPetTypes();
		Map<Integer, PetTypeVisitCount> countMap = new HashMap<>();
		for (PetType petType : petTypes) {
			countMap.put(petType.getId(), new PetTypeVisitCount(petType.getName(), 0));
		}
		owners.findAll().forEach(owner -> owner.getPets().forEach(pet -> {
			PetTypeVisitCount counter = countMap.get(pet.getType().getId());
			if (counter != null) {
				counter.visitCount += pet.getVisits().size();
			}
		}));
		return new ArrayList<>(countMap.values());
	}

	public static class PetTypeVisitCount {

		public final String petTypeName;

		public int visitCount;

		public PetTypeVisitCount(String petTypeName, int visitCount) {
			this.petTypeName = petTypeName;
			this.visitCount = visitCount;
		}

	}

}
