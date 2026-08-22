package org.example.mcpserver.client;

import java.util.List;

import org.example.mcpserver.dto.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class PetClinicClient {

	private final RestClient restClient;

	public PetClinicClient(RestClient petClinicRestClient) {
		this.restClient = petClinicRestClient;
	}

	public OwnerDto getOwnerById(int ownerId) {
		return restClient.get()
			.uri("/api/owners/{id}", ownerId)
			.retrieve()
			.body(OwnerDto.class);
	}

	public List<OwnerDto> findOwnersByLastName(String lastName) {
		OwnerDto[] owners = restClient.get()
			.uri(uriBuilder -> uriBuilder
				.path("/api/owners")
				.queryParam("lastName", lastName)
				.build())
			.retrieve()
			.body(OwnerDto[].class);

		return owners == null ? List.of() : List.of(owners);
	}

	public OwnerDto createOwner(OwnerDto owner) {
		return restClient.post()
			.uri("/api/owners")
			.body(owner)
			.retrieve()
			.body(OwnerDto.class);
	}

	public List<PetTypeDto> getPetTypes() {
		PetTypeDto[] types = restClient.get()
			.uri("/api/pettypes")
			.retrieve()
			.body(PetTypeDto[].class);

		return types == null ? List.of() : List.of(types);
	}

	public VetListResponse getVets() {
		return restClient.get()
			.uri("/vets")
			.retrieve()
			.body(VetListResponse.class);
	}

	public PetDto getPet(Integer ownerId, Integer petId) {
		return restClient.get()
			.uri("/api/owners/{ownerId}/pets/{petId}", ownerId, petId)
			.retrieve()
			.body(PetDto.class);
	}

	public PetDto createPet(Integer ownerId, PetDto pet) {
		return restClient.post()
			.uri("/api/owners/{ownerId}/pets", ownerId)
			.body(pet)
			.retrieve()
			.body(PetDto.class);
	}

	public VisitDto[] getPetVisits(Integer ownerId, Integer petId) {
		return restClient.get()
			.uri("/api/owners/{ownerId}/pets/{petId}/visits", ownerId, petId)
			.retrieve()
			.body(VisitDto[].class);
	}

	public VisitDto createVisit(Integer ownerId, Integer petId, VisitDto visit) {
		return restClient.post()
			.uri("/api/owners/{ownerId}/pets/{petId}/visits", ownerId, petId)
			.body(visit)
			.retrieve()
			.body(VisitDto.class);
	}
}
