package org.springframework.samples.petclinic.api;

import java.util.List;

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

	public PetTypeRestController(PetTypeRepository types) {
		this.types = types;
	}

	/** GET /api/pettypes */
	@GetMapping("/api/pettypes")
	public List<PetType> listPetTypes() {
		return types.findPetTypes();
	}

}
