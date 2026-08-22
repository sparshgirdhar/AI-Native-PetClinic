package org.example.mcpserver.resources;

import org.example.mcpserver.client.PetClinicClient;
import org.example.mcpserver.dto.PetTypeDto;
import org.example.mcpserver.dto.VetListResponse;
import org.springframework.ai.mcp.annotation.McpResource;
import org.springframework.stereotype.Component;
import tools.jackson.databind.ObjectMapper;

import java.util.List;

@Component
public class PetClinicResources {

	private final PetClinicClient petClinicClient;
	private final ObjectMapper objectMapper;

	public PetClinicResources(
		PetClinicClient petClinicClient,
		ObjectMapper objectMapper) {
		this.petClinicClient = petClinicClient;
		this.objectMapper = objectMapper;
	}

	@McpResource(
		uri = "vets://list",
		name = "Vet Directory",
		description = "All veterinarians at the clinic, including their specialties " +
			"(e.g. surgery, dentistry, radiology). " +
			"Use this to match a requested specialty to a vet, or to list available vets."
	)
	public String getVets() {
		VetListResponse vets = petClinicClient.getVets();
		return toJson(vets);
	}

	@McpResource(
		uri = "pet-types://list",
		name = "Pet Types",
		description = "The full list of valid pet types (e.g. dog, cat, bird) and their ids, " +
			"as accepted by petclinic-app when creating a pet."
	)
	public String getPetTypes() {
		List<PetTypeDto> types = petClinicClient.getPetTypes();
		return toJson(types);
	}

	private String toJson(Object value) {
		return objectMapper.writeValueAsString(value);
	}
}
