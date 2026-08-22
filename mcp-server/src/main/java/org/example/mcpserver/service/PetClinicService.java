package org.example.mcpserver.service;

import java.util.List;

import org.example.mcpserver.client.PetClinicClient;
import org.example.mcpserver.dto.OwnerDto;
import org.example.mcpserver.dto.PetTypeDto;
import org.example.mcpserver.dto.VetDto;
import org.springframework.stereotype.Service;

@Service
public class PetClinicService {

	private final PetClinicClient client;

	public PetClinicService(PetClinicClient client) {
		this.client = client;
	}

	public List<OwnerDto> searchOwners(String lastName) {
		return client.findOwnersByLastName(lastName);
	}

	public OwnerDto getOwner(Integer ownerId) {
		return client.getOwnerById(ownerId);
	}

	public List<PetTypeDto> getPetTypes() {
		return client.getPetTypes();
	}

	public List<VetDto> getVets() {
		return client.getVets().vetList();
	}
}
