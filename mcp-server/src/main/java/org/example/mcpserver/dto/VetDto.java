package org.example.mcpserver.dto;

import java.util.List;

public record VetDto(
	Integer id,
	String firstName,
	String lastName,
	Integer nrOfSpecialties,
	List<PetTypeDto> specialties
) {}
