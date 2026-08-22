package org.example.mcpserver.dto;

import java.time.LocalDate;
import java.util.List;

public record PetDto(
	Integer id,
	String name,
	LocalDate birthDate,
	PetTypeDto type,
	List<VisitDto> visits
) {
	/**
	 * Convenience constructor for creating a new pet, where there is no visits list yet.
	 * Defaults visits to an empty list rather than null.
	 */
	public PetDto(Integer id, String firstName, LocalDate birthDate, PetTypeDto type) {
		this(id, firstName, birthDate, type, List.of());
	}
}
